from __future__ import annotations
import os
from mrpipe.meta import LoggerModule
import gzip
import shutil
from mrpipe.Helper import Helper
import glob
import re
import copy
import pathlib
import json



logger = LoggerModule.Logger()

class Path:
    def __init__(self, path, isDirectory = False, create=False, clobber=False, shouldExist = False, static=False, cleanup=False):
        self.path = self._joinPath(path)
        self.isDirectory = isDirectory
        self.exists()
        self.clobber = clobber
        self.static = static  # static = True implies, that the filename can not be changed, i.e. when written to and read from yml. This would be the case if a program outputs unchangeable file names.
        self.cleanup = cleanup  # cleanup = True implies that the file/dir is removed at the cleanup state #TODO implement cleanup stage
        self.existCached: bool = None
        logger.debug(f"Created Path class: {self}")
        if create:
            self.createDir()
        if shouldExist:
            if not self.exists():
                logger.error(f"Path {self.path} does not exists, but shouldExist is True. This may lead to unexpected errors.")

    def get_filename(self) -> str:
        return os.path.basename(self.path)

    def get_filename_sans_ending(self) -> str:
        fn = os.path.basename(self.path)
        fn.rstrip(".gz") #remove zipped if thats present
        return fn.stem

    def get_filetype(self) -> str:
        return os.path.splitext(self.get_filename())[1]

    def get_directory(self) -> str:
        return os.path.dirname(self.path)

    def _joinPath(self, path):
        path = Helper.ensure_list(path)
        # logger.info(str(path))
        return os.path.join(*path)

    def createSymLink(self, target: Path):
        if self.isDirectory:
            logger.error(f"Symlink {target} is directory, only supports files.")
        try:
            os.symlink(self.path, target.path)
        except Exception as e:
            logger.logExceptionError(f"Symlink could not be created: {target}", e)
            return None
        return target

    def copy(self, path: str, clobber: bool = False, unzip: bool = False):
        newPath = copy.deepcopy(self)
        if unzip:
            newPathZipped = copy.deepcopy(self)
            newPathZipped.path = str(path)
            newPath.path = str(path).rstrip(".gz")
        else:
            newPath.path = str(path)
        if(newPath.exists() and not clobber):
            logger.error(f"File {newPath.path} already exists, and clobber is false. Not Overwriting existing file. Assuming that existing and new file are the same.")
            return newPath
        try:
            if not os.path.isdir(newPath.get_directory()):
                pathlib.Path(newPath.get_directory()).mkdir(parents=True, exist_ok=False)
            if unzip:
                shutil.copy(str(self.path), str(newPathZipped.path))
                newPathZipped.unzipFile()
                newPath.exists(acceptCache=False)
            else:
                shutil.copy(str(self.path), str(newPath.path))
        except Exception as e:
            logger.logExceptionError(f"File could not be copied: {self.path}", e)
            return None
        return newPath

    def exists(self, acceptZipped : bool = True, acceptUnzipped : bool = True, transform : bool = True, acceptCache : bool = False):
        if acceptCache and self.existCached is not None:
            return self.existCached
        if self.isDirectory:
            exists = os.path.isdir(self.path)
            self.existCache = exists
            return exists
        else:
            exists = os.path.isfile(self.path)
            if (not exists) and acceptZipped:
                if os.path.isfile(self.path + ".gz"):
                    logger.warning(f"File does not exist unzipped, but exist zipped: {self.path}.gz. Assuming you also accept the zipped version.")
                    self.path = self.path + ".gz"
                    if transform:
                        self.unzipFile(removeAfter=True)
                    self.existCache = True
                    return True
            if (not exists) and acceptUnzipped:
                if os.path.isfile(self.path.rstrip(".gz")):
                    logger.warning(f"File does not exist zipped, but exist unzipped: {self.path.rstrip('.gz')}. Assuming you also accept the zipped version.")
                    self.path = self.path.rstrip(".gz")
                    if transform:
                        self.zipFile(removeAfter=True)
                    self.existCached = True
                    return True
            self.existCached = exists
            return exists

    def createDir(self):
        if self.exists() and not self.clobber:
            logger.info(f"Directory already exists and clobber is false: {self}")
            return
        if self.isDirectory:
            pathlib.Path(self.path).mkdir(exist_ok=True, parents=True)
            logger.info(f"Created Directory: {self}")
        else:
            logger.warning(f"You tried to create a file, this can only create directories: {self}")

    def checkIfZipped(self):
        if self.path.endswith(".gz") and self.exists():
            return True
        else:
            return False

    @classmethod
    def Identify(cls, fileDescription, pattern, searchDir: Path, previousPatterns, negativePattern):
        #TODO For now, it is not possible to ignore the input given for now, so this may lead to issues, when an already defined pattern matches a file, but the user wants to specify a different file (However, this is unlikely)

        #TODO Add logic to identify duplicated file from multiple different files.
        for pp in previousPatterns:
            r = glob.glob(str(searchDir.join(pp)))
            if len(r) == 1:
                logger.debug(f"Found file with pattern {pp} in {searchDir}: \n{r[0]}")
                return Path(r[0], shouldExist=True, static=True), None, None
            elif len(r) == 2: #case when bot *.nii and *.nii.gz file exist
                l0 = len(r[0])
                l1 = len(r[1])
                if l0 < l1:
                    short = r[0]
                    long = r[1]
                else:
                    short = r[1]
                    long = r[0]
                if long == (short + ".gz"):
                    logger.debug(f"Found file with pattern {pp} in {searchDir}: \n{long}")
                    return Path(long, shouldExist=True, static=True), None, None

        matches = {}
        for file in os.listdir(str(searchDir)):
            if any(re.match(neg_pat, file) for neg_pat in negativePattern):
                continue  # Skip files that match any negative pattern
            if m := re.match(pattern, file):
                matches[m.group(1)] = file

        if len(matches) == 0:
            return None, None, None
        elif len(matches) == 1:
            key = list(matches.keys())[0]
            logger.info(f'Found pattern Match for {fileDescription} in {searchDir}: {key}')
            if Path._confirmChoosen(fileDescription, matches[key], key):
                return Path(os.path.join(searchDir, matches[key]), shouldExist=True, static=True), key, None
            else:
                return None, None, key
        elif len(matches) > 1:
            key = Path._identifyChoose(fileDescription=fileDescription, matches=matches)
            if key is not None:
                logger.info(f'Found pattern Match for {fileDescription} in {searchDir}: {key}')
                return Path(os.path.join(searchDir, matches[key]), shouldExist=True, static=True), key
            else:
                return None, None, None
        logger.error(f'File not found for {fileDescription} with patterns {pattern} and {previousPatterns}. This will probably break the modality for this session: {searchDir}')
        return None, None, None

    @staticmethod
    def _identifyChoose(fileDescription, matches):
        while True:
            try:
                print(f"Please select the correct match for '{fileDescription}' from the following list. This will be used as Template for other Subjects and Sessions if possible:")
                print("0: No Valid match")
                for i, key in enumerate(matches, 1):
                    print(f"{i}: {matches[key]}")
                # Wait for the user to enter a number to specify the correct match
                correct_match_index = int(input()) - 1
                if 0 <= correct_match_index < len(matches):
                    return list(matches)[correct_match_index]
                elif correct_match_index == -1:
                    return None
                else:
                    print("Invalid Input, please try again:")
            except Exception as e:
                print("Invalid Input, please try again:")

    @staticmethod
    def _confirmChoosen(fileDescription, match, key):
        while True:
            print(f"Please verify that for '{fileDescription}' the following is correct:\n File: {match}\n Pattern: {key}\n For: {fileDescription}")
            print(f"(y)es or (n)o?:")
            response = input().lower()
            if response == "y" or response == "yes":
                return True
            if response == "n" or response == "no":
                return False
            else:
                print("Invalid Input, please try again:")


    def zipFile(self, removeAfter : bool = True):
        if self.isDirectory:
            logger.warning("You tried to zip a directory. This is not implemented yet.")
            return
        if not self.checkIfZipped():
            try:
                if os.path.exists(self.path + ".gz"):
                    logger.warning(
                        f"Unzipped file already seem to exist, overwriting: {self.path + '.gz'}")
                    os.remove(self.path + ".gz")
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
        return Path(os.path.join(self.path, s), isDirectory=isDirectory, clobber=clobber, shouldExist=shouldExist)

    def unzipFile(self, removeAfter : bool = True):
        if self.isDirectory:
            logger.warning("You tried to unzip a directory. This is not implemented yet.")
            return
        if self.checkIfZipped():
            try:
                if os.path.exists(self.path.rstrip(".gz")):
                    logger.warning(
                        f"Zipped file already seem to exist, overwriting: {self.path.rstrip('.gz')}")
                    os.remove(self.path.rstrip(".gz"))
                logger.info(f"Unzipping {self.path}")
                with gzip.open(self.path, 'rb') as f_in:
                    with open(self.path.rstrip(".gz"), 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                oldpath = self.path
                self.path = self.path.rstrip(".gz")
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

    def setStatic(self):
        #TODO: stop these paths from beeing modifyable by the user, as the name is specified by the program and cannot be modified.
        self.static = True
        return self

    def setCleanup(self):
        #TODO files and folders to be removed at cleanup stage.
        self.cleanup = True
        return self

    def setOptional(self):
        #TODO files which exists optionally: Warn if they are used for regular tasks, as the may only exists for some users.
        self.optional = True
        return self

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

    # Making the class subscriptable
    def __getitem__(self, item):
        return self.path[item]

    def remove(self):
        if self.isDirectory:
            logger.error(f'Trying to remove directory {self.path}, this is not supported, only files can be removed.')
            return False
        elif not self.exists():
            logger.info(f'File to be deleted does not exist: {self.path}')
            return True
        else:
            try:
                os.remove(self.path)
                return True
            except Exception as e:
                logger.error(f'Error while trying to remove file {self.path}: \n{e}')
                return False


class StatsFilePath(Path):
    def __init__(self, path, attributeName: str, clobber: bool = False):
        super().__init__(path, clobber=clobber, create=True)
        if self.get_filetype() is not ".json":
            logger.ERROR(f"Error: This is not a JSON file: {self.path}. Stat files must be JSON. Changing file type to JSON.")
            self.path = self.get_directory().join(self.get_filename_sans_ending() + ".json")
        self.attributeName = attributeName

    def exists(self):
        with open(self.path, 'r') as file:
            data = json.load(file)
        if self.attributeName in data: value = data[self.attributeName]
        if isinstance(value, (str, int, float, bool)):
            return True
        else:
            return False

    def writeValue(self, value) -> bool:
        if not self.clobber and self.exists():
            logger.error(f'Attribute {self.attributeName} already exists in  {self.path} and clobber is False, so it cannot be overwritten.')
            return False
        try:
            with open(self.path, 'r') as file:
                data = json.load(file)
            data[self.attributeName] = value
            with open(self.path, 'w') as file:
                json.dump(data, file, indent=4)
            logger.INFO(f'Successfully added "{self.attributeName}: {value}" to {self.path}')
        except FileNotFoundError as e:
            logger.logExceptionError(f'File {self.path} not found.', e)
            return False
        except json.JSONDecodeError as e:
            logger.logExceptionError(f'Error decoding JSON in {self.path}.', e)
            return False
        except Exception as e:
            logger.logExceptionError(f'An error occurred: ', e)
            return False
        return True




