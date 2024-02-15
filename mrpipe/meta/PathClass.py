import os
import warnings
from mrpipe.meta import loggerModule

logger = loggerModule.Logger()

class Path:

    def __init__(self, path: str, isDirectory = False, create=False, clobber=False):
        self.path = path
        self.isDirectory = isDirectory
        self.exists()
        self.clobber = clobber
        logger.info(f"Created Path class: {self}")
        if create:
            self.createDir(clobber)

    def exists(self):
        if self.isDirectory:
            return os.path.isdir(self.path)
        else:
            return os.path.isfile(self.path)

    def createDir(self):
        if self.exists() and not self.clobber:
            logger.warning(f"Directory already exists and clobber is false: {self}")
            return
        if self.isDirectory:
            os.makedirs(self.path, exist_ok=True)
            logger.debug(f"Created Directory: {self}")
        else:
            logger.warning(f"ou tried to create a file, this can only create directories: {self}")

    def __str__(self):
        return os.path.abspath(self.path)

    def __repr__(self):
        return os.path.abspath(self.path)

    def __fspath__(self):
        return os.path.abspath(self.path)

