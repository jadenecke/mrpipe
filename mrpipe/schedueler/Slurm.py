import os.path
import subprocess as sps
from enum import Enum
import re
from time import sleep
from mrpipe.meta import loggerModule
from mrpipe.schedueler import Bash

logger = loggerModule.Logger()

class ProcessStatus(Enum):
    notRun = 1
    running = 2
    finished = 3
    error = 4


class Scheduler:

    jobScript: Bash.Script = None

    # def __int__(self, SLURM_ntasks: int = 1, SLURM_cpusPerTask: int = 1, SLURM_nnodes: int = None, SLURM_ngpus: int = 0, SLURM_memPerCPU: float = 2.5):
    def __init__(self, job: str, SLURM_ntasks=1, SLURM_cpusPerTask=1, SLURM_nnodes=None, SLURM_ngpus=None,
                 SLURM_memPerCPU=2, SLURM_partition: str = None):
        self.SLURM_ntasks = SLURM_ntasks
        self.SLURM_cpusPerTask = SLURM_cpusPerTask
        self.SLURM_nnodes = SLURM_nnodes
        self.SLURM_ngpus = SLURM_ngpus
        self.SLURM_memPerCPU = SLURM_memPerCPU
        self.SLURM_partition = SLURM_partition
        self.job = job
        self.status = ProcessStatus.notRun
        self.jobid = None
        self.jobidFound = False
        self.user = None


    def _gpuNodeCheck(self):
        # check for number of GPUs requested vs nodes and task mismatch and correct if necessary.
        if self.SLURM_ngpus and (self.SLURM_nnodes or self.SLURM_ntasks):
            if not (self.SLURM_ngpus is self.SLURM_nnodes is self.SLURM_ntasks):
                logger.warning("Slurm allocation is trying to use GPUs. Therefore exactly on GPU per node must be allocated with one task per Node. Everything else will lead to uncontrolled shared usage of the GPUs and probably memory overflow errors.")
                logger.warning("Letting number of GPUs dictate everything else.")
                self.SLURM_ntasks = self.SLURM_ngpus
                self.SLURM_nnodes = self.SLURM_ngpus

    def _jobSubmitString(self, mode: str) -> str:
        if mode not in ["sbatch", "salloc"]:
            logger.critical("Job mode wrongly defined, must either be sbatch or salloc. Defaulting to sbatch")
            mode = "sbatch"
        allocstr = mode
        if self.SLURM_ntasks:
            allocstr += f' --ntasks={self.SLURM_ntasks}'
        if self.SLURM_cpusPerTask:
            allocstr += f' --cpus-per-task={self.SLURM_cpusPerTask}'
        if self.SLURM_nnodes:
            allocstr += f' --nodes={self.SLURM_nnodes}'
        if self.SLURM_memPerCPU:
            allocstr += f' --mem-per-cpu={self.SLURM_memPerCPU * 1000}'
        if self.SLURM_ngpus:
            allocstr += f' --gres=gpu:{self.SLURM_memPerCPU}'
        if self.SLURM_partition:
            allocstr += f' --partition={self.SLURM_partition}'
        if mode == "sbatch":
            allocstr += f' --wrap="{self.job}"'
        else:
            allocstr += f' {self.job}'
        return allocstr

    def salloc(self, attach=True):
        logger.info(f'Running salloc on: {self.job}')
        if self.status is not ProcessStatus.notRun:
            logger.warning(f'This job as already been evoked and its current status is: {self.status.name}. Not running again.')
            return
        try:
            self._gpuNodeCheck()
            logger.process( "Trying to allocate resources on the Cluster.")
            jobSubmitString = self._jobSubmitString(mode="salloc")
            logger.debug(f'salloc String: {jobSubmitString}')
            proc = sps.Popen(jobSubmitString, shell=True, stdout=sps.PIPE, stderr=sps.STDOUT)
            self.userJobs()

            for line in iter(proc.stdout.readline, b''):
                decoded_line = line.decode('utf-8').rstrip('\n')
                logger.debug(decoded_line)
                if not self.jobidFound:
                    m = re.match(r'salloc: Granted job allocation ([0-9]+)', decoded_line)
                    if m:
                        self.jobid = m.group(1)
                        self.jobidFound = True
                        logger.debug(f'Job Id: {self.jobid}')
                        if not attach:
                            break

            if attach:
                returncode = proc.wait()
                if returncode == 0:
                    logger.debug(f'Job finished: {self.job}')
                    self.status = ProcessStatus.finished
                else:
                    logger.debug(f'Job failed: {self.job}')
                    self.status = ProcessStatus.error

                logger.debug(f'Returncode: {proc.returncode}')
                self.jobPostMortem()
        except Exception as e:
            # logger.critical('Could not allocate the following resources:')
            # logger.critical(str(self))
            # logger.critical('With the following error message: ')
            # logger.critical(str(e.with_traceback()))
            logger.logExceptionCritical(f"Could not allocate the following resources: {str(self)}", e)

    def sbatch(self):
        logger.info(f'Running sbatch on: {self.job}')
        if self.status is not ProcessStatus.notRun:
            logger.warning(f'This job as already been evoked and its current status is: {self.status.name}. Not running again.')
            return
        try:
            self._gpuNodeCheck()
            logger.process( "Trying to allocate resources on the Cluster.")
            jobSubmitString = self._jobSubmitString(mode="sbatch")
            logger.debug(f'sbatch String: {jobSubmitString}')
            proc = sps.Popen(jobSubmitString, shell=True, stdout=sps.PIPE, stderr=sps.STDOUT)
            self.userJobs()
            for line in iter(proc.stdout.readline, b''):
                decoded_line = line.decode('utf-8').rstrip('\n')
                logger.debug(decoded_line)
                if not self.jobidFound:
                    m = re.match(r'Submitted batch job ([0-9]+)', decoded_line)
                    if m:
                        self.jobid = m.group(1)
                        self.jobidFound = True
                        logger.debug(f'Job Id: {self.jobid}')

            returncode = proc.wait()
            if returncode == 0:
                logger.debug(f'Job submitted: {self.job}')
                self.status = ProcessStatus.running
            else:
                logger.debug(f'Job failed: {self.job}')
                self.status = ProcessStatus.error

            logger.debug(f'Returncode: {proc.returncode}')
            self.jobPostMortem()
        except Exception as e:
            # logger.critical('Could not allocate the following resources:')
            # logger.critical(str(self))
            # logger.critical('With the following error message: ')
            # logger.critical(str(e.with_traceback()))
            logger.logExceptionCritical(f"Could not allocate the following resources: {str(self)}", e)

    def getAllocateString(self, mode: str) -> str:
        return self._jobSubmitString(mode)

    def _createBashJob(self, mode: str):
        self.jobScript = Bash.jobScript(self._jobSubmitString)

    def



    def jobPostMortem(self):
        sleep(0.5)
        if not logger.level >= logger.DEBUG:
            return
        if not self.jobid:
            logger.warning("Job ID is not set, probably because job was not run. Cant call post mortem.")
        logger.debug('############################ POST MORTEM ############################')
        proc = sps.Popen(f'sacct -j {self.jobid} --format=JobID,Start,End,Elapsed,NCPUS', shell=True, stdout=sps.PIPE, stderr=sps.STDOUT)
        for line in iter(proc.stdout.readline, b''):
            # logger.debug(line.decode('utf-8'))
            decoded_line = line.decode('utf-8').rstrip('\n')
            logger.debug(decoded_line)
        proc.wait()
        logger.debug('#####################################################################')

    def userJobs(self):
        sleep(0.5)
        if not logger.level >= logger.DEBUG:
            return
        if not self.user:
            self.getUser()

        logger.debug('############################ YOUR JOBS ############################')
        proc = sps.Popen(f'squeue -u  {self.user}', shell=True, stdout=sps.PIPE, stderr=sps.STDOUT)
        for line in iter(proc.stdout.readline, b''):
            # logger.debug(line.decode('utf-8'))
            decoded_line = line.decode('utf-8').rstrip('\n')
            logger.debug(decoded_line)
        proc.wait()
        logger.debug('###################################################################')

    def getUser(self):
        self.user = sps.run("whoami", shell=True, capture_output=True).stdout.decode('utf-8')

    def _getInterpreter(self):
        if not self.job:
            logger.warning('Can not get interpreter, if job is not specified.')
        for term in self.job.split(" "):
            if os.path.isfile(term):
                with open(self.job) as f:
                    first_line = f.readline()

    def __str__(self):
        return f"""Resource allocation request:
               Number of Tasks: {self.SLURM_ntasks}
               Number of CPUs per task: {self.SLURM_cpusPerTask}
               Number of nodes: {self.SLURM_nnodes}
               Number of GPUs: {self.SLURM_ngpus}, (Script can only utilize one gpu per node, because our SLURM version is to old and does not support GPUS_PER_TASK
               Number of Memory per CPU: {self.SLURM_memPerCPU}Gb
               Number of CPUs in Total: {self.SLURM_cpusPerTask * self.SLURM_ntasks}"""






#
#
# class batch_setting_new:
#     settings = ""
#     dep = ''
#
#     def __init__(self,
#                  settings="--ntasks=1 --cpus-per-task=1 -N 1 --job-name=$name --mem=8000 --time=1-0 --out=submit.out"):
#         self.settings = settings
#
#     def __str__(self):
#         return self.settings
#
#     def edit_default(self, edit):
#         # this function won't check if the options put in is correct or not
#         # directly replace the default version
#         self.settings = edit
#
#     def add_options(self, edit):
#         # add options
#         self.settings += f" {edit}"
#
#     def reset_dep(self):
#         # if not dep is needed
#         self.dep = ''
#
#     def add_dep(self, edit):
#         # if need to add dep
#         try:
#             edit = int(edit)
#         except ValueError:
#             print("dependency input should be numerical jobid")
#             return
#
#         if not self.dep:
#             self.dep = f"--dependency=afterok:{str(edit)}"
#         else:
#             self.dep += f":{str(edit)}"
#
#     def sbatch(self, wrap):
#         sub = ['sbatch',
#                self.settings, self.dep,
#                f'--wrap="{wrap.strip()}"']
#         # print(" ".join(sub))
#         process = sps.Popen(" ".join(sub), shell=True, stdout=sps.PIPE)
#         stdout = process.communicate()[0].decode("utf-8")
#         return (stdout)
#
# def sbatch(job_name="py_job", mem='8', dep="", time='3-0', log="submit.out", wrap="python hello.py", add_option=""):
#     sub = ['sbatch', '--ntasks=1', '--cpus-per-task=1', '-N', '1', f'--job-name={job_name}', f'--mem={mem}000',
#            f'--time={time}', dep, add_option, f'--out={log}', f'--wrap="{wrap.strip()}"']
#     # print(" ".join(sub))
#     process = sps.Popen(" ".join(sub), shell=True, stdout=sps.PIPE)
#     stdout = process.communicate()[0].decode("utf-8")
#     return (stdout)
#
#
# def run_cmd(cmd):
#     # simplified subprocess.run() of running linux command in python
#     # cmd pass in as a list of strings, i.e. cd .. should be ['cd', '..']
#     # return screen print as a string
#     process = sps.run(cmd, stdout=sps.PIPE)
#     return process.stdout.decode("utf-8")
