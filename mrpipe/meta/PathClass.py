import os
from mrpipe.meta import LoggerModule
import gzip
import shutil
from mrpipe.Helper import Helper

logger = LoggerModule.Logger()

class Path:
    def __init__(self, path, isDirectory = False, create=False, clobber=False, shouldExist = False):
        self.path = self._joinPath(path)
        self.isDirectory = isDirectory
        self.exists()
        self.clobber = clobber
        logger.debug(f"Created Path class: {self}")
        if create:
            self.createDir()
        if shouldExist:
            if not self.exists():
                logger.error(f"Path {self.path} does not exists, but shouldExist is True. This may lead to unexpected errors.")

    def _joinPath(self, path):
        path = Helper.ensure_list(path)
        # logger.info(str(path))
        return os.path.join(*path)

    def exists(self, acceptZipped : bool = True, acceptUnzipped : bool = True, transform : bool = True):
        if self.isDirectory:
            return os.path.isdir(self.path)
        else:
            exists = os.path.isfile(self.path)
            if (not exists) and acceptZipped:
                if os.path.isfile(self.path + ".gz"):
                    logger.warning(f"File does not exist unzipped, but exist zipped: {self.path}.gz. Assuming you also accept the zipped version.")
                    self.path = self.path + ".gz"
                    if transform:
                        self.unzipFile(removeAfter=True)
                    return True
            if (not exists) and acceptUnzipped:
                if os.path.isfile(self.path.rstrip(".gz")):
                    logger.warning(f"File does not exist zipped, but exist unzipped: {self.path}.gz. Assuming you also accept the zipped version.")
                    self.path = self.path.rstrip(".gz")
                    if transform:
                        self.zipFile(removeAfter=True)
                    return True
            return exists

    def createDir(self):
        if self.exists() and not self.clobber:
            logger.warning(f"Directory already exists and clobber is false: {self}")
            return
        if self.isDirectory:
            os.makedirs(self.path, exist_ok=True)
            logger.info(f"Created Directory: {self}")
        else:
            logger.warning(f"You tried to create a file, this can only create directories: {self}")

    def checkIfZipped(self):
        if self.path.endswith(".gz") and self.exists():
            return True
        else:
            return False


    def zipFile(self, removeAfter : bool = True):
        if self.isDirectory:
            logger.warning("You tried to zip a directory. This is not implemented yet.")
            return
        if not self.checkIfZipped():
            try:
                logger.info(f'Zipping {self.path}...')
                with open(self.path, 'rb') as f_in:
                    with gzip.open(self.path + ".gz", 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                oldpath = self.path
                self.path = self.path + ".gz"
                if self.exists() and removeAfter:
                    os.remove(oldpath)
            except Exception as e:
                logger.logExceptionError(f"Gzip of file failed: {self.path}", e)
        else:
            if self.exists():
                logger.warning(f"You tried to zip a file which either is already zipped: {self.path}")
            else:
                logger.warning(f"You tried to zip a file which does not (yet) exist: {self.path}")

    def join(self, s: str, isDirectory: bool = False, clobber=None, shouldExist: bool = False):
        if not clobber:
            clobber = self.clobber
        if shouldExist:
            if not self.exists():
                logger.error(f"Path {self.path} does not exists, but shouldExist is True. This may lead to unexpected errors.")
        return Path(os.path.join(self.path, s), isDirectory=isDirectory, clobber=clobber)

    def unzipFile(self, removeAfter : bool = True):
        if self.isDirectory:
            logger.warning("You tried to unzip a directory. This is not implemented yet.")
            return
        if self.checkIfZipped():
            try:
                logger.info(f"Unzipping {self.path}")
                with gzip.open(self.path, 'rb') as f_in:
                    with open(self.path.rstrip(".gz"), 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                oldpath = self.path
                self.path = self.path + ".gz"
                if self.exists() and removeAfter:
                    os.remove(oldpath)
            except Exception as e:
                logger.logExceptionError(f"Gzip of file failed: {self.path}", e)
        else:
            logger.warning(f"You tried to unzip a file which does not appeard to be zipped, at least it does not end with .gz: {self.path}")

    def parent(self):
        if self.isDirectory:
            return self.join(os.pardir, isDirectory=True)
        else:
            return Path(os.path.dirname(self.path), isDirectory=True)

    def __str__(self):
        return os.path.abspath(self.path)

    def __repr__(self):
        return os.path.abspath(self.path)

    def __fspath__(self):
        return os.path.abspath(self.path)

    #TODO: Think about getstate and setstate to clean up yaml structure.
    # def __getstate__(self):
    #     return {'path': self.path}
    # def __setstate__(self, state):
    #     self.path = state['path']
    #     self.isDirectory = False
    #     self.clobber = False

    def __add__(self, other):
        if isinstance(other, Path):
            return Path(os.path.join(self.path, other.path), isDirectory=other.isDirectory, clobber=other.clobber)
        if isinstance(other, str):
            return Path(self.path + other)
        else:
            raise TypeError("Unsupported operands type for +: 'Path' and '{}'".format(type(other).__name__))
