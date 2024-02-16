from typing import List
from mrpipe.meta import loggerModule
from mrpipe.meta import PathClass
from mrpipe import helper
from abc import ABC, abstractmethod
from enum import Enum

logger = loggerModule.Logger()

class TaskStatus(Enum):
    #normal states
    notRun = 1
    submitted = 2
    finished = 3
    isPreComputed = 4
    #error States
    inFilesNotVerifable = 90
    outFilesNotVerfiable = 91


class Task:
    def __init__(self, name: str, clobber=False):
        #settable
        self.clobber = clobber
        self.name = name

        #unsettables
        self.inFiles: List[PathClass] = []
        self.outFiles: List[PathClass] = []
        self.state = TaskStatus.notRun

    @abstractmethod
    def getCommand(self):
        #To be implemented by child classes
        pass

    def setStatePrecomputed(self):
        if self.state == TaskStatus.notRun:
            self.state = TaskStatus.isPreComputed
        else:
            logger.warning(f"Not setting precomputed, because Task state is not notRun. Task state remains: {self.state}")


    def shouldRun(self):
        if self.state == TaskStatus.notRun:
            return True
        else:
            return False

    def verifyInFiles(self) -> bool:
        for file in self.inFiles:
            if not file.exists():
                logger.error(f"Could not verify InFiles, required file does not exists: {file}")
                self.state = TaskStatus.inFilesNotVerifable
                return False
        return True

    def checkIfDone(self) -> bool:
        for file in self.outFiles:
            if not file.exists():
                return False
        else:
            self.state = TaskStatus.isPreComputed
            return True

    def verifyOutFiles(self):
        for file in self.outFiles:
            if file.exists() and (not self.clobber):
                return False
                self.state = TaskStatus.outFilesNotVerfiable
                logger.error(f"Could not verify OutFiles, file already exists and clobber is false: {file}")
        return True

    def addInFiles(self, file):
        file = helper.ensure_list(file)
        for el in file:
            if not isinstance(el, PathClass):
                logger.error(f"Could not add file to InFiles, file is not instance of PathClass or [PathClass]: {type(el)}")
            else:
                self.inFiles.append(el)

    def addOutFiles(self, file):
        file = helper.ensure_list(file)
        for el in file:
            if not isinstance(el, PathClass):
                logger.error(
                    f"Could not add file to OutFiles, file is not instance of PathClass or [PathClass]: {type(el)}")
            else:
                self.inFiles.append(el)
