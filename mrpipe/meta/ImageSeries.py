import sys

from mrpipe.meta.ImageWithSideCar import ImageWithSideCar
from mrpipe.meta import LoggerModule
from mrpipe.meta.PathClass import Path
from mrpipe.Helper import Helper
from typing import List
from numpy import cross
import glob
import os

logger = LoggerModule.Logger()

class MEGRE():
    def __init__(self, inputDirectory: Path = None, magnitudePaths: List[Path] = None, phasePaths: List[Path] = None,
                 magnitudeJsonPaths: List[Path] = None, phaseJsonPaths: List[Path] = None, echoNumber: int = None,
                 echoTimes: List[float] = None):
        self.echoNumber = None
        self.echoTimes = None
        self.magnitude = []
        self.phase = []

        if inputDirectory is not None:
            niftiFiles = glob.glob(str(inputDirectory.join("*.nii*")))
            jsonFiles = glob.glob(str(inputDirectory.join("*.json")))
            if len(niftiFiles) <= 1:
                logger.critical("No nifti files found. Will not proceed. Directory of files: " + str(inputDirectory))
                #TODO maybe solve this more gracefully: if file is not found config exits, but realy the processing module should get removed with an error from the session.
                sys.exit(1)
            self._magnitudePaths, self._phasePaths = Helper.separate_files(niftiFiles, ["ph", "pha", "phase"], ensureEqual=True)
            self._magnitudeJsonPaths, self._phaseJsonPaths = Helper.separate_files(jsonFiles, ["ph", "pha", "phase"], ensureEqual=True)
            #bring image and json paths in the same order:
            self._magnitudePaths, self._magnitudeJsonPaths = self._match_lists(self._magnitudePaths, self._magnitudeJsonPaths)
            self._phasePaths, self._phaseJsonPaths = self._match_lists(self._phasePaths, self._phaseJsonPaths)
        else:
            self._magnitudePaths = magnitudePaths
            self._phasePaths = phasePaths
            self._magnitudeJsonPaths = magnitudeJsonPaths
            self._phaseJsonPaths = phaseJsonPaths

        if self._magnitudeJsonPaths is not None and self._phaseJsonPaths is not None:
            logger.debug("Taking MEGRE information from nifti files and json sidecars")
            if not len(self._magnitudePaths) == len(self._phasePaths) == len(self._magnitudeJsonPaths) == len(self._phaseJsonPaths):
                logger.error(f"File number of magnitude and phase and json files do not match: {self._magnitudePaths}, {self._phasePaths}, {self._magnitudeJsonPaths}, {self._phaseJsonPaths}")
                self._magnitudePaths = self._magnitudeJsonPaths = self._phasePaths = self._phaseJsonPaths = None
            self.magnitude: List[ImageWithSideCar] = [ImageWithSideCar(imagePath=fp, jsonPath=jp) for fp, jp in zip(self._magnitudePaths, self._magnitudeJsonPaths)]
            self.phase: List[ImageWithSideCar] = [ImageWithSideCar(imagePath=fp, jsonPath=jp) for fp, jp in zip(self._phasePaths, self._phaseJsonPaths)]
            self.echoNumber = len(self.magnitude)
            self.echoTimes = [mag.getAttribute("EchoTime") for mag in self.magnitude]
            # sort them by echo times
            self.sort_by_echoTimes() #only required if echo times are picked up by json files and from directory
        else:
            if inputDirectory is not None:
                # TODO: This setup will lead to unwanted side effects if the image paths are determined automatically from an input directory, but json Paths are none (because none present), then the images will be unordered and not match the echo timings
                logger.error(f"Echo times could not be determined from the json files in this input directory: {inputDirectory}. This will highly likely cause errors because the image files were automatically determined and can not be brought in the correct order. This session will be removed.")
                self._magnitudePaths = self._magnitudeJsonPaths = self._phasePaths = self._phaseJsonPaths = None
            logger.debug("Taking MEGRE information from nifti files and utilizing general echo number and time information")
            if echoNumber is None or echoTimes is None:
                logger.error(f"No Echo Number and Echo times for the given magnitude and phase images. This is to few information to work with. Magnitude file: {self._magnitudePaths}")
                self._magnitudePaths = self._magnitudeJsonPaths = self._phasePaths = self._phaseJsonPaths = None

            #TODO Fix this: just assume that jsons must be present. Otherwise instruct user to create jsons files with necessary information.
            self.echoNumber = echoNumber
            self.echoTimes = echoTimes

        logger.debug(f"Identified: {self}")

    def get_magnitude_paths(self):
        return [mag.imagePath for mag in self.magnitude]

    def get_phase_paths(self):
        return [pha.imagePath for pha in self.phase]

    def get_b0_directions(self):
        resList = []
        for mag in self.magnitude:
            ori = mag.getAttribute("ImageOrientationPatientDICOM")
            Xz = ori[2]
            Yz = ori[5]
            Zxyz = cross(ori[0:3], ori[3:6])
            Zz = Zxyz[2]
            resList.append([-Xz, -Yz, Zz])
        for i in range(1, len(resList)):
            eps = 0.000001
            if sum([abs(a_i - b_i) for a_i, b_i in zip(resList[0], resList[i])]) > eps:
                logger.error(
                    f"Different b0 field directions from different echos for, returning None and failing for the session: {self.magnitude.jsonPaths[0]}")
        logger.info("Calculated B0 field direction of image based on ImageOrientationPatientDICOM: {H}")
        return resList[0]

    def validate(self) -> bool:
        if self.echoNumber is None or self.echoTimes is None:
            return False
        if self.magnitude is None or self.phase is None:
            return False
        if len(self.magnitude) <= 2:
            logger.warning("Number of magnitude/Phase images must be greater than 2")
            return False
        if len(self.echoTimes) < 2:
            return False
        if not len(self.magnitude) == len(self.phase) == len(self.echoTimes):
            return False
        return True

    def sort_by_echoTimes(self):
        magEchoTimes = [mag.getAttribute("EchoTime") for mag in self.magnitude]
        phaEchoTimes = [pha.getAttribute("EchoTime") for pha in self.phase]
        #Error check if Echo times are missing:
        if any([mag is None for mag in magEchoTimes]) or any([pha is None for pha in phaEchoTimes]):
            logger.error(f"Found no magnitude/phase echo times for {magEchoTimes}/{self._magnitudePaths} and {phaEchoTimes}/{self._phasePaths} for sorting. This may result in errors later on.")
            return None
        # Combine the lists into a list of tuples
        combinedMag = list(zip(self.magnitude,  magEchoTimes))
        combinedPha = list(zip(self.phase, phaEchoTimes))
        # Sort the combined list based on the echoTimes values
        combinedMag.sort(key=lambda x: x[1])
        combinedPha.sort(key=lambda x: x[1])
        logger.debug(f"Sorting by Echo. \nResult Magnitude: {combinedMag}, \nResult Phase: {combinedPha}")
        # Unzip the sorted combined list back into individual lists
        self.magnitude, self.echoTimes = zip(*combinedMag)
        self.phase, _ = zip(*combinedPha)


    @staticmethod
    def _match_lists(list1, list2):
        if not (list1 and list2):
            logger.info(f"Cannot Match lists when one list is None: \nList 1: {list1}, \nList 2: {list2}")
            return None, None
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
