from mrpipe.meta import loggerModule
from mrpipe.schedueler import Slurm
import pickle

logger = loggerModule.Logger()

class PipeJob:
    def __init__(self, name: str, job: Slurm.Scheduler, picklePath: str):
        self.name = name
        self.job = job
        self.picklePath = picklePath
        self.nextJob = None
        logger.debug(f"Created PipeJob, {self}")


    @classmethod
    def fromPickled(cls, path: str):
        logger.debug(f'Trying to load pickled job from path: {path}')
        try:
            with (open(path, 'rb') as file):
                loadedPickle = pickle.load(file)
                logger.debug(f'Job successfully unpickled:\n{loadedPickle}')
                return loadedPickle
        except Exception as e:
            logger.logExceptionCritical("Was not able to load the pickled job. Pipe breaks here and now.", e)


    def pickleJob(self):
        logger.debug(f'Pickling Job:\n{self}')
        try:
            with open(self.picklePath, "wb") as file:
                pickle.dump(obj=self, file=file)
            logger.debug(f'Job successfully pickled:\n{self.picklePath}')
        except Exception as e:
            logger.logExceptionCritical("Was not able to pickle the job. The Pipe will break before this job.", e)

    def __str__(self):
        return f'Job Name: {self.name}\nJob Path: {self.picklePath}\nJob: {self.job}\nFollow-up Job: {self.nextJob}'
