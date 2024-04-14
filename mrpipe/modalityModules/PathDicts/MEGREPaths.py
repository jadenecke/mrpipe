import os.path
from typing import List
from mrpipe.meta import LoggerModule
import numpy as np
from mrpipe.modalityModules.PathDicts.BasePaths import PathBase
from mrpipe.meta.PathClass import Path
from mrpipe.meta.PathCollection import PathCollection

logger = LoggerModule.Logger()

class PathDictMEGRE(PathCollection):

    echoNumber = None
    echoTimings = None

    @staticmethod
    def setEchoNumber(echoNumber):
        if not isinstance(echoNumber, int):
            logger.error("Echo Timings is not list but got {}".format(type(echoNumber)))
        elif PathDictMEGRE.echoNumber is None:
            PathDictMEGRE.echoNumber = echoNumber
        else:
            logger.error(f"Echo Number already set: {PathDictMEGRE.echoNumber}. Not setting new echo number: {echoNumber}")
    @staticmethod
    def getEchoNumber():
        return PathDictMEGRE.echoNumber

    @staticmethod
    def setEchoTimings(echoTimings):
        if not isinstance(echoTimings, List):
            logger.error("Echo Timings is not list but got {}".format(type(echoTimings)))
        elif PathDictMEGRE.echoTimings is None:
            PathDictMEGRE.echoTimings = echoTimings
        else:
            logger.error(f"Echo Numbers already set: {PathDictMEGRE.echoNumber}. Not setting new echoNumber: {echoTimings}")

    @staticmethod
    def getEchoTimings() -> List[float]:
        return PathDictMEGRE.echoTimings

    class Bids(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="megre_bids")
            self.basedir = Path(os.path.join(basepaths.bidsPath, filler), isDirectory=True)
            self.basename = Path(os.path.join(basepaths.bidsPath, filler,
                                        nameFormatter.format(subj=sub, ses=ses, basename=basename)))
            self.magnitude = []
            for i in range(PathDictMEGRE.echoNumber):
                en = i+1
                echo, pattern = Path.Identify(f"MEGRE Magnitude Echo {en}", pattern=r"[^\._]+_[^_]+_(.*_e[0-9]+.*)\.nii.*",
                                                         searchDir=self.basedir, previousPatterns=[
                        nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".nii*" for pattern in
                        PathDictMEGRE.getFilePatterns(f"MEGREPattern_mag_{en}")])
                self.magnitude.append(echo)
                if pattern is not None:
                    PathDictMEGRE.setFilePatterns(f"MEGREPattern_mag_{en}", pattern)

            self.phase = []
            for i in range(PathDictMEGRE.echoNumber):
                en = i + 1
                echo, pattern = Path.Identify(f"MEGRE Phase Echo {en}",
                                              pattern=r"[^\._]+_[^_]+_(.*_e[0-9]+.*_ph[a]*.*)\.nii.*",
                                              searchDir=self.basedir, previousPatterns=[
                        nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".nii*" for pattern in
                        PathDictMEGRE.getFilePatterns(f"MEGREPattern_pha_{en}")])
                self.phase.append(echo)
                if pattern is not None:
                    PathDictMEGRE.setFilePatterns(f"MEGREPattern_pha_{en}", pattern)

            #json Files
            self.magnitudeJSON = []
            for i in range(PathDictMEGRE.echoNumber):
                en = i + 1
                echo, pattern = Path.Identify(f"MEGRE Magnitude JSON Echo {en}",
                                              pattern=r"[^\._]+_[^_]+_(.*_e[0-9]+.*)\.json",
                                              searchDir=self.basedir, previousPatterns=[
                        nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".json" for pattern in
                        PathDictMEGRE.getFilePatterns(f"MEGREPattern_mag_{en}")])
                self.magnitudeJSON.append(echo)
                if pattern is not None:
                    PathDictMEGRE.setFilePatterns(f"MEGREPattern_mag_{en}", pattern)

            self.phaseJSON = []
            for i in range(PathDictMEGRE.echoNumber):
                en = i + 1
                echo, pattern = Path.Identify(f"MEGRE Phase JSON Echo {en}",
                                              pattern=r"[^\._]+_[^_]+_(.*_e[0-9]+.*_ph[a]*.*)\.json",
                                              searchDir=self.basedir, previousPatterns=[
                        nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".json" for pattern in
                        PathDictMEGRE.getFilePatterns(f"MEGREPattern_pha_{en}")])
                self.phaseJSON.append(echo)
                if pattern is not None:
                    PathDictMEGRE.setFilePatterns(f"MEGREPattern_pha_{en}", pattern)

    class Bids_processed(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="megre_bidsProcessed")
            self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
            self.flair = Path(self.basename + ".nii.gz")
            self.json = Path(self.basename + ".json")
            #To T1w
            self.toT1w_prefix = self.basename + "_toT1w"
            self.toT1w_toT1w = (self.toT1w_prefix + "Warped.nii.gz").setStatic()
            self.toT1w_0GenericAffine = (self.toT1w_prefix + "0GenericAffine.mat").setStatic()
            self.toT1w_InverseWarped = (self.toT1w_prefix + "InverseWarped.nii.gz").setStatic().setCleanup()

            self.iso1mm = self.Iso1mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)


        class Iso1mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                super().__init__(name="megre_bidsProcessed_iso1mm")
                basename = basename + "_iso1mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler, "resample_iso1mm"), isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
                # To T1w
                self.baseimage = self.basename + "_toT1w.nii.gz"

                #ToMNI
                self.toMNI = self.basename + "_toMNI.nii.gz"


    class Meta_QC(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="megre_metaQC")
            self.basedir = Path(os.path.join(basepaths.qcPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename), isDirectory=False)
            self.ToT1w_native_slices = self.basename + "flairToT1w_native.png"


    class Bids_statistics(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="megre_bidsStatistic")
            self.basedir = Path(os.path.join(basepaths.bidsStatisticsPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))

    def __init__(self, sub, ses, basepaths, basedir="FLAIR", nameFormatter="{subj}_{ses}_{basename}",
                 modalityBeforeSession=False, basename="FLAIR"):
        super().__init__(name="FLAIR")
        if modalityBeforeSession:
            filler = os.path.join(sub, basedir, ses)
        else:
            filler = os.path.join(sub, ses, basedir)

        self.inquireEchoNumber()


        self.bids = self.Bids(filler, basepaths, sub, ses, nameFormatter, basename)
        self.bids_processed = self.Bids_processed(filler, basepaths, sub, ses, nameFormatter, basename)
        self.bids_statistics = self.Bids_statistics(filler, basepaths, sub, ses, nameFormatter, basename)
        self.meta_QC = self.Meta_QC(filler, basepaths, sub, ses, nameFormatter, basename)
        self.echoNumber: int = None
        self.echoTimings: List[float]

    def inquireEchoNumber(self):
        if self.getEchoNumber() is None:
            while True:
                try:
                    print(f"Please specify the number of Echoes:")
                    # Wait for the user to enter a number to specify a number of echoes
                    echoNumber = int(input())
                    if echoNumber < 2:
                        print("Invalid Input, echo number must be >= 2. Please try again:")
                    else:
                        self.setEchoNumber(int(echoNumber))
                        print("Echo number set to: " + str(self.getEchoNumber()))
                        break
                except Exception as e:
                    print("Invalid Input, please try again:")

        if self.getEchoTimings() is None:
            while True:
                try:
                    print(f"Please specify the Echo Timings seperated by spaces in milliseconds\n"
                          f"(echo delta will be inferred and even echo spacing is required):")
                    # Wait for the user to enter a number to specify a number of echoes
                    echoTimings = input().split()
                    for i in range(len(echoTimings)):  # convert each item to int type
                        echoTimings[i] = float(echoTimings[i])

                    if len(echoTimings) != self.getEchoNumber():
                        print(f"Invalid Input, length of Echoes timings ({len(echoTimings)}) must be equal to the number of Echoes ({self.getEchoNumber()})")
                        raise Exception()
                    for i in range(len(echoTimings)):  # check that everything is in ascending order
                        if i > 0:
                            if echoTimings[i-1] >= echoTimings[i]:
                                print("Echo timings must be entered in an ascending order.")
                                raise Exception()

                    if any([t > 0.1 for t in echoTimings]):
                        print("Echo timing larger than 100 milliseconds, this is highly unlikely to occur.")
                        raise Exception()

                    if any(np.diff(echoTimings) > ((echoTimings[len(echoTimings) - 1] - echoTimings[0]) / (len(echoTimings) - 1))*1.1):
                        print("Echo spacing varies by more then 10%, this algorithem only works with evenly spaced echoes.")
                        raise Exception()

                    self.setEchoTimings(echoTimings)
                    print("Echo timings set to: " + str(self.getEchoTimings()))
                    break
                except Exception as e:
                    print("Invalid Input, please try again:")
