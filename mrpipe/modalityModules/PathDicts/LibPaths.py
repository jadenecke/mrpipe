from mrpipe.meta.PathCollection import PathCollection
from mrpipe.meta.PathClass import Path

class LibPaths(PathCollection):
    def __init__(self, libcudnn="/path/to/libcudnn", test="/test"):
        self.libcudnn = Path(libcudnn, isDirectory=True)
        self.test = Path(test, isDirectory=True)
