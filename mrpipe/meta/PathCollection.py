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
        output_dict = {}
        for key, value in self.__dict__.items():
            if isinstance(value, Path):
                output_dict[key] = value.path
            else:
                output_dict[key] = value

        with open(filepath, 'w') as file:
            yaml.dump(output_dict, file)

    @classmethod
    def from_yaml(cls, filepath):
        with open(filepath, 'r') as file:
            data = yaml.safe_load(file)
        return cls(**data)


    def __str__(self):
        paths = []
        for key, path in self.__dict__.items():
            if isinstance(path, Path):
                paths.append(f"{key}: {str(path)}")
            if isinstance(path, PathCollection):
                paths.append(str(path))
        return "\n".join(s for s in paths)
