from mrpipe.meta.PathCollection import PathCollection
from typing import Optional
from mrpipe.meta import LoggerModule
from mrpipe.modalityModules.PathDicts.MEGREPaths import PathDictMEGRE
from mrpipe.modalityModules.PathDicts.T1wPaths import PathDictT1w
from mrpipe.modalityModules.PathDicts.FLAIRPaths import PathDictFLAIR
from mrpipe.modalityModules.PathDicts.PETAV45Paths import PathDictPETAV45
from mrpipe.modalityModules.PathDicts.BasePaths import PathBase
from mrpipe.modalityModules.Modalities import Modalities
from mrpipe.modalityModules.PathDicts.PETNAV4694Paths import PathDictPETNAV4694
from mrpipe.modalityModules.PathDicts.PETFBBPaths import PathDictPETFBB
from mrpipe.modalityModules.PathDicts.PETAV1451Paths import PathDictPETAV1451
from mrpipe.modalityModules.PathDicts.PETPI2620Paths import PathDictPETPI2620
from mrpipe.modalityModules.PathDicts.PETMK6240Paths import PathDictPETMK6240

logger = LoggerModule.Logger()

class SubjectPaths(PathCollection):
    def __init__(self):
        super().__init__("Paths")
        self.path_yaml = None
        self.T1w: Optional[PathDictT1w] = None
        self.flair: Optional[PathDictFLAIR] = None
        self.megre: Optional[PathDictMEGRE] = None
        self.pet_av45: Optional[PathDictPETAV45] = None


    def checkPathsConfigured(self, modalityName: str) -> bool:
        if modalityName not in Modalities().modalityNames():
            logger.error(
                f"The supplied modality does not exist. Supplied modality: {modalityName}, available modalities: {Modalities().modalityNames()}")
            return False
        if (modalityName in self.__dict__.keys()) and (self.__dict__[modalityName]) and (self.__dict__[modalityName] is not None):
            return True
        else:
            return False

    # IMPORTANT: must have the same names as Modalities corresponding Elements
    def setT1w(self, sub, ses, basepaths: PathBase, **kwargs):
        self.T1w = PathDictT1w(sub=sub, ses=ses, basepaths=basepaths, **kwargs).verify()

    def setFlair(self, sub, ses, basepaths: PathBase, **kwargs):
        self.flair = PathDictFLAIR(sub=sub, ses=ses, basepaths=basepaths, **kwargs).verify()

    def setMEGRE(self, sub, ses, basepaths: PathBase, **kwargs):
        self.megre = PathDictMEGRE(sub=sub, ses=ses, basepaths=basepaths, **kwargs).verify()

    def setPETAV45(self, sub, ses, basepaths: PathBase, **kwargs):
        self.pet_av45 = PathDictPETAV45(sub=sub, ses=ses, basepaths=basepaths, **kwargs).verify()

    def setPETNAV4694(self, sub, ses, basepaths: PathBase, **kwargs):
        self.pet_nav4694 = PathDictPETNAV4694(sub=sub, ses=ses, basepaths=basepaths, **kwargs).verify()

    def setPETFBB(self, sub, ses, basepaths: PathBase, **kwargs):
        self.pet_fbb = PathDictPETFBB(sub=sub, ses=ses, basepaths=basepaths, **kwargs).verify()

    def setPETAV1451(self, sub, ses, basepaths: PathBase, **kwargs):
        self.pet_av1451 = PathDictPETAV1451(sub=sub, ses=ses, basepaths=basepaths, **kwargs).verify()

    def setPETPI2620(self, sub, ses, basepaths: PathBase, **kwargs):
        self.pet_pi2620 = PathDictPETPI2620(sub=sub, ses=ses, basepaths=basepaths, **kwargs).verify()

    def setPETMK6240(self, sub, ses, basepaths: PathBase, **kwargs):
        self.pet_mk6240 = PathDictPETMK6240(sub=sub, ses=ses, basepaths=basepaths, **kwargs).verify()

