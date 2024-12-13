import sys

from mrpipe.meta.ImageWithSideCar import ImageWithSideCar
from mrpipe.meta import LoggerModule
from mrpipe.meta.PathClass import Path
from mrpipe.Helper import Helper
from typing import List
import glob
import os

logger = LoggerModule.Logger()

class MEGRE():
    def __init__(self, inputDirectory: Path = None, magnitudePaths: List[Path] = None, phasePaths: List[Path] = None,
                 magnitudeJsonPaths: List[Path] = None, phaseJsonPaths: List[Path] = None, echoNumber: int = None,
                 echoTimes: List[float] = None):
        self.echoNumber = None
        self.echoTimes = None

        if inputDirectory is not None:
            niftiFiles = glob.glob(str(inputDirectory.join("*.nii*")))
            jsonFiles = glob.glob(str(inputDirectory.join("*.json")))
            if len(niftiFiles) <= 1:
                logger.critical("No nifti files found. Will not proceed. Directory of files: " + str(inputDirectory))
                #TODO maybe solve this more gracefully: if file is not found config exits, but realy the processing module should get removed with an error from the session.
                sys.exit(1)
            self.magnitudePaths, self.phasePaths = Helper.separate_files(niftiFiles, ["ph", "pha", "phase"], ensureEqual=True)
            self.magnitudeJsonPaths, self.phaseJsonPaths = Helper.separate_files(jsonFiles, ["ph", "pha", "phase"], ensureEqual=True)
            #bring image and json paths in the same order:
            self.magnitudePaths, self.magnitudeJsonPaths = self._match_lists(self.magnitudePaths, self.magnitudeJsonPaths)
            self.phasePaths, self.phaseJsonPaths = self._match_lists(self.phasePaths, self.phaseJsonPaths)
        else:
            self.magnitudePaths = magnitudePaths
            self.phasePaths = phasePaths
            self.magnitudeJsonPaths = magnitudeJsonPaths
            self.phaseJsonPaths = phaseJsonPaths

        if self.magnitudeJsonPaths is not None and self.phaseJsonPaths is not None:
            logger.debug("Taking MEGRE information from nifti files and json sidecars")
            if not len(self.magnitudePaths) == len(self.phasePaths) == len(self.magnitudeJsonPaths) == len(self.phaseJsonPaths):
                logger.error(f"File number of magnitude and phase and json files do not match: {self.magnitudePaths}, {self.phasePaths}, {self.magnitudeJsonPaths}, {self.phaseJsonPaths}")
                self.magnitudePaths = self.magnitudeJsonPaths = self.phasePaths = self.phaseJsonPaths = None
            self.magnitude: List[ImageWithSideCar] = [ImageWithSideCar(imagePath=fp, jsonPath=jp) for fp, jp in zip(self.magnitudePaths, self.magnitudeJsonPaths)]
            self.phase: List[ImageWithSideCar] = [ImageWithSideCar(imagePath=fp, jsonPath=jp) for fp, jp in zip(self.phasePaths, self.phaseJsonPaths)]
            self.echoNumber = len(self.magnitude)
            self.echoTimes = [mag.getAttribute("EchoTime") for mag in self.magnitude]
            # sort them by echo times
            self.sort_by_echoTimes() #only required if echo times are picked up by json files and from directory
        else:
            if inputDirectory is not None:
                # TODO: This setup will lead to unwanted side effects if the image paths are determined automatically from an input directory, but json Paths are none (because none present), then the images will be unordered and not match the echo timings
                logger.critical(f"echo times could not be determined from the json files in this input directory: {inputDirectory}. This will highly likely cause errors because the image files were automatically determined and can not be brought in the correct order. This session will be removed.")
                self.magnitudePaths = self.magnitudeJsonPaths = self.phasePaths = self.phaseJsonPaths = None
            logger.debug("Taking MEGRE information from nifti files and utilizing general echo number and time information")
            if echoNumber is None or echoTimes is None:
                logger.error(f"No Echo Number and Echo times for the given magnitude and phase images. This is to few information to work with. First magnitude file: {self.magnitudePaths[0]}")
                self.magnitudePaths = self.magnitudeJsonPaths = self.phasePaths = self.phaseJsonPaths = None
            self.echoNumber = echoNumber
            self.echoTimes = echoTimes



        logger.debug(f"Identified: {self}")

    def validate(self):
        if self.echoNumber is None or self.echoTimes is None:
            return False
        if self.magnitudePaths is None or self.phasePaths is None:
            return False
        if len(self.echoTimes) < 2:
            return False
        if not len(self.magnitudePaths) == len(self.phasePaths) == len(self.echoTimes):
            return False
        return True

    def sort_by_echoTimes(self):
        # Combine the lists into a list of tuples
        combined = list(zip(self.magnitude, self.phase, self.echoTimes))
        # Sort the combined list based on the echoTimes values
        combined.sort(key=lambda x: x[2])
        logger.debug(f"Sorting by Echo. Result: {combined}")
        # Unzip the sorted combined list back into individual lists
        self.magnitude, self.phase, self.echoTimes = zip(*combined)


    @staticmethod
    def _match_lists(list1, list2):
        # Create a dictionary with keys as filenames without extensions and values as file paths for list1
        dict1 = {os.path.basename(path).split(".")[0]: path for path in list1}
        # Create a dictionary with keys as filenames without extensions and values as file paths for list2
        dict2 = {os.path.basename(path).split(".")[0]: path for path in list2}

        # Find the common keys in both dictionaries
        common_keys = set(dict1.keys()).intersection(set(dict2.keys()))

        if not (all(key in common_keys for key in dict1.keys()) and all(key in common_keys for key in dict2.keys())):
            return None, None
        # Create sorted lists based on the common keys
        list1_sorted = [dict1[key] for key in common_keys]
        list2_sorted = [dict2[key] for key in common_keys]

        return list1_sorted, list2_sorted

    def __str__(self):
        return f"MEGRE seqeuence: Echo Number: {self.echoNumber} ({self.echoTimes})\nMagnitude:\n{[str(m) for m in self.magnitude]}\nPhase:\n{[str(p) for p in self.phase]}"
