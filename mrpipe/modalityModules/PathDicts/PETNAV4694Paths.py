import os.path
from mrpipe.modalityModules.PathDicts.BasePaths import PathBase
from mrpipe.meta.PathClass import Path
from mrpipe.meta.PathClass import StatsFilePath
from mrpipe.meta.PathCollection import PathCollection
from mrpipe.meta.ImageWithSideCar import ImageWithSideCar


class PathDictPETNAV4694(PathCollection):

    class Bids(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="PETNAV4694_bids")
            self.basedir = Path(os.path.join(basepaths.bidsPath, filler), isDirectory=True)
            PETNAV4694File, PETNAV4694Pattern, PETNAV4694_NegativePattern = Path.Identify("PET-NAV4694 Image", pattern=r"[^\._]+_[^_]+_(.*)\.nii.*",
                                                                            searchDir=self.basedir,
                                                                            previousPatterns=[nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".nii*" for pattern in PathDictPETNAV4694.getFilePatterns("PETNAV4694Pattern")],
                                                                            negativePattern=[nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".nii*" for pattern in PathDictPETNAV4694.getFilePatterns("PETNAV4694_NegativePattern")])
            if PETNAV4694Pattern is not None:
                PathDictPETNAV4694.setFilePatterns("PETNAV4694Pattern", PETNAV4694Pattern)
            if PETNAV4694_NegativePattern is not None:
                PathDictPETNAV4694.setFilePatterns("PETNAV4694_NegativePattern", PETNAV4694_NegativePattern)

            jsonFile, JsonPattern, Json_NegativePattern = Path.Identify("PET-NAV4694 json", pattern=r"[^\._]+_[^_]+_(.*)\.json",
                                                                         searchDir=self.basedir,
                                                                         previousPatterns=[nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".json*" for pattern in PathDictPETNAV4694.getFilePatterns("PETNAV4694_JsonPattern")],
                                                                         negativePattern=[nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".json*" for pattern in PathDictPETNAV4694.getFilePatterns("PETNAV4694_Json_NegativePattern")])
            if JsonPattern is not None:
                PathDictPETNAV4694.setFilePatterns("PETNAV4694_JsonPattern", JsonPattern)
            if Json_NegativePattern is not None:
                PathDictPETNAV4694.setFilePatterns("PETNAV4694_Json_NegativePattern", Json_NegativePattern)

            self.PETNAV4694 = ImageWithSideCar(imagePath=PETNAV4694File, jsonPath=jsonFile)

    class Bids_processed(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="PETNAV4694_bidsProcessed")
            self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
            self.PETNAV4694_recentered = Path(self.basename + "_recentered.nii.gz")
            self.json = Path(self.basename + ".json")


            # To T1w
            self.toT1w_prefix = self.basename + "_toT1w"
            self.toT1w_toT1w = (self.toT1w_prefix + "Warped.nii.gz").setStatic()
            self.toT1w_0GenericAffine = (self.toT1w_prefix + "0GenericAffine.mat").setStatic()
            self.toT1w_InverseWarped = (self.toT1w_prefix + "InverseWarped.nii.gz").setStatic().setCleanup()

            # from T1w
            self.refMask_inT1w = self.basename + "_WHOLECER_mask_inT1w.nii.gz"
            self.refMask = self.basename + "_WHOLECER_mask.nii.gz"
            self.atlas_schaefer200_17Net = self.basename + "_schafer200_17Net.nii.gz"
            self.atlas_mindboggle = self.basename + "_mindboggle101.nii.gz"


            # SUVR calculations
            self.reMaskVal = self.basename + "_WHOLECER_meanValue.txt"
            self.SUVR = Path(self.basename + "_WHOLECER_SUVR.nii.gz")

            # Smoothing
            self.SUVR_smoothed4mmFWHM = Path(self.basename + "_WHOLECER_SUVR_smoothed4mmFWHM.nii.gz")
            self.SUVR_smoothed6mmFWHM = Path(self.basename + "_WHOLECER_SUVR_smoothed6mmFWHM.nii.gz")
            self.SUVR_smoothed8mmFWHM = Path(self.basename + "_WHOLECER_SUVR_smoothed8mmFWHM.nii.gz")

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
                self.baseimage = self.basename + "_WHOLECER_SUVR_toT1w.nii.gz"
                self.SUVR_smoothed4mmFWHM_toT1w = Path(self.basename + "_WHOLECER_SUVR_smoothed4mmFWHM_toT1w.nii.gz")
                self.SUVR_smoothed6mmFWHM_toT1w = Path(self.basename + "_WHOLECER_SUVR_smoothed6mmFWHM_toT1w.nii.gz")
                self.SUVR_smoothed8mmFWHM_toT1w = Path(self.basename + "_WHOLECER_SUVR_smoothed8mmFWHM_toT1w.nii.gz")

                # ToMNI
                self.toMNI = self.basename + "_WHOLECER_SUVR_toMNI.nii.gz"
                self.SUVR_smoothed4mmFWHM_toMNI = Path(self.basename + "_WHOLECER_SUVR_smoothed4mmFWHM_toMNI.nii.gz")
                self.SUVR_smoothed6mmFWHM_toMNI = Path(self.basename + "_WHOLECER_SUVR_smoothed6mmFWHM_toMNI.nii.gz")
                self.SUVR_smoothed8mmFWHM_toMNI = Path(self.basename + "_WHOLECER_SUVR_smoothed8mmFWHM_toMNI.nii.gz")

        class Iso2mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                basename = basename + "_iso2mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler, "resample_iso2mm"),
                                    isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))

                # To T1w
                self.baseimage = self.basename + "_WHOLECER_SUVR_toT1w.nii.gz"
                self.SUVR_smoothed4mmFWHM_toT1w = Path(self.basename + "_WHOLECER_SUVR_smoothed4mmFWHM_toT1w.nii.gz")
                self.SUVR_smoothed6mmFWHM_toT1w = Path(self.basename + "_WHOLECER_SUVR_smoothed6mmFWHM_toT1w.nii.gz")
                self.SUVR_smoothed8mmFWHM_toT1w = Path(self.basename + "_WHOLECER_SUVR_smoothed8mmFWHM_toT1w.nii.gz")

                # ToMNI
                self.toMNI = self.basename + "_WHOLECER_SUVR_toMNI.nii.gz"
                self.SUVR_smoothed4mmFWHM_toMNI = Path(self.basename + "_WHOLECER_SUVR_smoothed4mmFWHM_toMNI.nii.gz")
                self.SUVR_smoothed6mmFWHM_toMNI = Path(self.basename + "_WHOLECER_SUVR_smoothed6mmFWHM_toMNI.nii.gz")
                self.SUVR_smoothed8mmFWHM_toMNI = Path(self.basename + "_WHOLECER_SUVR_smoothed8mmFWHM_toMNI.nii.gz")


        class Iso3mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                basename = basename + "_iso3mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler, "resample_iso3mm"),
                                    isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))

                # To T1w
                self.baseimage = self.basename + "_WHOLECER_SUVR_toT1w.nii.gz"
                self.SUVR_smoothed4mmFWHM_toT1w = Path(self.basename + "_WHOLECER_SUVR_smoothed4mmFWHM_toT1w.nii.gz")
                self.SUVR_smoothed6mmFWHM_toT1w = Path(self.basename + "_WHOLECER_SUVR_smoothed6mmFWHM_toT1w.nii.gz")
                self.SUVR_smoothed8mmFWHM_toT1w = Path(self.basename + "_WHOLECER_SUVR_smoothed8mmFWHM_toT1w.nii.gz")

                # ToMNI
                self.toMNI = self.basename + "_WHOLECER_SUVR_toMNI.nii.gz"
                self.SUVR_smoothed4mmFWHM_toMNI = Path(self.basename + "_WHOLECER_SUVR_smoothed4mmFWHM_toMNI.nii.gz")
                self.SUVR_smoothed6mmFWHM_toMNI = Path(self.basename + "_WHOLECER_SUVR_smoothed6mmFWHM_toMNI.nii.gz")
                self.SUVR_smoothed8mmFWHM_toMNI = Path(self.basename + "_WHOLECER_SUVR_smoothed8mmFWHM_toMNI.nii.gz")

    class Meta_QC(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            self.basedir = Path(os.path.join(basepaths.qcPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename), isDirectory=False)
            self.ToT1w_native_slices = self.basename + "_PETNAV4694ToT1w_native.png"
            self.refMask_native_slices = self.basename + "_PETNAV4694_refMask.png"

    class Bids_statistics(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            self.basedir = Path(os.path.join(basepaths.bidsStatisticsPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))

            self.SUVR_WHOLECER_Mindboggle101_mean = self.basename + "_SUVR_WHOLECER_Mindboggle101_mean.csv"
            self.SUVR_WHOLECER_Schaefer200_17Net_mean = self.basename + "_SUVR_WHOLECER_Schaefer200_17Net_mean.csv"

            self.Centiloid_WHOLECER_Mindboggle101_mean = self.basename + "_Centiloid_WHOLECER_Mindboggle101_mean.csv"
            self.Centiloid_WHOLECER_Schaefer200_17Net_mean = self.basename + "_Centiloid_WHOLECER_Schaefer200_17Net_mean.csv"

    def __init__(self, sub, ses, basepaths, basedir="pet-NAV4694", nameFormatter="{subj}_{ses}_{basename}",
                 modalityBeforeSession=False, basename="pet-NAV4694"):
        super().__init__(name="PETNAV4694")
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

