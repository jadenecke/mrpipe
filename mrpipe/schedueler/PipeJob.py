from time import sleep

from mrpipe.Helper import Helper
from mrpipe.meta import LoggerModule
from mrpipe.schedueler import Slurm
from mrpipe.meta.PathClass import Path
import os
import pickle
from typing import List
from mrpipe.Toolboxes.envs import EnvClass
from mrpipe.modalityModules.PathDicts.BasePaths import PathBase

logger = LoggerModule.Logger()

class PipeJob:

    pickleNameStandard = "PipeJob.pkl"
    def __init__(self, name: str, job: Slurm.Scheduler, basepaths: PathBase, moduleName: str, env: EnvClass = None, verbose:int = 0, recompute = False):
        #settable
        self.name = name
        self.job = job
        self.basepaths = basepaths
        self.verbose = verbose
        self.env = env
        self.recompute = recompute
        self.moduleName = moduleName

        #unsettable
        self.job.jobDir = self.basepaths.pipeJobPath.join(moduleName).join(name, isDirectory=True)
        self.job.logDir = self.basepaths.logPath.join(moduleName).join(name, isDirectory=True)
        self.dag_visited = False
        self.dag_processing = False
        self.job.setPickleCallback(self.pickleCallback)
        self.picklePath = os.path.join(self.job.jobDir, PipeJob.pickleNameStandard)
        self._nextJob = None
        self._dependencies: List[str] = []
        logger.debug(f"Created PipeJob, {self}")

    @classmethod
    def fromPickled(cls, path: str, pickleName:str=None):
        if not pickleName:
            pickleName = PipeJob.pickleNameStandard
        logger.info(f'Trying to load pickled job from path: {os.path.join(path, pickleName)}')
        try:
            with open(os.path.join(path, pickleName), 'rb') as file:
                loadedPickle = pickle.load(file)
                logger.debug(f'Job successfully unpickled:\n{loadedPickle}')
                loadedPickle.job.updateSlurmStatus()
                return loadedPickle
        except Exception as e:
            logger.logExceptionCritical("Was not able to load the pickled job. Pipe breaks here and now.", e)

    def createJobDir(self):
        if not self.job.jobDir.exists(acceptCache=False):
            os.makedirs(self.job.jobDir, mode=0o777, exist_ok=True)

    def setVerbosity(self, level: int):
        self.verbose = level

    def setJobDir(self, jobDir: Path):
        if not self.job.jobDir:
            self.job.jobDir = jobDir
        else:
            #TODO: This should probably be reverted to logger.warning or an actual error, because it affects the user if the module name is changed. However for now i muted it because this gets also triggered by the load/configure step when running the pipeline.
            logger.info(f'Job dir already set: {self.job.jobDir}. Not changing.')

    def runJob(self):
        logger.info(f"Trying to run the following job: {self.name}")
        if self.hasJobStarted():
            logger.warning(f"Job already started. Not running again. Current job status: {self.getJobStatus()}")
            return None
        dependentJobs = self.checkDependencies()
        if dependentJobs:
            logger.warning("Job dependencies not fulfilled. Not running. Returning dependencies")
            logger.warning(dependentJobs)
            return dependentJobs
        if self.env:
            self.job.job.addSetup(self.env.getSetup(), add=True, mode=List.insert, index=0)
        else:
            self.job.job.addSetup(EnvClass.EnvClass().getSetup(), add=True, mode=List.insert, index=0)
        if logger.level <= logger.INFO:
            self.job.job.addSetup("echo $PATH", add=True)
            self.job.job.addSetup("conda info", add=True)
            self.job.job.addSetup("conda list", add=True)
        if self._nextJob:
            # modulepath = os.path.dirname(inspect.getfile(mrpipe))
            self.job.job.addPostscript(["source deactivate", "source activate mrpipe"], add=True)
            self.job.job.addPostscript(f"""{os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "mrpipe.py")} step {self._nextJob}{f" -{'v'*self.verbose}" if self.verbose else ''}""", add=True)

        for index, task in enumerate(self.job.taskList):
            if (not task.verifyInFiles()) and (not task.verifyOutFiles()):
                logger.error(f"Removing task from tasklist because files could not be verified. Task name: {task.name}")
                self.job.taskList.remove(task)

        #Do task setup, i.e. remove output files if clobber is true, because not every job supports clobber
        for task in self.job.taskList:
            task.preRunCheck()

        if not self.recompute:
            for index, task in enumerate(self.job.taskList):
                if task.checkIfDone():
                    logger.process(
                        f"Removing task from tasklist because its output files already exists. Task name: {task.name}")
                    task.setStatePrecomputed()
        for task in self.job.taskList:
            task.createOutDirs()
        self.job.run()

    def _pickleJob(self) -> None:
        logger.debug(f'Pickling Job:\n{self}')
        try:
            self.createJobDir()
            counter = 0
            while not (self.job.jobDir.exists(acceptCache=True) or counter >= 100): #wait until directory is actually created.
                counter += 1
                sleep(0.01)
            if not self.job.jobDir.exists(acceptCache=True):
                logger.error(f"Could not create job. Job dir: {self.job.jobDir}, Job could not be pickled. Job name: {self}. This will likely break the pipeline during processing.")
            else:
                with open(self.picklePath, "wb") as file:
                    pickle.dump(obj=self, file=file)
                logger.debug(f'Job successfully pickled:\n{self.picklePath}')
        except Exception as e:
            logger.logExceptionCritical("Was not able to pickle the job. The Pipe will break before this job.", e)

    async def pickleCallback(self):
        self._pickleJob()

    def setNextJob(self, job, overwrite: bool = False):
        if self._nextJob and not overwrite:
            logger.warning(f"Next job already set and overwrite is False: {self}")
        if isinstance(job, PipeJob):
            logger.info(f"Setting Next Job for {self.name}: {job.name}")
            self._nextJob = job.job.jobDir
            self._pickleJob()
        else:
            logger.error(f"Can only set PipeJobs as follow-up job to PipeJob: {self.name}. You provided {type(job)}")

    def getNextJob(self):
        if not self._nextJob:
            logger.warning(f"Next job not set: {self}")
            return None
        else:
            return PipeJob.fromPickled(self._nextJob)

    def getNextJobPath(self):
        if not self._nextJob:
            logger.warning(f"Next job not set: {self}")
            return None
        else:
            return self._nextJob

    def getTaskInFiles(self):
        return Helper.ensure_list([task.inFiles for task in self.job.taskList], flatten=True)

    def getTaskOutFiles(self):
        return Helper.ensure_list([task.outFiles for task in self.job.taskList], flatten=True)

    def setDependencies(self, job) -> None:
        job = Helper.ensure_list(job)
        if isinstance(job, list):
            for el in job:
                if isinstance(el, PipeJob):
                    logger.info(f"Appending Job Dependency to {self.name}: {el.name}")
                    self._dependencies.append(el.job.jobDir)
                else:
                    logger.error(
                        f"Can only append PipeJobs or [PipeJobs] as dependency to PipeJob: {self.name}. You provided {type(el)}")
            self._pickleJob()
        else:
            logger.error(f"Can only append PipeJobs or [PipeJobs] as dependency to PipeJob: {self.name}. You provided {type(job)}")


    def isDependency(self, job) -> bool:
        if isinstance(job, PipeJob):
            return job.job.jobDir in self._dependencies
        else:
            logger.error(
                f"Can only check for dependencies if a PipeJob is provided: {self.name}. You provided {type(el)}")
            return None

    def checkDependencies(self):
        # Returns paths of picklejobs required to run before this one can run
        notRun = []
        logger.error(f"Job to run: \n{self}")
        for dep in self._dependencies:
            depJob = PipeJob.fromPickled(dep)
            depJob.job.updateSlurmStatus()
            if depJob.job.status in [Slurm.ProcessStatus.notStarted, Slurm.ProcessStatus.setup]:
                notRun.append(depJob.job.picklePath)
            elif depJob.job.status == Slurm.ProcessStatus.finished:
                logger.error(f"Dependency Job: \n{depJob}")
            else:
                logger.error(
                    "Dependency Job is either still running or failed. Will no start dependency again. This probably will result in a failing pipeline.")
                logger.error(f"Dependency Job: \n{depJob}")
        notRunString = "\n".join(notRun)
        logger.debug(f"Dependency Jobs not run to {self.name}: \n{notRunString}")
        return notRun

    def getDependencies(self):
        return self._dependencies

    def getJobStatus(self):
        self.job.updateSlurmStatus()
        return self.job.status

    def hasJobStarted(self) -> bool:
        return self.job.status not in [Slurm.ProcessStatus.notStarted, Slurm.ProcessStatus.setup]


    def __str__(self):
        return f'Job Name: {self.name}\nJob Path: {self.picklePath}\nJob: {self.job}\nFollow-up Job: {self._nextJob}\nJob Status: {self.getJobStatus()}'
