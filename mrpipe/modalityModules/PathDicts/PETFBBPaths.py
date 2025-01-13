import os.path
from mrpipe.modalityModules.PathDicts.BasePaths import PathBase
from mrpipe.meta.PathClass import Path
from mrpipe.meta.PathClass import StatsFilePath
from mrpipe.meta.PathCollection import PathCollection



class PathDictPETFBB(PathCollection):

    class Bids(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="PETFBB_bids")
            self.basedir = Path(os.path.join(basepaths.bidsPath, filler), isDirectory=True)
            self.PETFBB, PETFBBPattern, PETFBB_NegativePattern = Path.Identify("PET-FBB Image", pattern=r"[^\._]+_[^_]+_(.*)\.nii.*",
                                                                            searchDir=self.basedir,
                                                                            previousPatterns=[nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".nii*" for pattern in PathDictPETFBB.getFilePatterns("PETFBBPattern")],
                                                                            negativePattern=[nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".nii*" for pattern in PathDictPETFBB.getFilePatterns("PETFBB_NegativePattern")])
            if PETFBBPattern is not None:
                PathDictPETFBB.setFilePatterns("PETFBBPattern", PETFBBPattern)
            if PETFBB_NegativePattern is not None:
                PathDictPETFBB.setFilePatterns("PETFBB_NegativePattern", PETFBB_NegativePattern)

            self.json, JsonPattern, Json_NegativePattern = Path.Identify("PET-FBB json", pattern=r"[^\._]+_[^_]+_(.*)\.json",
                                                                         searchDir=self.basedir,
                                                                         previousPatterns=[nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".nii*" for pattern in PathDictPETFBB.getFilePatterns("JsonPattern")],
                                                                         negativePattern=[nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".nii*" for pattern in PathDictPETFBB.getFilePatterns("Json_NegativePattern")])
            if JsonPattern is not None:
                PathDictPETFBB.setFilePatterns("JsonPattern", JsonPattern)
            if Json_NegativePattern is not None:
                PathDictPETFBB.setFilePatterns("Json_NegativePattern", Json_NegativePattern)

    class Bids_processed(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="PETFBB_bidsProcessed")
            self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
            self.PETFBB_recentered = Path(self.basename + "_recentered.nii.gz")
            self.json = Path(self.basename + ".json")


            # To T1w
            self.toT1w_prefix = self.basename + "_toT1w"
            self.toT1w_toT1w = (self.toT1w_prefix + "Warped.nii.gz").setStatic()
            self.toT1w_0GenericAffine = (self.toT1w_prefix + "0GenericAffine.mat").setStatic()
            self.toT1w_InverseWarped = (self.toT1w_prefix + "InverseWarped.nii.gz").setStatic().setCleanup()

            # from T1w
            self.refMask = self.basename + "_WHOLECER_mask.nii.gz"
            self.atlas_schaefer200_17Net = self.basename + "_schafer200_17Net.nii.gz"
            self.atlas_mindboggle = self.basename + "_schafer200_17Net.nii.gz"


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
            self.ToT1w_native_slices = self.basename + "_PETFBBToT1w_native.png"

    class Bids_statistics(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            self.basedir = Path(os.path.join(basepaths.bidsStatisticsPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))

            self.SUVR_WHOLECER_Mindboggle101_mean = self.basename.join("_SUVR_WHOLECER_Mindboggle101_mean.csv")
            self.SUVR_WHOLECER_Schaefer200_17Net_mean = self.basename.join("_SUVR_WHOLECER_Schaefer200_17Net_mean.csv")


    def __init__(self, sub, ses, basepaths, basedir="pet-FBB", nameFormatter="{subj}_{ses}_{basename}",
                 modalityBeforeSession=False, basename="pet-FBB"):
        super().__init__(name="PETFBB")
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
