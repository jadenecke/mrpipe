from abc import ABC, abstractmethod
from mrpipe.meta.PathClass import Path
import yaml


class PathCollection(ABC):
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
        with open(filepath, 'w') as file:
            yaml.dump(self.__dict__, file)

    @classmethod
    def from_yaml(cls, filepath):
        with open(filepath, 'r') as file:
            data = yaml.safe_load(file)
        return cls(**data)


    def __str__(self):
        paths = []
        for key, path in self.__dict__.items():
            if isinstance(path, Path):
                paths.append(str(path))
            if isinstance(path, PathCollection):
                paths.append(str(path))
        return str(paths)
