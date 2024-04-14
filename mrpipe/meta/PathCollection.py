from abc import ABC, abstractmethod

from mrpipe.Helper import Helper
from mrpipe.meta.PathClass import Path
import yaml
import json
from mrpipe.meta import LoggerModule
logger = LoggerModule.Logger()


class PathCollection(ABC):
    filePatterns = {}
    filePatternPath = None

    @abstractmethod
    def __init__(self, name):
        self.name = name
        pass

    def createDirs(self):
        for key, path in self.__dict__.items():
            if isinstance(path, Path) and path.isDirectory:
                path.createDir()
            if isinstance(path, PathCollection):
                path.createDirs()

    def to_yaml(self, filepath):
        output_dict = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Path):
                output_dict[key] = value.path
            else:
                output_dict[key] = value

        with open(filepath, 'w') as file:
            yaml.dump(output_dict, file)

    @staticmethod
    def getFilePatterns(name: str):
        if name not in PathCollection.filePatterns.keys():
            return []
        else:
            patterns = PathCollection.filePatterns[name]
            logger.debug(f"Found file patterns for {name}: {str(patterns)}")
            return patterns

    @staticmethod
    def setFilePatterns(name: str, filePatterns):
        if name not in PathCollection.filePatterns:
            PathCollection.filePatterns[name] = []
        for pattern in Helper.ensure_list(filePatterns, flatten=True):
            PathCollection.filePatterns[name].append(pattern)
        PathCollection.filePatternsToJSON()

    @classmethod
    def from_yaml(cls, filepath):
        with open(filepath, 'r') as file:
            data = yaml.safe_load(file)
        return cls(**data)

    @staticmethod
    def filePatternsToJSON():
        if PathCollection.filePatternPath is None:
            logger.warning(f"No file pattern Path found, not saving")
            return False
        logger.debug("Writing file patterns to json: {}".format(PathCollection.filePatternPath))
        for key, patterns in PathCollection.filePatterns.items(): #TODO Silly solution to fix the bug that patterns would be added to the JSON file multiple times for whatever reason
            PathCollection.filePatterns[key] = list(set(patterns))
        with open(PathCollection.filePatternPath, 'w') as file:
            json.dump(PathCollection.filePatterns, file)
        return True

    @staticmethod
    def filePatternsFromJson():
        if PathCollection.filePatternPath is None:
            logger.warning(f"No file pattern Path found, returning empty")
            return False
        if not PathCollection.filePatternPath.exists():
            logger.warning(f"Pattern file does not exist (maybe not yet), returning empty")
            return False
        logger.debug("Reading file patterns from json: {}".format(PathCollection.filePatternPath))
        if len(PathCollection.filePatterns) != 0:
            logger.info(f"Found {len(PathCollection.filePatterns)} file patterns already in class. This will overwrite any existing patterns")
        with open(PathCollection.filePatternPath, 'r') as file:
            PathCollection.filePatterns.update(json.load(file))
        for key, patterns in PathCollection.filePatterns.items(): #TODO Silly solution to fix the bug that patterns would be added to the JSON file multiple times for whatever reason
            PathCollection.filePatterns[key] = list(set(patterns))
        return True


    def __str__(self):
        paths = []
        for key, path in self.__dict__.items():
            if isinstance(path, Path):
                paths.append(f"{key}: {str(path)}")
            if isinstance(path, PathCollection):
                paths.append(str(path))
        return "\n".join(s for s in paths)

    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        from mrpipe.modalityModules.PathDicts.BasePaths import PathBase
        for el in [*args, kwargs.values()]:
            if isinstance(el, PathBase):
                PathCollection.filePatternPath = el.filePatterns
                instance.filePatternsFromJson()
        return instance
