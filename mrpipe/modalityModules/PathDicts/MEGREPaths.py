import os.path
from typing import List
from mrpipe.meta import LoggerModule
import numpy as np
import glob
from mrpipe.modalityModules.PathDicts.BasePaths import PathBase
from mrpipe.meta.PathClass import Path
from mrpipe.meta.PathCollection import PathCollection
from mrpipe.meta.ImageSeries import MEGRE

logger = LoggerModule.Logger()

class PathDictMEGRE(PathCollection):

    echoNumberCommon = None
    echoTimingsCommon = None

    @staticmethod
    def setEchoNumber(echoNumber):
        if not isinstance(echoNumber, int):
            logger.error("Echo Timings is not list but got {}".format(type(echoNumber)))
        elif PathDictMEGRE.echoNumberCommon is None:
            PathDictMEGRE.echoNumberCommon = echoNumber
        else:
            logger.error(f"Echo Number already set: {PathDictMEGRE.echoNumberCommon}. Not setting new echo number: {echoNumber}")
    @staticmethod
    def getEchoNumber():
        return PathDictMEGRE.echoNumberCommon

    @staticmethod
    def setEchoTimings(echoTimings):
        if not isinstance(echoTimings, List):
            logger.error("Echo Timings is not list but got {}".format(type(echoTimings)))
        elif PathDictMEGRE.echoTimingsCommon is None:
            PathDictMEGRE.echoTimingsCommon = echoTimings
        else:
            logger.error(f"Echo Numbers already set: {PathDictMEGRE.echoNumberCommon}. Not setting new echoNumber: {echoTimings}")

    @staticmethod
    def getEchoTimings() -> List[float]:
        return PathDictMEGRE.echoTimingsCommon

    class Bids(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="megre_bids")
            self.basedir = Path(os.path.join(basepaths.bidsPath, filler), isDirectory=True)
            self.basename = Path(os.path.join(basepaths.bidsPath, filler,
                                        nameFormatter.format(subj=sub, ses=ses, basename=basename)))
            self.megre = MEGRE(self.basedir)

            # for i in range(PathDictMEGRE.echoNumber):
            #     en = i+1
            #     echo, pattern = Path.Identify(f"MEGRE Magnitude Echo {en}", pattern=r"[^\._]+_[^_]+_(.*_?e?[0-9]*.*)\.nii.*",
            #                                              searchDir=self.basedir, previousPatterns=[
            #             nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".nii*" for pattern in
            #             PathDictMEGRE.getFilePatterns(f"MEGREPattern_mag_{en}")])
            #     self.magnitude.append(echo)
            #     if pattern is not None:
            #         PathDictMEGRE.setFilePatterns(f"MEGREPattern_mag_{en}", pattern)

            # for i in range(PathDictMEGRE.echoNumber):
            #     en = i + 1
            #     echo, pattern = Path.Identify(f"MEGRE Phase Echo {en}",
            #                                   pattern=r"[^\._]+_[^_]+_(.*_?e?[0-9]*.*_ph[a]*.*)\.nii.*",
            #                                   searchDir=self.basedir, previousPatterns=[
            #             nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".nii*" for pattern in
            #             PathDictMEGRE.getFilePatterns(f"MEGREPattern_pha_{en}")])
            #     self.phase.append(echo)
            #     if pattern is not None:
            #         PathDictMEGRE.setFilePatterns(f"MEGREPattern_pha_{en}", pattern)

            #json Files
            # for i in range(PathDictMEGRE.echoNumber):
            #     en = i + 1
            #     echo, pattern = Path.Identify(f"MEGRE Magnitude JSON Echo {en}",
            #                                   pattern=r"[^\._]+_[^_]+_(.*_e[0-9]+.*)\.json",
            #                                   searchDir=self.basedir, previousPatterns=[
            #             nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".json" for pattern in
            #             PathDictMEGRE.getFilePatterns(f"MEGREPattern_mag_{en}")])
            #     self.magnitudeJSON.append(echo)
            #     if pattern is not None:
            #         PathDictMEGRE.setFilePatterns(f"MEGREPattern_mag_{en}", pattern)

            # for i in range(PathDictMEGRE.echoNumber):
            #     en = i + 1
            #     echo, pattern = Path.Identify(f"MEGRE Phase JSON Echo {en}",
            #                                   pattern=r"[^\._]+_[^_]+_(.*_e[0-9]+.*_ph[a]*.*)\.json",
            #                                   searchDir=self.basedir, previousPatterns=[
            #             nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".json" for pattern in
            #             PathDictMEGRE.getFilePatterns(f"MEGREPattern_pha_{en}")])
            #     self.phaseJSON.append(echo)
            #     if pattern is not None:
            #         PathDictMEGRE.setFilePatterns(f"MEGREPattern_pha_{en}", pattern)


    class Bids_processed(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="megre_bidsProcessed")
            basenameWithoutPath = nameFormatter.format(subj=sub, ses=ses, basename=basename)
            self.baseString = basenameWithoutPath
            self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler), isDirectory=True)
            self.basename = self.basedir.join(basenameWithoutPath)
            self.phase4D = Path(self.basename + "_phase4D.nii.gz")
            self.magnitude4d = Path(self.basename + "_mag4D.nii.gz")
            self.chiSepDir = self.basedir.join("ChiSeperation")
            self.brainMask_toMEGRE = Path(self.basename + "_brainMask_fromT1w.nii.gz")

            #chisep output files:
            self.chiParamagnetic = self.chiSepDir.join(basenameWithoutPath + "_ChiSep-Para.nii.gz")
            self.chiDiamagnetic = self.chiSepDir.join(basenameWithoutPath + "_ChiSep-Dia.nii.gz")
            self.chiTotal = self.chiSepDir.join(basenameWithoutPath + "_ChiSep-Total.nii.gz")
            self.QSM = self.chiSepDir.join(basenameWithoutPath + "_QSM.nii.gz")
            self.localfild = self.chiSepDir.join(basenameWithoutPath + "_localfield.nii.gz")
            self.unwrappedPhase = self.chiSepDir.join(basenameWithoutPath + "_unwrappedPhase.nii.gz")
            self.fieldMap = self.chiSepDir.join(basenameWithoutPath + "_fieldMap.nii.gz")
            self.B0 = self.chiSepDir.join(basenameWithoutPath + "_B0.nii.gz")
            self.NStd = self.chiSepDir.join(basenameWithoutPath + "_N_std.nii.gz")
            self.BrainMaskAfterVSharp = self.chiSepDir.join(basenameWithoutPath + "_mask_brain_VSHARP.nii.gz")


            #TODO: shift to new module
            #To T1w
            self.toT1w_prefix = self.basename + "_toT1w"
            self.toT1w_toT1w = (self.toT1w_prefix + "Warped.nii.gz").setStatic()
            self.toT1w_0GenericAffine = (self.toT1w_prefix + "0GenericAffine.mat").setStatic()
            self.toT1w_InverseWarped = (self.toT1w_prefix + "InverseWarped.nii.gz").setStatic().setCleanup()



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
            self.ToT1w_native_slices = self.basename + "_ToT1w_native.png"

            self.chiSepDia_native_slices = self.basename + "_chiSepDia_native.png"
            self.chiSepPara_native_slices = self.basename + "_chiSepPara_native.png"
            self.chiSepQSM_native_slices = self.basename + "_chiSepQSM_native.png"


    class Bids_statistics(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="megre_bidsStatistic")
            self.basedir = Path(os.path.join(basepaths.bidsStatisticsPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))

    def __init__(self, sub, ses, basepaths, basedir="MEGRE", nameFormatter="{subj}_{ses}_{basename}",
                 modalityBeforeSession=False, basename="MEGRE"):
        super().__init__(name="MEGRE")
        if modalityBeforeSession:
            filler = os.path.join(sub, basedir, ses)
        else:
            filler = os.path.join(sub, ses, basedir)

        self.inquireEchoNumber()
        self.subjectName = sub
        self.sessionName = ses
        self.bids = self.Bids(filler, basepaths, sub, ses, nameFormatter, basename)
        self.bids_processed = self.Bids_processed(filler, basepaths, sub, ses, nameFormatter, basename)
        self.bids_statistics = self.Bids_statistics(filler, basepaths, sub, ses, nameFormatter, basename)
        self.meta_QC = self.Meta_QC(filler, basepaths, sub, ses, nameFormatter, basename)
        self.echoNumberCommon: int = None # not used because not
        self.echoTimingsCommon: List[float]

    def verify(self):
        #TODO: This could be changed to allow for non-matching echo number, as the pipeline is flexible enough to handle it from the json information (if that is present)
        if len(self.bids.megre.magnitude) != PathDictMEGRE.echoNumberCommon:
            logger.warning(f"Subject with non-matching magnitude number found, excluding subject {self.subjectName} ({self.sessionName})")
            return None
        if len(self.bids.megre.phase) != PathDictMEGRE.echoNumberCommon:
            logger.warning(f"Subject with non-matching magnitude number found, excluding subject {self.subjectName} ({self.sessionName})")
            return None
        return self


    def inquireEchoNumber(self):
        if self.getEchoNumber() is None:
            confEchoNumber = self.getConfigElement("MEGERE_EchoNumber")
            if isinstance(confEchoNumber, list):
                confEchoNumber = confEchoNumber[0]
            if confEchoNumber is not None:
                logger.process(f'Got MEGRE Echo number from config: {confEchoNumber}')
                self.setEchoNumber(confEchoNumber)
            else:
                while True:
                    try:
                        print(f"Please specify the number of Echoes:")
                        # Wait for the user to enter a number to specify a number of echoes
                        echoNumber = int(input())
                        if echoNumber < 2:
                            print("Invalid Input, echo number must be >= 2. Please try again:")
                        else:
                            self.setEchoNumber(int(echoNumber))
                            self.setConfigElement("MEGERE_EchoNumber", int(echoNumber), overwrite=True)
                            print("Echo number set to: " + str(self.getEchoNumber()))
                            break
                    except Exception as e:
                        print("Invalid Input, please try again:")

        if self.getEchoTimings() is None:
            confEchoTimings = self.getConfigElement("MEGERE_EchoTimings")
            if confEchoTimings is not None:
                logger.process(f'Got MEGRE Echo Timings from config: {confEchoTimings}')
                self.setEchoTimings(confEchoTimings)
            else:
                while True:
                    try:
                        print(f"Please specify the Echo Timings seperated by spaces in seconds\n"
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
                        self.setConfigElement("MEGERE_EchoTimings", echoTimings, overwrite=True)
                        print("Echo timings set to: " + str(self.getEchoTimings()))
                        break
                    except Exception as e:
                        print("Invalid Input, please try again:")
