from mrpipe.meta import loggerModule
from mrpipe.schedueler import Slurm
import os
import pickle
import asyncio

logger = loggerModule.Logger()

class PipeJob:

    pickleNameStandard = "PipeJob.pkl"
    def __init__(self, name: str, job: Slurm.Scheduler, jobDir: str):
        #settable
        self.name = name
        self.job = job
        self.job.jobDir = os.path.join(jobDir, name)

        #unsettable
        self.job.setPickleCallback(self.pickleCallback)
        self.picklePath = os.path.join(self.job.jobDir, PipeJob.pickleNameStandard)
        self._nextJob = None
        self._dependencies: PipeJob = []
        logger.debug(f"Created PipeJob, {self}")

    @classmethod
    def fromPickled(cls, path: str, pickleName:str=None):
        if not pickleName:
            pickleName = PipeJob.pickleNameStandard
        logger.debug(f'Trying to load pickled job from path: {os.path.join(path, pickleName)}')
        try:
            with open(os.path.join(path, pickleName), 'rb') as file:
                loadedPickle = pickle.load(file)
                logger.debug(f'Job successfully unpickled:\n{loadedPickle}')
                return loadedPickle
        except Exception as e:
            logger.logExceptionCritical("Was not able to load the pickled job. Pipe breaks here and now.", e)

    def createJobDir(self):
        if not os.path.isdir(self.job.jobDir):
            os.mkdir(self.job.jobDir, mode=0o777)

    def runJob(self):
        logger.debug(f"Trying to run the following job: {self.name}")
        if self.hasJobStarted():
            logger.warning(f"Job already started. Not running again. Current job status: {self.getJobStatus()}")
            return None
        dependentJobs = self.checkDependencies()
        if dependentJobs:
            logger.warning("Job dependencies not fulfilled. Not running. Returning dependencies")
            logger.warning(dependentJobs)
            return dependentJobs
        if self._nextJob:
            self.job.job.addPostscript(f'mrpipe.py step {self._nextJob}')
        self.job.run()

    def _pickleJob(self) -> None:
        logger.debug(f'Pickling Job:\n{self}')
        try:
            self.createJobDir()
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
            logger.debug(f"Setting Next Job for {self.name}: \n{job.name}")
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

    def setDependencies(self, job) -> None:
        if isinstance(job, PipeJob):
            job = [job]
        if isinstance(job, list):
            for el in job:
                if isinstance(el, PipeJob):
                    logger.debug(f"Appending Job Dependency to {self.name}: \n{el.name}")
                    self._dependencies.append(el.job.jobDir)
                else:
                    logger.error(
                        f"Can only append PipeJobs or [PipeJobs] as dependency to PipeJob: {self.name}. You provided {type(el)}")
            self._pickleJob()
        else:
            logger.error(f"Can only append PipeJobs or [PipeJobs] as dependency to PipeJob: {self.name}. You provided {type(job)}")

    def checkDependencies(self):
        # Returns paths of picklejobs required to run before this one can run
        notRun = []
        for dep in self._dependencies:
            depJob = PipeJob.fromPickled(dep)
            if depJob.job.status == Slurm.ProcessStatus.notStarted:
                notRun.append(depJob.job.picklePath)
            elif depJob.job.status != Slurm.ProcessStatus.finished:
                logger.error("Dependency Job is either still running or failed. Will no start dependency again. This probably will result in a failing pipeline.")
                logger.error(f"Job to run: \n{self}")
                logger.error(f"Dependency Job: \n{depJob}")
        notRunString = "\n".join(notRun)
        logger.info(f"Dependency Jobs not run to {self.name}: \n{notRunString}")
        return notRun


    def getJobStatus(self):
        return self.job.status

    def hasJobStarted(self) -> bool:
        return self.job.status != Slurm.ProcessStatus.notStarted

    def __str__(self):
        return f'Job Name: {self.name}\nJob Path: {self.picklePath}\nJob: {self.job}\nFollow-up Job: {self._nextJob}\nJob Status: {self.getJobStatus()}'
