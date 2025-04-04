from typing import List
from mrpipe.meta import LoggerModule
from mrpipe.meta.PathClass import Path
from mrpipe.Helper import Helper
from abc import ABC, abstractmethod
from enum import Enum

logger = LoggerModule.Logger()

class TaskStatus(Enum):
    #normal states
    notRun = 1
    submitted = 2
    finished = 3
    isPreComputed = 4
    recompute = 5
    #error States
    inFilesNotVerifable = 90
    outFilesNotVerfiable = 91


class Task(ABC):
    def __init__(self, name: str, clobber=False):
        #settable
        self.clobber = clobber
        self.name = name

        #unsettables
        self.inFiles: List[Path] = []
        self.outFiles: List[Path] = []
        self.state = TaskStatus.notRun
        self.cleanupCommand = None

    @abstractmethod
    def getCommand(self):
        #To be implemented by child classes
        pass

    def addCleanup(self, command: str):
        self.cleanupCommand = command

    def getState(self):
        return self.state

    def setStatePrecomputed(self):
        if self.state in [TaskStatus.notRun, TaskStatus.isPreComputed]:
            self.state = TaskStatus.isPreComputed
        else:
            logger.warning(f"Not setting precomputed, because Task state is not notRun. Task state remains: {self.state}")

    def setStateRecompute(self):
        if self.state not in [TaskStatus.inFilesNotVerifable, TaskStatus.outFilesNotVerfiable, TaskStatus.submitted]:
            self.state = TaskStatus.recompute


    def shouldRun(self):
        if self.state == TaskStatus.notRun or self.state == TaskStatus.recompute:
            return True
        else:
            return False

    def verifyInFiles(self) -> bool:
        for file in self.inFiles:
            if file is None:
                logger.error(f"Infile contains None element, indicating that a Path identification failed. Taskname: {self.name}")
                self.state = TaskStatus.inFilesNotVerifable
                return False
            if not file.exists():
                logger.error(f"Could not verify InFiles, required file does not exists: {file}")
                self.state = TaskStatus.inFilesNotVerifable
                return False
        return True

    def checkIfDone(self) -> bool:
        if self.getState() == TaskStatus.recompute:
            logger.info(f"Task was requested to be recomputed. Setting to clobber and recomputing it.")
            return False
        if self.getState() == TaskStatus.isPreComputed:
            return True
        for file in self.outFiles:
            if not file.exists():
                logger.info(f"Outfile contains file which does not exist yet, need to compute task. File: {file}")
                return False
        #self.state = TaskStatus.isPreComputed #was duplicated
        self.setStatePrecomputed()
        return True

    def verifyOutFiles(self):
        for file in self.outFiles:
            if file.exists() and (not self.clobber):
                self.state = TaskStatus.outFilesNotVerfiable
                logger.error(f"Could not verify OutFiles, file already exists and clobber is false: {file}")
                return False
        return True

    def addInFiles(self, file):
        file = Helper.ensure_list(file, flatten=True)
        for el in file:
            if not isinstance(el, Path):
                logger.error(f"Could not add file to InFiles for task '{self.name}', file is not instance of PathClass or [PathClass]: {type(el)}; {str(el)}")
            else:
                if self.checkUnique(file):
                    self.inFiles.append(el)

    def createOutDirs(self):
        for outfile in self.outFiles:
            outfile.parent().create()

    def addOutFiles(self, file):
        self.state = TaskStatus.notRun
        file = Helper.ensure_list(file, flatten=True)
        for el in file:
            if not isinstance(el, Path):
                logger.error(
                    f"Could not add file to OutFiles, file is not instance of PathClass or [PathClass]: {type(el)}; {str(el)}; Task Name: {self.name}")
                logger.error(str(el))
            else:
                if self.checkUnique(file):
                    self.outFiles.append(el)
        self.checkIfDone()

    def preRunCheck(self):
        if self.clobber:
            for file in self.outFiles:
                file.remove()

    def checkUnique(self, file):
        if file in self.inFiles or file in self.outFiles:
            logger.warning(f'File {file} already exists in InFiles or OutFiles')
            return False
        else:
            return True
