import os.path
from typing import List
from mrpipe.meta import LoggerModule
import numpy as np
import glob
from mrpipe.modalityModules.PathDicts.BasePaths import PathBase
from mrpipe.meta.PathClass import Path
from mrpipe.meta.PathClass import StatsFilePath
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
            self.phase4DScaled0p65 = Path(self.basename + "_phase4D_ScaledMax0p65.nii.gz")
            self.magnitude4dScaled0p65 = Path(self.basename + "_mag4D_ScaledMax0p65.nii.gz")
            self.magnitudeE1Scaled0p65 = Path(self.basename + "_mag_e1_ScaledMax0p65.nii.gz")

            self.chiSepDir = self.basedir.join("ChiSeperation", isDirectory=True)
            self.clearswiDir = self.basedir.join("clearSWI", isDirectory=True)
            self.brainMask_toMEGRE = Path(self.basename + "_brainMaskChiSep_fromT1w.nii.gz")

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

            #clearswi output files:
            self.clearswi = self.clearswiDir.join("clearswi.nii.gz").setStatic()
            self.clearswiMIP = self.clearswiDir.join("mip.nii.gz").setStatic().setCleanup()
            self.clearswiSettings = self.clearswiDir.join("settings_clearswi.txt").setStatic()
            self.clearswiCitations = self.clearswiDir.join("citations_clearswi.nii.gz").setStatic().setCleanup()
            self.clearswi_mip_calculated = self.clearswiDir.join("mip_calculated.nii.gz")

            #Shivai CMB segmentation:
            self.shivai_outputDir = self.basedir.join("shivaiCMB", isDirectory=True)
            self.shivai_CMB_QC = self.shivai_outputDir.join("results").join("report").join(self.baseString).join("Shiva_report.pdf").setStatic()
            self.shivai_CMB_Probability_SegSpace = self.shivai_outputDir.join("results").join("segmentations").join("cmb_segmentation_swi-space").join(self.baseString + "_cmb_map.nii.gz").setStatic()
            self.shivai_CMB_Mask_segSapce = self.shivai_outputDir.join("results").join("segmentations").join("cmb_segmentation_swi-space").join(self.baseString).join("labelled_cmb.nii.gz").setStatic()

            self.shivai_CMB_Mask_labels = Path(self.basename + "_CMB_CompLabel.nii.gz")
            self.shivai_CMB_Probability = Path(self.basename + "_CMB_Probability.nii.gz")

            self.fromT1w_GMWMMask = Path(self.basename + "_FromT1w_SynthSeg_GMWMMask.nii.gz")
            self.shivai_CMB_Mask_labelsLimited = Path(self.basename + "_CMB_CompLabelGMWMLimited.nii.gz")
            self.shivai_CMB_ProbabilityLimited = Path(self.basename + "_CMB_ProbabilityGMWMLimited.nii.gz")

            self.shivai_CMB_Mask = Path(self.basename + "_CMB_Mask.nii.gz")



            #TODO: shift to new module
            #To T1w
            self.toT1w_prefix = self.basename + "_toT1w"
            self.toT1w_toT1w = (self.toT1w_prefix + "Warped.nii.gz").setStatic()
            self.toT1w_0GenericAffine = (self.toT1w_prefix + "0GenericAffine.mat").setStatic()
            self.toT1w_InverseWarped = (self.toT1w_prefix + "InverseWarped.nii.gz").setStatic().setCleanup()

            self.chiDiamagnetic_toT1w = self.basename + "_ChiSep-Dia_toT1w.nii.gz"
            self.chiParamagnetic_toT1w = self.basename + "_ChiSep-Para_toT1w.nii.gz"
            self.QSM_toT1w = self.basename + "_QSM_toT1w.nii.gz"

            #From T1w
            self.fromT1w_T1w = self.basename + "_fromT1w_T1w.nii.gz"
            self.fromT1w_synthSeg = self.basename + "_fromT1w_synthSeg.nii.gz"
            self.fromT1w_WMCortical_thr0p5_ero1mm = self.basename + "_fromT1w_WMCortical_thr0p5_ero1mm.nii.gz"
            self.fromT1w_GMCortical_thr0p5_ero1mm = self.basename + "_fromT1w_GMCortical_thr0p5_ero1mm.nii.gz"

            #From Flair
            self.fromFlair_NAWMCortical_thr0p5_ero1mm = self.basename + "_fromFlair_NAWMCortical_thr0p5_ero1mm.nii.gz"
            self.fromFlair_WMH = self.basename + "_fromFlair_WMH.nii.gz"

            self.iso1mm = self.Iso1mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)
            self.iso1p5mm = self.Iso1p5mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses,
                                          nameFormatter=nameFormatter,
                                          basename=basename)
            self.iso2mm = self.Iso2mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)
            self.iso3mm = self.Iso3mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)


        class Iso1mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                super().__init__(name="megre_bidsProcessed_iso1mm")
                basename = basename + "_iso1mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler, "resample_iso1mm"), isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
                # To T1w
                self.chiDiamagnetic_toT1w = self.basename + "ChiSep-Dia_toT1w.nii.gz"
                self.chiParamagnetic_toT1w = self.basename + "_ChiSep-Para_toT1w.nii.gz"
                self.QSM_toT1w = self.basename + "_QSM_toT1w.nii.gz"

                #ToMNI
                self.chiDiamagnetic_toMNI = self.basename + "ChiSep-Dia_toMNI.nii.gz"
                self.chiParamagnetic_toMNI = self.basename + "_ChiSep-Para_toMNI.nii.gz"
                self.QSM_toMNI = self.basename + "_QSM_toMNI.nii.gz"

                # from MNI atlas
                self.atlas_HammersmithLobar_megreNative = self.basename + "_HammersmithLobar_fromMNI.nii.gz"
                self.atlas_HammersmithLobar_megreNative_maskedWM0p5_ero1mm = self.basename + "_HammersmithLobar_fromMNI_maskedWM0p5_ero1mm.nii.gz"

                self.atlas_JHUDTI_1mm_megreNative = self.basename + "_JHUDTI_1mm_fromMNI.nii.gz"
                self.atlas_JHUDTI_1mm_megreNative_maskedWM0p5_ero1mm = self.basename + "_JHUDTI_1mm_fromMNI_maskedWM0p5_ero1mm.nii.gz"

                self.atlas_Schaefer200_17Net_megreNative = self.basename + "_Schaefer200_17Net_fromMNI.nii.gz"
                self.atlas_Schaefer200_17Net_megreNative_maskedGMCortical0p5_ero1mm = self.basename + "_Schaefer200_17Net_fromMNI_maskedGMCortical0p5_ero1mm.nii.gz"

                self.atlas_Mindboggle101_megreNative = self.basename + "_Mindboggle101_fromMNI.nii.gz"
                self.atlas_Mindboggle101_megreNative_maskedGMCortical0p5_ero1mm = self.basename + "_Mindboggle101_fromMNI_maskedGMCortical0p5_ero1mm.nii.gz"

        class Iso1p5mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                super().__init__(name="megre_bidsProcessed_iso1p5mm")
                basename = basename + "_iso1p5mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler, "resample_iso1p5mm"), isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
                # To T1w
                self.chiDiamagnetic_toT1w = self.basename + "ChiSep-Dia_toT1w.nii.gz"
                self.chiParamagnetic_toT1w = self.basename + "_ChiSep-Para_toT1w.nii.gz"
                self.QSM_toT1w = self.basename + "_QSM_toT1w.nii.gz"

                #ToMNI
                self.chiDiamagnetic_toMNI = self.basename + "ChiSep-Dia_toMNI.nii.gz"
                self.chiParamagnetic_toMNI = self.basename + "_ChiSep-Para_toMNI.nii.gz"
                self.QSM_toMNI = self.basename + "_QSM_toMNI.nii.gz"

        class Iso2mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                super().__init__(name="megre_bidsProcessed_iso2mm")
                basename = basename + "_iso2mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler, "resample_iso2mm"), isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
                # To T1w
                self.chiDiamagnetic_toT1w = self.basename + "ChiSep-Dia_toT1w.nii.gz"
                self.chiParamagnetic_toT1w = self.basename + "_ChiSep-Para_toT1w.nii.gz"
                self.QSM_toT1w = self.basename + "_QSM_toT1w.nii.gz"

                #ToMNI
                self.chiDiamagnetic_toMNI = self.basename + "ChiSep-Dia_toMNI.nii.gz"
                self.chiParamagnetic_toMNI = self.basename + "_ChiSep-Para_toMNI.nii.gz"
                self.QSM_toMNI = self.basename + "_QSM_toMNI.nii.gz"

        class Iso3mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                super().__init__(name="megre_bidsProcessed_iso3mm")
                basename = basename + "_iso3mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler, "resample_iso3mm"), isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
                # To T1w
                self.chiDiamagnetic_toT1w = self.basename + "ChiSep-Dia_toT1w.nii.gz"
                self.chiParamagnetic_toT1w = self.basename + "_ChiSep-Para_toT1w.nii.gz"
                self.QSM_toT1w = self.basename + "_QSM_toT1w.nii.gz"

                #ToMNI
                self.chiDiamagnetic_toMNI = self.basename + "ChiSep-Dia_toMNI.nii.gz"
                self.chiParamagnetic_toMNI = self.basename + "_ChiSep-Para_toMNI.nii.gz"
                self.QSM_toMNI = self.basename + "_QSM_toMNI.nii.gz"



    class Meta_QC(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="megre_metaQC")
            self.basedir = Path(os.path.join(basepaths.qcPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename), isDirectory=False)
            self.ToT1w_native_slices = self.basename + "_ToT1w_native.png"

            self.chiSepDia_native_slices = self.basename + "_chiSepDia_native.png"
            self.chiSepPara_native_slices = self.basename + "_chiSepPara_native.png"
            self.chiSepQSM_native_slices = self.basename + "_chiSepQSM_native.png"

            self.shivai_CMB_VisMCB = self.basename + "_CMB.png"


    class Bids_statistics(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="megre_bidsStatistic")
            self.basedir = Path(os.path.join(basepaths.bidsStatisticsPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))

            # chiSep Results from T1w
            chiSepResults = str(self.basename + "_ChiSepResults.json")
            self.chiSepResults_chiNeg_mean_WMCortical_0p5_ero1mm = StatsFilePath(chiSepResults, attributeName="chiSepResults_chiNeg_WMCortical_0p5_ero1mm", subject=sub, session=ses)
            self.chiSepResults_chiPos_mean_WMCortical_0p5_ero1mm = StatsFilePath(chiSepResults, attributeName="chiSepResults_chiPos_WMCortical_0p5_ero1mm", subject=sub, session=ses)
            self.chiSepResults_QSM_mean_WMCortical_0p5_ero1mm = StatsFilePath(chiSepResults, attributeName="chiSepResults_QSM_WMCortical_0p5_ero1mm", subject=sub, session=ses)

            self.chiSepResults_chiNeg_mean_GMCortical_0p5_ero1mm = StatsFilePath(chiSepResults, attributeName="chiSepResults_chiNeg_GMCortical_0p5_ero1mm", subject=sub, session=ses)
            self.chiSepResults_chiPos_mean_GMCortical_0p5_ero1mm = StatsFilePath(chiSepResults, attributeName="chiSepResults_chiPos_GMCortical_0p5_ero1mm", subject=sub, session=ses)
            self.chiSepResults_QSM_mean_GMCortical_0p5_ero1mm = StatsFilePath(chiSepResults, attributeName="chiSepResults_QSM_GMCortical_0p5_ero1mm", subject=sub, session=ses)

            # chiSep Results from Flair
            self.chiSepResults_chiNeg_mean_NAWMCortical_0p5_ero1mm = StatsFilePath(chiSepResults, attributeName="chiSepResults_chiNeg_NAWMCortical_0p5_ero1mm", subject=sub, session=ses)
            self.chiSepResults_chiPos_mean_NAWMCortical_0p5_ero1mm = StatsFilePath(chiSepResults, attributeName="chiSepResults_chiPos_NAWMCortical_0p5_ero1mm", subject=sub, session=ses)
            self.chiSepResults_QSM_mean_NAWMCortical_0p5_ero1mm = StatsFilePath(chiSepResults, attributeName="chiSepResults_QSM_NAWMCortical_0p5_ero1mm", subject=sub, session=ses)

            self.chiSepResults_chiNeg_mean_WMH = StatsFilePath(chiSepResults, attributeName="chiSepResults_chiNeg_WMH", subject=sub, session=ses)
            self.chiSepResults_chiPos_mean_WMH = StatsFilePath(chiSepResults, attributeName="chiSepResults_chiPos_WMH", subject=sub, session=ses)
            self.chiSepResults_QSM_mean_WMH = StatsFilePath(chiSepResults, attributeName="chiSepResults_QSM_WMH", subject=sub, session=ses)

            # chiSep Results from MNI atlases
            self.chiSepResults_chiNeg_mean_HammersmithLobar_maskedWM0p5_ero1mm = self.basename + "chiSepResults_chiNeg_mean_HammersmithLobar_maskedWM0p5_ero1mm.csv"
            self.chiSepResults_chiPos_mean_HammersmithLobar_maskedWM0p5_ero1mm = self.basename + "chiSepResults_chiPos_mean_HammersmithLobar_maskedWM0p5_ero1mm.csv"
            self.chiSepResults_QSM_mean_HammersmithLobar_maskedWM0p5_ero1mm = self.basename + "chiSepResults_QSM_mean_HammersmithLobar_maskedWM0p5_ero1mm.csv"

            self.chiSepResults_chiNeg_mean_JHUDTI_1mm_maskedWM0p5_ero1mm = self.basename + "chiSepResults_chiNeg_mean_JHUDTI_1mm_maskedWM0p5_ero1mm.csv"
            self.chiSepResults_chiPos_mean_JHUDTI_1mm_maskedWM0p5_ero1mm = self.basename + "chiSepResults_chiPos_mean_JHUDTI_1mm_maskedWM0p5_ero1mm.csv"
            self.chiSepResults_QSM_mean_JHUDTI_1mm_maskedWM0p5_ero1mm = self.basename + "chiSepResults_QSM_mean_JHUDTI_1mm_maskedWM0p5_ero1mm.csv"

            self.chiSepResults_chiNeg_mean_Schaefer200_17Net_maskedGM0p5_ero1mm = self.basename + "chiSepResults_chiNeg_mean_Schaefer200_17Net_maskedGM0p5_ero1mm.csv"
            self.chiSepResults_chiPos_mean_Schaefer200_17Net_maskedGM0p5_ero1mm = self.basename + "chiSepResults_chiPos_mean_Schaefer200_17Net_maskedGM0p5_ero1mm.csv"
            self.chiSepResults_QSM_mean_Schaefer200_17Net_maskedGM0p5_ero1mm = self.basename + "chiSepResults_QSM_mean_Schaefer200_17Net_maskedGM0p5_ero1mm.csv"

            self.chiSepResults_chiNeg_mean_Mindboggle101_maskedGM0p5_ero1mm = self.basename + "chiSepResults_chiNeg_mean_Mindboggle101_maskedGM0p5_ero1mm.csv"
            self.chiSepResults_chiPos_mean_Mindboggle101_maskedGM0p5_ero1mm = self.basename + "chiSepResults_chiPos_mean_SMindboggle101_maskedGM0p5_ero1mm.csv"
            self.chiSepResults_QSM_mean_Mindboggle101_maskedGM0p5_ero1mm = self.basename + "chiSepResults_QSM_mean_Mindboggle101_maskedGM0p5_ero1mm.csv"


            #Lesion Results
            lesionResults = str(self.basename + "_LesionResults.json")
            self.lesionResults_CMB_Count = StatsFilePath(lesionResults, attributeName="CMB_Count", subject=sub, session=ses)

    def __init__(self, sub, ses, basepaths, basedir="MEGRE", nameFormatter="{subj}_{ses}_{basename}",
                 modalityBeforeSession=False, basename="MEGRE"):
        super().__init__(name="MEGRE")
        if modalityBeforeSession:
            fillerBids = os.path.join(sub, basedir, ses)
            filler = os.path.join(sub, basename, ses)
        else:
            fillerBids = os.path.join(sub, ses, basedir)
            filler = os.path.join(sub, ses, basename)

        self.inquireEchoNumber()
        self.subjectName = sub
        self.sessionName = ses
        self.bids = self.Bids(fillerBids, basepaths, sub, ses, nameFormatter, basename)
        self.bids_processed = self.Bids_processed(filler, basepaths, sub, ses, nameFormatter, basename)
        self.bids_statistics = self.Bids_statistics(filler, basepaths, sub, ses, nameFormatter, basename)
        self.meta_QC = self.Meta_QC(filler, basepaths, sub, ses, nameFormatter, basename)
        self.echoNumberCommon: int = None  # not used because not
        self.echoTimingsCommon: List[float]

    def verify(self):
        if not self.bids.megre.validate():
            logger.warning(
                f"Subject without valid MEGRE specifications found, excluding subject {self.subjectName} ({self.sessionName})")
            return None
        #TODO: This could be changed to allow for non-matching echo number, as the pipeline is flexible enough to handle it from the json information (if that is present)

        # if len(self.bids.megre.magnitude) != PathDictMEGRE.echoNumberCommon:
        #     logger.warning(f"Subject with non-matching magnitude number found, excluding subject {self.subjectName} ({self.sessionName})")
        #     return None
        # if len(self.bids.megre.phase) != PathDictMEGRE.echoNumberCommon:
        #     logger.warning(f"Subject with non-matching magnitude number found, excluding subject {self.subjectName} ({self.sessionName})")
        #     return None
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
