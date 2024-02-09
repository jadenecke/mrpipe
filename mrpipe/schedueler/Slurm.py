import math
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

    job: Bash.Script = None
    nextJob = None

    # def __int__(self, SLURM_ntasks: int = 1, cpusPerTask: int = 1, SLURM_nnodes: int = None, ngpus: int = 0, SLURM_memPerCPU: float = 2.5):
    def __init__(self, job: str, cpusPerTask=1, cpusTotal = 1,
                 memPerCPU=2, minimumMemPerNode=2, partition: str = None, ngpus=None):
        #specify
        self.SLURM_cpusPerTask = cpusPerTask
        self.SLURM_ngpus = ngpus
        self.SLURM_memPerCPU = memPerCPU
        self.SLURM_partition = partition
        self.job = Bash.Script(job)
        self.status = ProcessStatus.notRun

        #calculate
        if ngpus:
            self.SLURM_ntasks = ngpus
        else:
            self.SLURM_ntasks = math.floor(cpusTotal/cpusPerTask)
        self.minCPUsPerNode = math.ceil(minimumMemPerNode / memPerCPU)
        self.SLURM_nnodes = ngpus

        #set Empty
        self.SLURM_jobid = None
        self.SLURM_jobidFound = False
        self.user = None

    def run(self):
        pass

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
        # use --mincpus flag to specify minimum numer of threads per node, to specify a minimum amount of memory per node.
        # Otherwise, it could happen that a task with 1 cpu and 2Gb of memory is allocated on an extra node and won't run because of memory restrictions.
        # jobs should usually run on shared memory allocation on as little nodes as necessary to have as many jobs as possible run in parallel with enough shared memory to handle memory spikes.
        if self.minCPUsPerNode:
            allocstr += f' --mincpus={self.minCPUsPerNode}'
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
                if not self.SLURM_jobidFound:
                    m = re.match(r'salloc: Granted job allocation ([0-9]+)', decoded_line)
                    if m:
                        self.SLURM_jobid = m.group(1)
                        self.SLURM_jobidFound = True
                        logger.debug(f'Job Id: {self.SLURM_jobid}')
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
                if not self.SLURM_jobidFound:
                    m = re.match(r'Submitted batch job ([0-9]+)', decoded_line)
                    if m:
                        self.SLURM_jobid = m.group(1)
                        self.SLURM_jobidFound = True
                        logger.debug(f'Job Id: {self.SLURM_jobid}')

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
            logger.logExceptionCritical(f"Could not allocate the following resources: {str(self)}", e)

    def getAllocateString(self, mode: str) -> str:
        return self._jobSubmitString(mode)

    def addNextJob(self, job: str):
        self.job.appendJob(job)

    def jobPostMortem(self):
        sleep(0.5)
        if not logger.level >= logger.DEBUG:
            return
        if not self.SLURM_jobid:
            logger.warning("Job ID is not set, probably because job was not run. Cant call post mortem.")
        logger.debug('############################ POST MORTEM ############################')
        proc = sps.Popen(f'sacct -j {self.SLURM_jobid} --format=JobID,Start,End,Elapsed,NCPUS', shell=True, stdout=sps.PIPE, stderr=sps.STDOUT)
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

    def srunify(self):
        for index, command in enumerate(self.job.jobLines):
            if not command.startswith("srun"):
                self.job.jobLines[index] = f"srun -n 1 --mem=0 --exclusive " + command

    # def _getInterpreter(self):
    #     if not self.job:
    #         logger.warning('Can not get interpreter, if job is not specified.')
    #     for term in self.job.split(" "):
    #         if os.path.isfile(term):
    #             with open(self.job) as f:
    #                 first_line = f.readline()

    def __str__(self):
        return f"""Resource allocation request:
               Number of Tasks: {self.SLURM_ntasks}
               Number of CPUs per task: {self.SLURM_cpusPerTask}
               Number of nodes: {self.SLURM_nnodes}
               Number of GPUs: {self.SLURM_ngpus}, (Script can only utilize one gpu per node, because our SLURM version is to old and does not support GPUS_PER_TASK
               Number of Memory per CPU: {self.SLURM_memPerCPU}Gb
               Number of CPUs in Total: {self.SLURM_cpusPerTask * self.SLURM_ntasks}
               Job String: {self._jobSubmitString("sbatch")}"""
