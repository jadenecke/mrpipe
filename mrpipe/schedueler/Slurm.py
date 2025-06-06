import math
import subprocess as sps
from enum import Enum
import re
from time import sleep
from mrpipe.Helper import Helper
from mrpipe.meta import LoggerModule
from mrpipe.schedueler import Bash
from typing import List
import os
import asyncio
from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.PathClass import Path
from mrpipe.Toolboxes.envs import EnvClass


logger = LoggerModule.Logger()

class ProcessStatus(Enum):
    notStarted = 1
    setup = 2
    submitted = 3
    running = 4
    finished = 5
    precomputed = 6
    error = 98
    unkown = 99



class Scheduler:

    job: Bash.Script = None
    nextJob = None

    # def __int__(self, SLURM_ntasks: int = 1, cpusPerTask: int = 1, SLURM_nnodes: int = None, ngpus: int = 0, SLURM_memPerCPU: float = 2.5):
    def __init__(self, taskList=None, jobDir: Path = None, logDir: Path = None, cpusPerTask=1, cpusTotal=1,
                 memPerCPU=2, minimumMemPerNode=2, partition: str = None, ngpus=None, clobber=False):
        #specify
        self.SLURM_cpusPerTask = cpusPerTask
        self.SLURM_ngpus = ngpus
        self.SLURM_memPerCPU = memPerCPU
        self.SLURM_partition = partition
        self.status = ProcessStatus.notStarted
        self.jobDir = jobDir
        self.clobber = clobber
        self.logDir = logDir

        #calculate
        if ngpus:
            self.SLURM_ntasks = ngpus
        else:
            self.SLURM_ntasks = math.floor(cpusTotal/cpusPerTask)
        self.minCPUsPerNode = math.ceil(minimumMemPerNode / memPerCPU)
        self.SLURM_nnodes = ngpus
        self.taskList = []
        if taskList:
            self.addTasks(taskList)

        #set Empty
        self.job = Bash.Script()
        self.SLURM_jobid = None
        self.SLURM_jobidFound = False
        self.user = None
        self.pickleCallback = None


    def run(self):
        if self.status is ProcessStatus.notStarted:
            self.setupJob()
        if self.status == ProcessStatus.setup:
            self._sbatch()
        else:
            logger.warning(f'Could not run job because of unfit status: {self.status.name}.')

    def setPickleCallback(self, callback):
        self.pickleCallback = callback

    def setupJob(self):
        if self.status != ProcessStatus.notStarted:
            logger.info("Job already setup.")
        else:
            logger.info(f"Setting up job: {self.jobDir}")
            try:
                self.logDir.create()
                self.jobDir.create()
                self.status = ProcessStatus.setup
                self.job.appendJob([task.getCommand() for task in self.taskList if task.shouldRun()])
                self._gpuNodeCheck()
                self._srunify() #srunify must be run before the "wait" line is added, otherwise it would yield "srun wait" and the shell would not actually wait.
                self.job.addPostscript("wait", add=True, mode=List.insert, index=0)
                self.job.addPostscript([task.cleanupCommand for task in self.taskList if task.shouldRun() and task.cleanupCommand is not None], add=True, mode=List.append)
                self.job.addSetup(self.slurmResourceLines(), add=True, mode=List.insert, index=0)
                if not os.path.isdir(self.jobDir):
                    os.mkdir(self.jobDir, mode=0o777)
                self.job.write(os.path.join(self.jobDir, "jobScript.sh"), clobber=True) #maybe clobber=self.clobber
                asyncio.run(self.pickleCallback())
            except Exception as e:
                self.status = ProcessStatus.error
                logger.logExceptionError(f'Job could not be set up, this job and every job after wont run.', e)


    def _gpuNodeCheck(self):
        # check for number of GPUs requested vs nodes and task mismatch and correct if necessary.
        if self.SLURM_ngpus: #and (self.SLURM_nnodes or self.SLURM_ntasks)
            # if not (self.SLURM_ngpus is self.SLURM_nnodes and self.SLURM_ntasks != 1):
            logger.warning("Slurm allocation is trying to use GPUs. Therefore exactly on GPU per node must be allocated with one task per Node. Everything else will lead to uncontrolled shared usage of the GPUs and probably memory overflow errors.")
            logger.warning("Letting number of GPUs dictate everything else.")
            self.SLURM_ntasks = self.SLURM_ngpus
            self.SLURM_nnodes = self.SLURM_ngpus

    def slurmResourceLines(self):
        resourceLines = [""]
        resourceLines.append(f"#SBATCH --job-name={Helper.shorten_name(name=os.path.basename(os.path.normpath(self.jobDir)), n=10)}")
        if self.SLURM_ntasks:
            resourceLines.append(f'#SBATCH --ntasks={self.SLURM_ntasks}')
        if self.SLURM_cpusPerTask:
            resourceLines.append(f'#SBATCH --cpus-per-task={self.SLURM_cpusPerTask}')
        if self.SLURM_nnodes:
            resourceLines.append(f'#SBATCH --nodes={self.SLURM_nnodes}')
        if self.SLURM_memPerCPU:
            resourceLines.append(f'#SBATCH --mem-per-cpu={self.SLURM_memPerCPU}Gb')
        if self.SLURM_ngpus:
            resourceLines.append(f'#SBATCH --gres=gpu:1') #set to 1, because --gres is a per node request. Per Job request is only available in later versions.
        if self.SLURM_partition:
            resourceLines.append(f'#SBATCH --partition={self.SLURM_partition}')
        # use --mincpus flag to specify minimum numer of threads per node, to specify a minimum amount of memory per node.
        # Otherwise, it could happen that a task with 1 cpu and 2Gb of memory is allocated on an extra node and won't run because of memory restrictions.
        # jobs should usually run on shared memory allocation on as little nodes as necessary to have as many jobs as possible run in parallel with enough shared memory to handle memory spikes.
        if self.minCPUsPerNode:
            resourceLines.append(f'#SBATCH --mincpus={self.minCPUsPerNode}')
        if self.logDir:
            resourceLines.append(f'#SBATCH --output={self.logDir.join("output.log")}')
        resourceLines.append("")
        return resourceLines

    def jobSubmitString(self) -> str:
        return f'sbatch {self.job.path}'

    def _salloc(self, attach=True):
        logger.debug(f'Running srun on: {self.job}')
        if self.status is not ProcessStatus.setup:
            logger.warning(
                f'This job is not setup and its current status is: {self.status.name}.Can not continue.')
            return
        try:
            self._gpuNodeCheck()
            logger.process("Trying to allocate resources on the Cluster.")
            # jobSubmitString = self._jobSubmitString(mode="salloc")
            # logger.info(f'salloc String: {jobSubmitString}')
            proc = sps.Popen("srun {self.job.path}", shell=True, stdout=sps.PIPE, stderr=sps.STDOUT)
            self.userJobs()
            self.status = ProcessStatus.submitted
            for line in iter(proc.stdout.readline, b''):
                decoded_line = line.decode('utf-8').rstrip('\n')
                logger.info(decoded_line)
                if not self.SLURM_jobidFound:
                    m = re.match(r'salloc: Granted job allocation ([0-9]+)', decoded_line)
                    if m:
                        self.SLURM_jobid = m.group(1)
                        self.SLURM_jobidFound = True
                        logger.info(f'Job Id: {self.SLURM_jobid}')
                        self.status = ProcessStatus.running
                        if not attach:
                            break

            if attach:
                returncode = proc.wait()
                if returncode == 0:
                    logger.info(f'Job finished: {self.job}')
                    self.status = ProcessStatus.finished
                else:
                    logger.info(f'Job failed: {self.job}')
                    self.status = ProcessStatus.error

                logger.info(f'Returncode: {proc.returncode}')
                asyncio.run(self.pickleCallback())
                self.jobPostMortem()
        except Exception as e:
            self.status = ProcessStatus.error
            asyncio.run(self.pickleCallback())
            logger.logExceptionCritical(f"Could not allocate the following resources: {str(self)}", e)

    def _sbatch(self):
        #this function only submits, any checks and additions should be done in run.
        logger.debug(f'Running sbatch on: {self.job}')
        if not self.job.path:
            logger.error(f' File not written to disk yet, nothing to sbatch for job: {self.job.path}.')
        try:
            logger.process("Trying to allocate resources on the Cluster.")
            proc = sps.Popen(f"sbatch {self.job.path}", shell=True, stdout=sps.PIPE, stderr=sps.STDOUT)
            self.userJobs()
            for line in iter(proc.stdout.readline, b''):
                decoded_line = line.decode('utf-8').rstrip('\n')
                logger.info(decoded_line)
                if not self.SLURM_jobidFound:
                    m = re.match(r'Submitted batch job ([0-9]+)', decoded_line)
                    if m:
                        self.SLURM_jobid = m.group(1)
                        self.SLURM_jobidFound = True
                        logger.info(f'Job Id: {self.SLURM_jobid}')

            returncode = proc.wait()
            if returncode == 0:
                logger.info(f'Job submitted: {self.job.path}')
                self.status = ProcessStatus.submitted
            else:
                logger.info(f'Job failed: {self.job.path}')
                self.status = ProcessStatus.error

            logger.info(f'Returncode: {proc.returncode}')
            asyncio.run(self.pickleCallback())
            self.jobPostMortem()
        except Exception as e:
            self.status = ProcessStatus.error
            asyncio.run(self.pickleCallback())
            logger.logExceptionCritical(f"Could not allocate the following resources: {str(self)}", e)

    def addJob(self, job: str):
        if self.status == ProcessStatus.notStarted:
            self.job.appendJob(job)
            asyncio.run(self.pickleCallback())
        else:
            logger.warning(f"Job already set up or started. Can not add additional job lines after setup. Job status: {self.status}")
            logger.warning(f"The following lines were not appended: \n{job}")

    def addTasks(self, tasks):
        tasks = Helper.ensure_list(tasks)
        for task in tasks:
            if not isinstance(task, Task):
                logger.error(f"Could not add task to tasklist because task is not of class Task: {type(Task)}")
            else:
                if len(self.taskList) > 0 and (not isinstance(task, type(self.taskList[0]))):
                    logger.error(f"The new instance is not of the same type as the instances in the list: {type(task)} and {type(self.taskList[0])}")
                else:
                    self.taskList.append(task)

    def jobPostMortem(self):
        sleep(0.5)
        if not logger.level >= logger.DEBUG:
            return
        if not self.SLURM_jobid:
            logger.warning("Job ID is not set, probably because job was not run. Cant call post mortem.")
        logger.info('############################ POST MORTEM ############################')
        proc = sps.Popen(f'sacct -j {self.SLURM_jobid} --format=JobID,Start,End,Elapsed,NCPUS', shell=True, stdout=sps.PIPE, stderr=sps.STDOUT)
        for line in iter(proc.stdout.readline, b''):
            # logger.info(line.decode('utf-8'))
            decoded_line = line.decode('utf-8').rstrip('\n')
            logger.info(decoded_line)
        proc.wait()
        logger.info('#####################################################################')

    def setPrecomputed(self):
        self.status = ProcessStatus.precomputed
        asyncio.run(self.pickleCallback())
        logger.debug('Setting task state to precomputed: {}'.format(self.status))

    def setNotStarted(self, skipPickle: bool = False):
        self.status = ProcessStatus.notStarted
        if not skipPickle:
            asyncio.run(self.pickleCallback())
        logger.debug('Setting task state to precomputed: {}'.format(self.status))

    def updateSlurmStatus(self):
        if self.status == ProcessStatus.precomputed:
            logger.debug("Not updating slurm status because Task state is precomputed.")
            return
        if not self.SLURM_jobid:
            logger.debug("Job ID is not set, probably because job was not run yet. Cant return Slurm Status")
            logger.debug(f'Job status of {self.jobDir}: {self.status}')
            return
        oldStatus = self.status
        proc = sps.Popen(f"sacct -j {self.SLURM_jobid} --format=State", shell=True,
                         stdout=sps.PIPE, stderr=sps.STDOUT)
        decoded_lines = []
        for line in iter(proc.stdout.readline, b''):
            decoded_lines.append(line.decode('utf-8').rstrip('\n'))
        if len(decoded_lines) > 3:
            statusCode = decoded_lines[2].strip()
            if statusCode == "COMPLETED":
                self.status = ProcessStatus.finished
            elif statusCode == "RUNNING":
                self.status = ProcessStatus.running
            elif statusCode == "FAILED":
                self.status = ProcessStatus.error
            else:
                self.status = ProcessStatus.unkown
            logger.info(f'Job status of {self.jobDir}: {self.status}')
        if self.status != oldStatus:
            asyncio.run(self.pickleCallback())
        else:
            logger.info("Something went wrong with sacct output, maybe cluster is to slow.")
            logger.info(f'Job status of {self.jobDir}: {self.status}')
            logger.info("sacct output was:")
            logger.info(decoded_lines)

    def userJobs(self):
        sleep(0.5)
        if not logger.level >= logger.DEBUG:
            return
        if not self.user:
            self.getUser()

        logger.info('############################ YOUR JOBS ############################')
        proc = sps.Popen(f'squeue -u  {self.user}', shell=True, stdout=sps.PIPE, stderr=sps.STDOUT)
        for line in iter(proc.stdout.readline, b''):
            # logger.info(line.decode('utf-8'))
            decoded_line = line.decode('utf-8').rstrip('\n')
            logger.info(decoded_line)
        proc.wait()
        logger.info('###################################################################')

    def getUser(self):
        self.user = sps.run("whoami", shell=True, capture_output=True).stdout.decode('utf-8')

    def _srunify(self):
        for index, command in enumerate(self.job.jobLines):
            if not command.startswith("srun"):
                self.job.jobLines[index] = f"srun -n 1 --mem=0 --exclusive " + command + " &"

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
               Job String: {self.jobSubmitString()}"""
