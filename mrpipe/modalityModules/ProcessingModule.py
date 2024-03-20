import sys
from typing import List
from abc import ABC, abstractmethod
from mrpipe.meta.PathClass import Path
from mrpipe.schedueler.PipeJob import PipeJob
from mrpipe.meta.Session import Session
from mrpipe.meta import loggerModule
from mrpipe.modalityModules.PathDicts.BasePaths import PathBase
from mrpipe.Toolboxes.envs.envs import Envs
from mrpipe.modalityModules.PathDicts.LibPaths import LibPaths

logger = loggerModule.Logger()


class ProcessingModule(ABC):
    # subclass should override this:
    requiredModalities = None
    optionalModalities = None

    def __init__(self, name: str, sessionList: List[Session], basepaths: PathBase, libPaths: LibPaths, args):
        # ProcessingModule ABC implements init function, the child modules should not implement it themselves. I think. For now.
        self.moduleName = name
        self.sessions = sessionList
        self.basepaths = basepaths
        self.args = args
        self.isSetup = False
        self.libpaths = libPaths

        # unsettable:
        self.envs = Envs(self.libpaths)
        self.jobDir = self.basepaths.pipeJobPath.join(name)
        self.pipeJobs: List[PipeJob] = []

    @classmethod
    def verifyModalities(cls, availableModalities: List[str]): #this throws an error because it takes the parent class and not the child class. (Nope, seems to be fixed.)
        for required in cls.requiredModalities:
            if required not in availableModalities:
                return False
        if cls.optionalModalities:
            for optional in cls.optionalModalities:
                if optional not in availableModalities:
                    logger.warning(
                        f"Required modality {optional} not in available modalities {availableModalities}. Skipping some part of the processing module.")
        return True

    @classmethod
    def verifyInputFilesForSession(cls):
        #TODO verify for each session that for all pipejobs the required input files are either there or are beeing created from other pipejobs, i.e. are output files.
        pass

    def addPipeJob(self, job: PipeJob, keepVerbosity: bool = False):
        if not keepVerbosity:
            job.setVerbosity(self.args.verbose)
        job.setJobDir(self.jobDir)
        self.pipeJobs.append(job)

    def safeSetup(self) -> bool:
        kept_sessions = []
        for session in self.sessions:
            for modality in self.requiredModalities:
                if not session.subjectPaths.checkPathsConfigured(modality):
                    logger.warning(f"Session {session} has no configured paths for this processing module ({self.moduleName}). Its very likely that the modality is missing for this session. Removing session from processing module. Session path is: {session.path}.")
                    self.sessions.remove(session)
                else:
                    kept_sessions.append(session)
                logger.info(f"Session {session} has configured paths for modality {modality}: {str(session.subjectPaths.__dict__.get(modality))}")

        if not kept_sessions:
            logger.critical(f"No subjects could be configured for this module. This is very likely a missmatch between the modality name set in ModalityNames.yml and the actual directory name. Please double check that the directories are spelled correctly. If you didn't change the file, you might also try to delete it and rerun the configuration. There is also the very unlikely chance that the subject paths were not configured before the Processing Module ({self.moduleName}). In this case the processing module code is wrong.")
            sys.exit(3)
        else:
            self.sessions = kept_sessions
        return self.setup()

    @abstractmethod
    def setup(self) -> bool:
        #do setup in child class
        self.isSetup = True
        return True


    def getJobs(self) -> List[PipeJob]:
        if not self.isSetup:
            logger.warning(f"{self} has not been setup yet. Trying to run setup, but might fail.")
            self.isSetup = self.setup()
        if not self.isSetup:
            logger.error(f"{self} Was not able to complete setup. Returning no jobs")
            return None
        return self.pipeJobs



    def verifySessions(self):
        for session in self.sessions:
            if not self.requiredModalities in session.modalities.available_modalities():
                self.sessions.remove(session)
                logger.warning(f'Required Modalities {self.requiredModalities} not found for session: {session.path}')

    def __str__(self):
        return self.moduleName
