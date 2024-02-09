from mrpipe.meta import loggerModule
from mrpipe.schedueler import PipeJob
import pickle

logger = loggerModule.Logger()


class Pipe:
    def __init__(self, name: str, dir: str):
        self.dir = dir
        self.name = name
        self.jobList = []

    def appendJob(self, job: PipeJob):
        if isinstance(job, list):
            for el in job:
                logger.debug(f"Appending Job to Pipe ({self.name}): \n{el}")
                self.jobList.append(el.picklePath)
        elif isinstance(job, PipeJob):
            logger.debug(f"Appending Job to Pipe ({self.name}): \n{job}")
            self.jobList.append(job.picklePath)
        else:
            logger.error(f"Can only add PipeJobs or [PipeJobs] to a Pipe ({self.name}). You provided {type(job)}")

    def configure(self):
        pass

    def run(self):
        pass