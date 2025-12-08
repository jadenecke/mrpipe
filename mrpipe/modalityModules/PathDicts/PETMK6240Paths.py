import os.path
from mrpipe.modalityModules.PathDicts.BasePaths import PathBase
from mrpipe.meta.PathClass import Path
from mrpipe.meta.PathClass import StatsFilePath
from mrpipe.meta.PathCollection import PathCollection
from mrpipe.meta.ImageWithSideCar import ImageWithSideCar


class PathDictPETMK6240(PathCollection):

    class Bids(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="PETMK6240_bids")
            self.basedir = Path(os.path.join(basepaths.bidsPath, filler), isDirectory=True)
            PETMK6240File, PETMK6240Pattern, PETMK6240_NegativePattern = Path.Identify("PET-MK6240 Image", pattern=r"[^\._]+_[^_]+_(.*)\.nii.*",
                                                                            searchDir=self.basedir,
                                                                            previousPatterns=[nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".nii*" for pattern in PathDictPETMK6240.getFilePatterns("PETMK6240Pattern")],
                                                                            negativePattern=[nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".nii*" for pattern in PathDictPETMK6240.getFilePatterns("PETMK6240_NegativePattern")])
            if PETMK6240Pattern is not None:
                PathDictPETMK6240.setFilePatterns("PETMK6240Pattern", PETMK6240Pattern)
            if PETMK6240_NegativePattern is not None:
                PathDictPETMK6240.setFilePatterns("PETMK6240_NegativePattern", PETMK6240_NegativePattern)

            jsonFile, JsonPattern, Json_NegativePattern = Path.Identify("PET-MK6240 json", pattern=r"[^\._]+_[^_]+_(.*)\.json",
                                                                         searchDir=self.basedir,
                                                                         previousPatterns=[nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".json*" for pattern in PathDictPETMK6240.getFilePatterns("PETMK6240_JsonPattern")],
                                                                         negativePattern=[nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".json*" for pattern in PathDictPETMK6240.getFilePatterns("PETMK6240_Json_NegativePattern")])
            if JsonPattern is not None:
                PathDictPETMK6240.setFilePatterns("PETMK6240_JsonPattern", JsonPattern)
            if Json_NegativePattern is not None:
                PathDictPETMK6240.setFilePatterns("PETMK6240_Json_NegativePattern", Json_NegativePattern)

            self.PETMK6240 = ImageWithSideCar(imagePath=PETMK6240File, jsonPath=jsonFile)

    class Bids_processed(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="PETMK6240_bidsProcessed")
            self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
            self.PETMK6240_recentered = Path(self.basename + "_recentered.nii.gz")
            self.json = Path(self.basename + ".json")


            # To T1w
            self.toT1w_prefix = self.basename + "_toT1w"
            self.toT1w_toT1w = (self.toT1w_prefix + "Warped.nii.gz").setStatic()
            self.toT1w_0GenericAffine = (self.toT1w_prefix + "0GenericAffine.mat").setStatic()
            self.toT1w_InverseWarped = (self.toT1w_prefix + "InverseWarped.nii.gz").setStatic().setCleanup()

            # from T1w
            self.refMask_inT1w = self.basename + "_INFCER_mask_inT1w.nii.gz"
            self.refMask = self.basename + "_INFCER_mask.nii.gz"
            self.atlas_schaefer200_17Net = self.basename + "_schafer200_17Net.nii.gz"
            self.atlas_mindboggle = self.basename + "_mindboggle101.nii.gz"


            # SUVR calculations
            self.reMaskVal = self.basename + "_INFCER_meanValue.txt"
            self.SUVR = Path(self.basename + "_INFCER_SUVR.nii.gz")

            # CenTaurRZ scale
            self.centaur_dir = self.basedir.join("CenTauRz")
            self.centaur_base = self.centaur_dir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
            self.centaur_maskNative_CenTauR = self.centaur_base + "_centaur_maskNative_CenTauR.nii.gz"
            self.centaur_maskNative_Frontal_CenTauR = self.centaur_base + "_centaur_maskNative_Frontal_CenTauR.nii.gz"
            self.centaur_maskNative_Mesial_CenTauR = self.centaur_base + "_centaur_maskNative_Mesial_CenTauR.nii.gz"
            self.centaur_maskNative_Meta_CenTauR = self.centaur_base + "_centaur_maskNative_Meta_CenTauR.nii.gz"
            self.centaur_maskNative_TP_CenTauR = self.centaur_base + "_centaur_maskNative_TP_CenTauR.nii.gz"

            self.centaur_maskNative_CenTauR_inT1w = self.centaur_base + "_centaur_maskNative_CenTauR_inT1w.nii.gz"
            self.centaur_maskNative_Frontal_CenTauR_inT1w = self.centaur_base + "_centaur_maskNative_Frontal_CenTauR_inT1w.nii.gz"
            self.centaur_maskNative_Mesial_CenTauR_inT1w = self.centaur_base + "_centaur_maskNative_Mesial_CenTauR_inT1w.nii.gz"
            self.centaur_maskNative_Meta_CenTauR_inT1w = self.centaur_base + "_centaur_maskNative_Meta_CenTauR_inT1w.nii.gz"
            self.centaur_maskNative_TP_CenTauR_inT1w = self.centaur_base + "_centaur_maskNative_TP_CenTauR_inT1w.nii.gz"

            # Smoothing
            self.SUVR_smoothed4mmFWHM = Path(self.basename + "_INFCER_SUVR_smoothed4mmFWHM.nii.gz")
            self.SUVR_smoothed6mmFWHM = Path(self.basename + "_INFCER_SUVR_smoothed6mmFWHM.nii.gz")
            self.SUVR_smoothed8mmFWHM = Path(self.basename + "_INFCER_SUVR_smoothed8mmFWHM.nii.gz")

            self.iso1p5mm = self.Iso1p5mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)
            self.iso2mm = self.Iso2mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)
            self.iso3mm = self.Iso3mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)

        class Iso1p5mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                basename = basename + "_iso1p5mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler, "resample_iso1p5mm"),
                                    isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))

                # To T1w
                self.baseimage = self.basename + "_INFCER_SUVR_toT1w.nii.gz"
                self.SUVR_smoothed4mmFWHM_toT1w = Path(self.basename + "_INFCER_SUVR_smoothed4mmFWHM_toT1w.nii.gz")
                self.SUVR_smoothed6mmFWHM_toT1w = Path(self.basename + "_INFCER_SUVR_smoothed6mmFWHM_toT1w.nii.gz")
                self.SUVR_smoothed8mmFWHM_toT1w = Path(self.basename + "_INFCER_SUVR_smoothed8mmFWHM_toT1w.nii.gz")

                # ToMNI
                self.toMNI = self.basename + "_INFCER_SUVR_toMNI.nii.gz"
                self.SUVR_smoothed4mmFWHM_toMNI = Path(self.basename + "_INFCER_SUVR_smoothed4mmFWHM_toMNI.nii.gz")
                self.SUVR_smoothed6mmFWHM_toMNI = Path(self.basename + "_INFCER_SUVR_smoothed6mmFWHM_toMNI.nii.gz")
                self.SUVR_smoothed8mmFWHM_toMNI = Path(self.basename + "_INFCER_SUVR_smoothed8mmFWHM_toMNI.nii.gz")

        class Iso2mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                basename = basename + "_iso2mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler, "resample_iso2mm"),
                                    isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))

                # To T1w
                self.baseimage = self.basename + "_INFCER_SUVR_toT1w.nii.gz"
                self.SUVR_smoothed4mmFWHM_toT1w = Path(self.basename + "_INFCER_SUVR_smoothed4mmFWHM_toT1w.nii.gz")
                self.SUVR_smoothed6mmFWHM_toT1w = Path(self.basename + "_INFCER_SUVR_smoothed6mmFWHM_toT1w.nii.gz")
                self.SUVR_smoothed8mmFWHM_toT1w = Path(self.basename + "_INFCER_SUVR_smoothed8mmFWHM_toT1w.nii.gz")

                # ToMNI
                self.toMNI = self.basename + "_INFCER_SUVR_toMNI.nii.gz"
                self.SUVR_smoothed4mmFWHM_toMNI = Path(self.basename + "_INFCER_SUVR_smoothed4mmFWHM_toMNI.nii.gz")
                self.SUVR_smoothed6mmFWHM_toMNI = Path(self.basename + "_INFCER_SUVR_smoothed6mmFWHM_toMNI.nii.gz")
                self.SUVR_smoothed8mmFWHM_toMNI = Path(self.basename + "_INFCER_SUVR_smoothed8mmFWHM_toMNI.nii.gz")


        class Iso3mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                basename = basename + "_iso3mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler, "resample_iso3mm"),
                                    isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))

                # To T1w
                self.baseimage = self.basename + "_INFCER_SUVR_toT1w.nii.gz"
                self.SUVR_smoothed4mmFWHM_toT1w = Path(self.basename + "_INFCER_SUVR_smoothed4mmFWHM_toT1w.nii.gz")
                self.SUVR_smoothed6mmFWHM_toT1w = Path(self.basename + "_INFCER_SUVR_smoothed6mmFWHM_toT1w.nii.gz")
                self.SUVR_smoothed8mmFWHM_toT1w = Path(self.basename + "_INFCER_SUVR_smoothed8mmFWHM_toT1w.nii.gz")

                # ToMNI
                self.toMNI = self.basename + "_INFCER_SUVR_toMNI.nii.gz"
                self.SUVR_smoothed4mmFWHM_toMNI = Path(self.basename + "_INFCER_SUVR_smoothed4mmFWHM_toMNI.nii.gz")
                self.SUVR_smoothed6mmFWHM_toMNI = Path(self.basename + "_INFCER_SUVR_smoothed6mmFWHM_toMNI.nii.gz")
                self.SUVR_smoothed8mmFWHM_toMNI = Path(self.basename + "_INFCER_SUVR_smoothed8mmFWHM_toMNI.nii.gz")

    class Meta_QC(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            self.basedir = Path(os.path.join(basepaths.qcPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename), isDirectory=False)
            self.ToT1w_native_slices = self.basename + "_PETMK6240ToT1w_native.png"

    class Bids_statistics(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            self.basedir = Path(os.path.join(basepaths.bidsStatisticsPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))

            centaur_native_fileName = self.basename + "_centaur_stats_native.json"
            self.centaur_native_SUVR_CenTauR = StatsFilePath(centaur_native_fileName, attributeName="centaur_maskNative_SUVR_CenTauR")
            self.centaur_native_SUVR_Frontal_CenTauR = StatsFilePath(centaur_native_fileName, attributeName="centaur_maskNative_SUVR_Frontal_CenTauR")
            self.centaur_native_SUVR_Mesial_CenTauR = StatsFilePath(centaur_native_fileName, attributeName="centaur_maskNative_SUVR_Mesial_CenTauR")
            self.centaur_native_SUVR_Meta_CenTauR = StatsFilePath(centaur_native_fileName, attributeName="centaur_maskNative_SUVR_Meta_CenTauR")
            self.centaur_native_SUVR_TP_CenTauR = StatsFilePath(centaur_native_fileName, attributeName="centaur_maskNative_SUVR_TP_CenTauR")

            self.centaur_native_CTRz_CenTauR = StatsFilePath(centaur_native_fileName, attributeName="centaur_maskNative_CTRz_CenTauR")
            self.centaur_native_CTRz_Frontal_CenTauR = StatsFilePath(centaur_native_fileName, attributeName="centaur_maskNative_CTRz_Frontal_CenTauR")
            self.centaur_native_CTRz_Mesial_CenTauR = StatsFilePath(centaur_native_fileName, attributeName="centaur_maskNative_CTRz_Mesial_CenTauR")
            self.centaur_native_CTRz_Meta_CenTauR = StatsFilePath(centaur_native_fileName, attributeName="centaur_maskNative_CTRz_Meta_CenTauR")
            self.centaur_native_CTRz_TP_CenTauR = StatsFilePath(centaur_native_fileName, attributeName="centaur_maskNative_CTRz_TP_CenTauR")

            self.SUVR_INFCER_Mindboggle101_mean = self.basename + "_SUVR_INFCER_Mindboggle101_mean.csv"
            self.SUVR_INFCER_Schaefer200_17Net_mean = self.basename + "_SUVR_INFCER_Schaefer200_17Net_mean.csv"


    def __init__(self, sub, ses, basepaths, basedir="pet-MK6240", nameFormatter="{subj}_{ses}_{basename}",
                 modalityBeforeSession=False, basename="pet-MK6240"):
        super().__init__(name="PETMK6240")
        if modalityBeforeSession:
            fillerBids = os.path.join(sub, basedir, ses)
            filler = os.path.join(sub, basename, ses)
        else:
            fillerBids = os.path.join(sub, ses, basedir)
            filler = os.path.join(sub, ses, basename)

        self.bids = self.Bids(fillerBids, basepaths, sub, ses, nameFormatter, basename)
        self.bids_processed = self.Bids_processed(filler, basepaths, sub, ses, nameFormatter, basename)
        self.bids_statistics = self.Bids_statistics(filler, basepaths, sub, ses, nameFormatter, basename)
        self.meta_QC = self.Meta_QC(filler, basepaths, sub, ses, nameFormatter, basename)

