from mrpipe.meta import loggerModule
from mrpipe.schedueler import PipeJob
from typing import List
import pickle

logger = loggerModule.Logger()


class Pipe:
    def __init__(self, name: str, dir: str, maxcpus: int = 1, maxMemory: int = 2):
        self.dir = dir
        self.name = name
        self.jobList:List[PipeJob.PipeJob] = []
        self.maxcpus = maxcpus
        self.maxMemory = maxMemory

    def appendJob(self, job: PipeJob.PipeJob):
        if isinstance(job, list):
            for el in job:
                logger.debug(f"Appending Job to Pipe ({self.name}): \n{el}")
                self.jobList.append(el)
        elif isinstance(job, PipeJob.PipeJob):
            logger.debug(f"Appending Job to Pipe ({self.name}): \n{job}")
            self.jobList.append(job)
        else:
            logger.error(f"Can only add PipeJobs or [PipeJobs] to a Pipe ({self.name}). You provided {type(job)}")

    def configure(self):
        pass

    def run(self):
        pass