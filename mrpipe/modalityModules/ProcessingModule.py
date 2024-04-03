import sys
from typing import List
from abc import ABC, abstractmethod
from mrpipe.meta.PathClass import Path
from mrpipe.schedueler.PipeJob import PipeJob
from mrpipe.meta.Session import Session
from mrpipe.meta import LoggerModule
from mrpipe.modalityModules.PathDicts.BasePaths import PathBase
from mrpipe.Toolboxes.envs.Envs import Envs
from mrpipe.modalityModules.PathDicts.LibPaths import LibPaths
from mrpipe.modalityModules.PathDicts.Templates import Templates

logger = LoggerModule.Logger()


class ProcessingModule(ABC):
    # subclass should override this:
    requiredModalities = None
    optionalModalities = None
    moduleDependencies = None

    def __init__(self, name: str, sessionList: List[Session], basepaths: PathBase, libPaths: LibPaths, templates: Templates, inputArgs):
        # ProcessingModule ABC implements init function, the child modules should not implement it themselves. I think. For now.
        self.moduleName = name
        self.basepaths = basepaths
        self.inputArgs = inputArgs
        self.isSetup = False
        self.libpaths = libPaths
        self.templates = templates
        self.moduleDependenciesDict = {}

        # unsettable:
        self.envs = Envs(self.libpaths)
        self.jobDir = self.basepaths.pipeJobPath.join(name)
        self.pipeJobs: List[PipeJob] = []
        self.sessions = []

        for session in sessionList:
            #TODO maybe this will bite my ass at some point when i want to verify which modules ran for which sessions, because the session are not listed anymore, neither in the PipeJob, nor the Processing module. But this should be solvable by iterating over all sessions and indicating that the session does not have this modality.
            for modality in self.requiredModalities:
                if modality in session.modalities.available_modalities():
                    self.sessions.append(session)
                else:
                    logger.warning(f"Tried to add session {session.path} but to processing module {self.moduleName} but modality {modality} does not exist in this session. Not adding session.")

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

    @staticmethod
    def verifyInputFilesForSession(cls):
        #TODO verify for each session that for all pipejobs the required input files are either there or are beeing created from other pipejobs, i.e. are output files.
        pass

    def addPipeJobs(self, keepVerbosity: bool = False):
        for el in self.__dict__.values():
            if isinstance(el, PipeJob):
                self.addPipeJob(el, keepVerbosity)

    def addPipeJob(self, job: PipeJob, keepVerbosity: bool = False):
        if not keepVerbosity:
            job.setVerbosity(self.inputArgs.verbose)
        job.setJobDir(self.jobDir)
        self.pipeJobs.append(job)

    def safeSetup(self, ModuleList: List['ProcessingModule'] = None) -> bool:
        kept_sessions = []
        for session in self.sessions:
            if not session.pathsConfigured:
                logger.error(f'Tried to add {session} without session PathsCollection initiated. This is highly likely not your fault, but a scheduler issue, please consult your pipeline maintainer.')
            for modality in self.requiredModalities:
                if not session.subjectPaths.checkPathsConfigured(modality):
                    logger.warning(f"Session {session.path} has no configured paths for this processing module ({self.moduleName}). Its very likely that the modality is missing for this session. Removing session from processing module.")
                    self.sessions.remove(session)
                else:
                    kept_sessions.append(session)
                    logger.debug(f"Session {session.path} has configured paths for modality {modality}: {str(session.subjectPaths.__dict__.get(modality))}")
        if not kept_sessions:
            logger.critical(f"No subjects could be configured for this module. This is very likely a missmatch between the modality name set in ModalityNames.yml and the actual directory name. Please double check that the directories are spelled correctly. If you didn't change the file, you might also try to delete it and rerun the configuration. There is also the very unlikely chance that the subject paths were not configured before the Processing Module ({self.moduleName}). In this case the processing module code is wrong.")
            sys.exit(3)
        else:
            self.sessions = kept_sessions
        if ModuleList and self.moduleDependencies:
            for module in ModuleList:
                # add processing modules which to module depends on, such that jobs are accessiable for dependencies.
                if module.moduleName in self.moduleDependencies:
                    self.moduleDependenciesDict[module.moduleName] = module
            ActiveModules = [module.moduleName for module in ModuleList]
            for moduleName in self.moduleDependencies:
                if moduleName not in ActiveModules:
                    logger.error(f'Module dependency {moduleName} for module {self.moduleName} not found in active Modules. Removing {self.moduleName} from the processing list. Please activate {moduleName} to run {self.moduleName}.')
                    return False
        return self.setup()

    @abstractmethod
    def setup(self) -> bool:
        #do setup in child class
        #CAVEAT: External job dependencies must be decleared in the setup section, because only then all modules are configured and present.

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
