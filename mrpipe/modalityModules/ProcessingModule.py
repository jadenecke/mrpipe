from typing import List
from abc import ABC, abstractmethod
from mrpipe.meta.PathClass import Path
from mrpipe.schedueler.PipeJob import PipeJob
from mrpipe.meta.Session import Session
from mrpipe.meta import loggerModule

logger = loggerModule.Logger()


class ProcessingModule(ABC):
    # subclass should override this:
    requiredModalities = None
    optionalModalities = None

    def __init__(self, name: str, sessionList: List[Session], jobDir: Path, args):
        # ProcessingModule ABC implements init function, the child modules should not implement it themselves. I think. For now.
        self.moduleName = name
        self.sessions = sessionList
        self.jobDir = jobDir.join(name)
        self.args = args

        # unsettable:
        self.pipeJobs: List[PipeJob] = []


    def addPipeJob(self, job: PipeJob, keepVerbosity: bool = False):
        if not keepVerbosity:
            job.setVerbosity(self.args.verbosity)
        job.setJobDir(self.jobDir)
        self.pipeJobs.append(job)

    @abstractmethod
    def setup(self):
        pass

    def verify(self, availableModalities: List[str]):
        for required in self.requiredModalities:
            if required not in availableModalities:
                return False
        for optional in self.optionalModalities:
            if optional not in availableModalities:
                logger.warning(
                    f"Required modality {optional} not in available modalities {availableModalities}. Skipping some part of the processing module.")
        return True

    def verifySessions(self):
        for session in self.sessions:
            if not self.requiredModalities in session.modalities.available_modalities():
                self.sessions.remove(session)
                logger.warning(f'Required Modalities {self.requiredModalities} not found for session: {session.path}')

    def __str__(self):
        return self.moduleName
