from __future__ import annotations
from time import sleep
from mrpipe.Toolboxes.Task import TaskStatus
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
        self.filteredPrecomputedTasks = False
        self._nextJob: PipeJob = None
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

    def createJobDir(self) -> bool:
        try:
            if not self.job.jobDir.exists(acceptCache=False):
                os.makedirs(self.job.jobDir, mode=0o777, exist_ok=True)
            return True
        except Exception as e:
            logger.logExceptionCritical("Could not create Job Dir", e)
            return False

    def setVerbosity(self, level: int):
        self.verbose = level

    def setJobDir(self, jobDir: Path):
        if not self.job.jobDir:
            self.job.jobDir = jobDir
        else:
            #TODO: This should probably be reverted to logger.warning or an actual error, because it effects the user if the module name is changed. However for now i muted it because this gets also triggered by the load/configure step when running the pipeline.
            logger.info(f'Job dir already set: {self.job.jobDir}. Not changing.')

    def runJob(self):
        logger.info(f"Trying to run the following job: {self.name}")
        if self.hasJobStarted():
            logger.warning(f"Job already started. Not running again. Current job status: {self.getJobStatus()}")
            return None
        dependentJobs = self.checkDependencies()
        if dependentJobs:
            logger.error("Job dependencies not fulfilled. Not running. Returning dependencies")
            logger.error(dependentJobs)
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
        self.filterPrecomputedTasks()

        for task in self.job.taskList:
            task.createOutDirs()
        self.job.run()

    def filterPrecomputedTasks(self, refilter=False):
        if self.filteredPrecomputedTasks and not refilter:
            return
        if not self.recompute:
            for index, task in enumerate(self.job.taskList):
                if task.checkIfDone():
                    logger.info(
                        f"Removing task from tasklist because its output files already exists. Task name: {self.name}")
            self.filteredPrecomputedTasks = True
        return

    def allTasksPrecomputed(self) -> bool:
        self.filterPrecomputedTasks()
        if self.recompute:
            return False
        stateVector = [task.getState() is TaskStatus.isPreComputed for task in self.job.taskList]
        isPrecomputed = all(stateVector)
        if isPrecomputed:
            self.job.setPrecomputed()
        return isPrecomputed

    def _pickleJob(self) -> None:
        logger.debug(f'Pickling Job:\n{self}')
        try:
            self.createJobDir()
            counter = 0
            while not (self.job.jobDir.exists(acceptCache=False) or counter >= 100): #wait until directory is actually created.
                counter += 1
                sleep(0.01)
            if not self.job.jobDir.exists(acceptCache=True):
                if not self.createJobDir():
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

    def getNextJob(self) -> PipeJob or None:
        if not self._nextJob:
            logger.warning(f"Next job not set for:\n{self}")
            return None
        else:
            return PipeJob.fromPickled(self._nextJob)

    def removeNextJob(self):
        logger.info(f"Removing next job from: \n{self}")
        self._nextJob = None
        self._pickleJob()


    def getNextJobPath(self):
        if not self._nextJob:
            logger.warning(f"Next job not set for:\n{self}")
            return None
        else:
            return self._nextJob.picklePath

    def getTaskInFiles(self, excludePrecomputed: bool = False):
        if excludePrecomputed:
            inFileList = Helper.ensure_list([task.inFiles for task in self.job.taskList if task.state is not TaskStatus.isPreComputed], flatten=True)
        else:
            inFileList = Helper.ensure_list([task.inFiles for task in self.job.taskList], flatten=True)
        return inFileList

    def getFirstTaskInFiles(self):
        if self.job.taskList is not None and len(self.job.taskList) > 0:
            infiles = self.job.taskList[0].inFiles
            return Helper.ensure_list([infiles], flatten=True)
        else:
            return []

    def getTaskOutFiles(self, excludePrecomputed: bool = False):
        if excludePrecomputed:
            outFileList = Helper.ensure_list([task.outFiles for task in self.job.taskList if task.getState() is not TaskStatus.isPreComputed], flatten=True)
        else:
            outFileList = Helper.ensure_list([task.outFiles for task in self.job.taskList], flatten=True)
        return outFileList

    def setDependencies(self, job) -> None:
        job = Helper.ensure_list(job)
        if isinstance(job, list):
            for el in job:
                if isinstance(el, PipeJob):
                    if el.job.jobDir in self._dependencies:
                        logger.debug(f"Skipping dependency {el}, already set as dependency job to {self}")
                    else:
                        logger.info(f"Appending Job Dependency to {self.name}: {el.name}")
                        self._dependencies.append(el.job.jobDir)
                        self._pickleJob()
                else:
                    logger.error(
                        f"Can only append PipeJobs or [PipeJobs] as dependency to PipeJob: {self.name}. You provided {type(el)}")
        else:
            logger.error(f"Can only append PipeJobs or [PipeJobs] as dependency to PipeJob: {self.name}. You provided {type(job)}")

    def isDependency(self, job) -> bool:
        if isinstance(job, PipeJob):
            return job.job.jobDir in self._dependencies
        else:
            logger.error(
                f"Can only check for dependencies if a PipeJob is provided: {self.name}. You provided {type(job)}")
            return None

    def checkDependencies(self):
        # Returns paths of picklejobs required to run before this one can run
        notRun = []
        logger.debug(f"Job to run: \n{self}")
        for dep in self._dependencies:
            depJob = PipeJob.fromPickled(dep)
            depJob.job.updateSlurmStatus()
            if depJob.job.status in [Slurm.ProcessStatus.notStarted, Slurm.ProcessStatus.setup]:
                notRun.append(depJob.picklePath)
            elif depJob.job.status in [Slurm.ProcessStatus.finished, Slurm.ProcessStatus.precomputed]:
                logger.debug(f"Finished or precomputed dependency Job: \n{depJob}")
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

    def setRecomputeDependencies(self):
        #DONT - TODO run only if anything is set to precomputed. / This is wrong because if one subject/Task is missing and another should be recomputed, this will avoid checking for the task that should be recomputed.
        #inFiles = self.getTaskInFiles()
        dependencies = self.getDependencies()
        if not dependencies:
            logger.debug(f"No dependencies found for {self.name}")
            return
        computedOutputFilesOfDependencies = Helper.ensure_list([
            PipeJob.fromPickled(dependency).getTaskOutFiles(excludePrecomputed=True) for dependency in dependencies
        ], flatten=True)
        if not computedOutputFilesOfDependencies:
            logger.debug(f"No computed output files found for any of the dependencies {self.name}")
            return
        computedOutputFilesOfDependencies = [str(file) for file in computedOutputFilesOfDependencies]
        logger.debug(f"Checking dependencies for {self.name}")
        logger.debug(f"Dependencies: {dependencies}")
        logger.debug(f"Checking if any of these files are a dependency of the current job: {computedOutputFilesOfDependencies}")
        for task in self.job.taskList:
            if task.state is not TaskStatus.isPreComputed:
                continue
            logger.debug(f"Checking whether the following input files are part of the computed output files: {task.inFiles}")
            searchVector = [str(file) in computedOutputFilesOfDependencies for file in task.inFiles]
            logger.debug(f"SearchVector: {searchVector}")
            if any(searchVector):
                logger.info(f"Task {self.name} relies on input of dependency which does not exist yet but task state is precomputed. Will recompute current task with new input of depdendency {dependencies}")
                task.setStateRecompute()
                self.job.setNotStarted(skipPickle=True)
                task.clobber = True
            else:
                logger.debug(f"No changes found in dependencies, so recomputing task is not necessary ({self.name})")
        self._pickleJob()
