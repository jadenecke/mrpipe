from mrpipe.meta import loggerModule
from mrpipe.schedueler import PipeJob
import pickle

logger = loggerModule.Logger()


class Pipe:
    def __init__(self, dir: str):
        self.dir = dir
        self.jobList = []

    def appendJob(self, job: PipeJob):
        pass

