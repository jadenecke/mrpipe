from mrpipe.meta import loggerModule
from mrpipe.schedueler import Slurm
import os
import pickle

logger = loggerModule.Logger()

class PipeJob:
    def __init__(self, name: str, job: Slurm.Scheduler):
        #settable
        self.name = name
        self.job = job

        #unsettable
        self.picklePath = os.path.join(name, "PipeJob.pkl")
        self._nextJob = None
        self._dependencies: PipeJob = None
        logger.debug(f"Created PipeJob, {self}")



    @classmethod
    def fromPickled(cls, path: str):
        logger.debug(f'Trying to load pickled job from path: {path}')
        try:
            with open(path, 'rb') as file:
                loadedPickle = pickle.load(file)
                logger.debug(f'Job successfully unpickled:\n{loadedPickle}')
                return loadedPickle
        except Exception as e:
            logger.logExceptionCritical("Was not able to load the pickled job. Pipe breaks here and now.", e)

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
        self.job.run()


    def pickleJob(self) -> None:
        logger.debug(f'Pickling Job:\n{self}')
        try:
            with open(self.picklePath, "wb") as file:
                pickle.dump(obj=self, file=file)
            logger.debug(f'Job successfully pickled:\n{self.picklePath}')
        except Exception as e:
            logger.logExceptionCritical("Was not able to pickle the job. The Pipe will break before this job.", e)

    def setNextJob(self, job, overwrite: bool = False):
        if self._nextJob and not overwrite:
            logger.warning(f"Next job already set and overwrite is False: {self}")
        if isinstance(job, PipeJob):
            logger.debug(f"Setting Next Job for {self.name}: \n{job}")
            self._nextJob = job.picklePath
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
        if isinstance(job, list):
            for el in job:
                logger.debug(f"Appending Job Dependency to {self.name}: \n{el}")
                self._dependencies.append(el.picklePath)
        elif isinstance(job, PipeJob):
            logger.debug(f"Appending Job Dependency to {self.name}: \n{job}")
            self._dependencies.append(job.picklePath)
        else:
            logger.error(f"Can only append PipeJobs or [PipeJobs] as dependency to PipeJob: {self.name}. You provided {type(job)}")

    def checkDependencies(self):
        # Returns paths of picklejobs required to run before this one can run
        notRun = []
        for dep in self._dependencies:
            depJob = PipeJob.fromPickled(dep)
            if depJob.job.status == Slurm.ProcessStatus.notRun:
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
        return self.job.status != Slurm.ProcessStatus.notRun

    def __str__(self):
        return f'Job Name: {self.name}\nJob Path: {self.picklePath}\nJob: {self.job}\nFollow-up Job: {self._nextJob}\nJob Status: {self.getJobStatus()}'
