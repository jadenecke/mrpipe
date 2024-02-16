from abc import ABC, abstractmethod
from mrpipe.meta.PathClass import Path
import yaml


class PathCollection(ABC):
    @abstractmethod
    def __init__(self):
        pass

    def createDirs(self):
        for key, path in self.__dict__.items():
            if isinstance(path, Path) and path.isDirectory:
                path.createDir()



    def to_yaml(self, filepath):
        with open(filepath, 'w') as file:
            yaml.dump(self.__dict__, file)

    @classmethod
    def from_yaml(cls, filepath):
        with open(filepath, 'r') as file:
            data = yaml.safe_load(file)
        return cls(**data)