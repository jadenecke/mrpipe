import os

class PathDefinition:

    def __init__(self, path: str, isDirectory = False, create = False):
        self.path = path
        self.isDirectory = isDirectory
        return(self)

    def exists(self):
        if self.isDirectory:
            return os.path.isdir(self.path)
        else:
            return os.path.isfile(self.path)

    def createDir(self):
        if self.isDirectory and os.path.isdir(self.path):
            os.makedirs(self.path, exist_ok=True)


