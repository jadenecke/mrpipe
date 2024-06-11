from mrpipe.meta.ImageWithSideCar import ImageWithSideCar
from mrpipe.meta import LoggerModule
from mrpipe.meta.PathClass import Path
from mrpipe.Helper import Helper
from typing import List
import glob


logger = LoggerModule.Logger()

class MEGRE():
    def __init__(self, inputDirectory: Path = None, magnitudePaths: List[Path] = None, phasePaths: List[Path] = None,
                 magnitudeJsonPaths: List[Path] = None, phaseJsonPaths: List[Path] = None, echoNumber: int = None,
                 echoTimes: List[float] = None):
        self.echoNumber = None
        self.echoTimes = None

        if inputDirectory is not None:
            niftiFiles = glob.glob(inputDirectory.join("*.nii*"))
            jsonFiles = glob.glob(inputDirectory.join("*.json"))
            self.magnitudePaths, self.phasePaths = Helper.separate_files(niftiFiles, ["ph", "pha", "phase"], ensureEqual=True)
            self.magnitudeJsonPaths, self.phaseJsonPaths = Helper.separate_files(jsonFiles, ["ph", "pha", "phase"], ensureEqual=True)
        else:
            self.magnitudePaths = magnitudePaths
            self.phasePaths = phasePaths
            self.magnitudeJsonPaths = magnitudeJsonPaths
            self.phaseJsonPaths = phaseJsonPaths


        if magnitudeJsonPaths is not None and phaseJsonPaths is not None:
            logger.debug("Taking MEGRE information from nifti files and json sidecars")
            if not len(self.magnitudePaths) == len(self.phasePaths) == len(self.magnitudeJsonPaths) == len(self.phaseJsonPaths):
                logger.error(f"File number of magnitude and phase and json files do not match: {self.magnitudePaths}, {self.phasePaths}, {self.magnitudeJsonPaths}, {self.phaseJsonPaths}")
            self.magnitude: List[ImageWithSideCar] = [ImageWithSideCar(imagePath=fp, jsonPath=jp) for fp, jp in zip(self.magnitudePaths, self.magnitudeJsonPaths)]
            self.phase: List[ImageWithSideCar] = [ImageWithSideCar(imagePath=fp, jsonPath=jp) for fp, jp in zip(self.phasePaths, self.phaseJsonPaths)]
            self.echoNumber = len(self.magnitude)
            self.echoTimes = [mag.getAttribute("EchoTime") for mag in self.magnitude]
        else:
            logger.debug("Taking MEGRE information from nifti files and utilizing general echo number and time information")
            if echoNumber is None or echoTimes is None:
                logger.error(f"No Echo Number and Echo times for the given magnitude and phase images. This is to few information to work with. First magnitude file: {self.magnitudePaths[0]}")
            self.echoNumber = echoNumber
            self.echoTimes = echoTimes





