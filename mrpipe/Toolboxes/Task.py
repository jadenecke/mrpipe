from typing import List
from mrpipe.meta import loggerModule
from mrpipe.meta import PathClass
from mrpipe import helper
from abc import ABC, abstractmethod

logger = loggerModule.Logger()

class Task:
    def __init__(self, name: str, clobber=False):
        #settable
        self.clobber = clobber
        self.name = name

        #unsettables
        self.inFiles: List[PathClass] = []
        self.outFiles: List[PathClass] = []

    @abstractmethod
    def getCommand(self):
        #To be implemented by child classes
        pass

    def verifyInFiles(self) -> bool:
        for file in self.inFiles:
            if not file.exists():
                logger.error(f"Could not verify InFiles, required file does not exists: {file}")
                return False
        return True

    def verifyOutFiles(self):
        for file in self.outFiles:
            if file.exists() and (not self.clobber):
                return False
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
