from mrpipe.meta.PathCollection import PathCollection
from typing import Optional
from mrpipe.meta import loggerModule
from mrpipe.modalityModules.PathDicts.T1wPaths import PathDictT1w
from mrpipe.modalityModules.PathDicts.BasePaths import PathBase
from mrpipe.modalityModules.Modalities import Modalities

logger = loggerModule.Logger()

class SubjectPaths(PathCollection):
    def __init__(self):
        super().__init__("Paths")
        self.T1w: Optional[PathDictT1w] = None


    def checkPathsConfigured(self, modalityName: str) -> bool:
        if modalityName not in Modalities().modalityNames():
            logger.error(
                f"The supplied modality does not exist. Supplied modality: {modalityName}, available modalities: {Modalities().modalityNames()}")
            return False
        if (modalityName in self.__dict__.keys()) and self.__dict__[modalityName]:
            return True
        else:
            return False


    def setT1w(self, sub, ses, basepaths: PathBase, **kwargs):
        self.T1w = PathDictT1w(sub=sub, ses=ses, basepaths=basepaths, **kwargs)

