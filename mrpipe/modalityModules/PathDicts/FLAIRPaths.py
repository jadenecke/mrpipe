import os.path
from mrpipe.modalityModules.PathDicts.BasePaths import PathBase
from mrpipe.meta.PathClass import Path
from mrpipe.meta.PathCollection import PathCollection
from mrpipe.Toolboxes.standalone.SynthSeg import SynthSeg

class PathDictFLAIR(PathCollection):

    class Bids(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="T1w_bids")
            self.basedir = Path(os.path.join(basepaths.bidsPath, filler), isDirectory=True)
            self.basename = Path(os.path.join(basepaths.bidsPath, filler,
                                        nameFormatter.format(subj=sub, ses=ses, basename=basename)))
            self.flair, FLAIRPattern = Path.Identify("FLAIR Image", pattern=r"[^\._]+_[^_]+_(.*)\.nii.*",
                                                      searchDir=self.basedir, previousPatterns=[nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".nii*" for pattern in PathDictFLAIR.getFilePatterns("FLAIRPattern")])
            if FLAIRPattern is not None:
                PathDictFLAIR.setFilePatterns("FLAIRPattern", FLAIRPattern)
            self.WMHMask, WMHMaskPattern = Path.Identify("WMH Mask Image", pattern=r"[^\._]+_[^_]+_(.*)\.nii.*",
                                                     searchDir=self.basedir, previousPatterns=[nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".nii*" for pattern in PathDictFLAIR.getFilePatterns("WMHMaskPattern")])
            if WMHMaskPattern is not None:
                PathDictFLAIR.setFilePatterns("WMHMaskPattern", WMHMaskPattern)
            self.json, JsonPattern = Path.Identify("FLAIR json", pattern=r"[^\._]+_[^_]+_(.*)\.json",
                                                      searchDir=self.basedir, previousPatterns=[nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".nii*" for pattern in PathDictFLAIR.getFilePatterns("JsonPattern")])
            if JsonPattern is not None:
                PathDictFLAIR.setFilePatterns("JsonPattern", JsonPattern)

    class Bids_processed(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="T1w_bidsProcessed")
            self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
            self.flair = Path(self.basename + ".nii.gz")
            self.WMHMask = Path(self.basename + "_WMH.nii.gz")
            self.N4BiasCorrected = Path(self.basename + "_N4.nii.gz", isDirectory=False)
            self.json = Path(self.basename + ".json")
            #To T1w
            self.toT1w_prefix = self.basename + "_toT1w"
            self.toT1w_toT1w = (self.toT1w_prefix + "Warped.nii.gz").setStatic()
            self.toT1w_0GenericAffine = (self.toT1w_prefix + "0GenericAffine.mat").setStatic()
            self.toT1w_InverseWarped = (self.toT1w_prefix + "InverseWarped.nii.gz").setStatic().setCleanup()
            self.WMHMask_toT1w = Path(self.basename + "_WMH_toT1w.nii.gz")

            self.iso1mm = self.Iso1mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)
            self.iso1p5mm = self.Iso1p5mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)
            self.iso2mm = self.Iso2mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)
            self.iso3mm = self.Iso3mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)

        class Iso1mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                basename = basename + "_iso1mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler, "resample_iso1mm"), isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
                # To T1w
                self.baseimage = self.basename + "_toT1w.nii.gz"
                self.WMHMask_toT1 = self.basename + "_WMH_toT1w.nii.gz"
                #ToMNI
                self.toMNI = self.basename + "_toMNI.nii.gz"
                self.WMHMask_toMNI = self.basename + "_WMH_toMNI.nii.gz"

        class Iso1p5mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                basename = basename + "_iso1p5mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler, "resample_iso1p5mm"),
                                    isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
                # To T1w
                self.baseimage = self.basename + "_toT1w.nii.gz"
                self.WMHMask_toT1 = self.basename + "_WMH_toT1w.nii.gz"
                # ToMNI
                self.toMNI = self.basename + "_toMNI.nii.gz"
                self.WMHMask_toMNI = self.basename + "_WMH_toMNI.nii.gz"
        class Iso2mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                basename = basename + "_iso2mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler, "resample_iso2mm"),
                                    isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
                # To T1w
                self.baseimage = self.basename + "_toT1w.nii.gz"
                self.WMHMask_toT1 = self.basename + "_WMH_toT1w.nii.gz"
                # ToMNI
                self.toMNI = self.basename + "_toMNI.nii.gz"
                self.WMHMask_toMNI = self.basename + "_WMH_toMNI.nii.gz"

        class Iso3mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                basename = basename + "_iso3mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler, "resample_iso3mm"),
                                    isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
                # To T1w
                self.baseimage = self.basename + "_toT1w.nii.gz"
                self.WMHMask_toT1 = self.basename + "_WMH_toT1w.nii.gz"
                # ToMNI
                self.toMNI = self.basename + "_toMNI.nii.gz"
                self.WMHMask_toMNI = self.basename + "_WMH_toMNI.nii.gz"

    class Meta_QC(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            self.basedir = Path(os.path.join(basepaths.qcPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename), isDirectory=False)
            self.ToT1w_native_slices = self.basename + "flairToT1w_native.png"
            self.ToT1w_1mm_slices = self.basename + "flairToT1w_1mm.png"
            self.ToT1w_1p5mm_slices = self.basename + "flairToT1w_1p5mm.png"
            self.ToT1w_2mm_slices = self.basename + "flairToT1w_2mm.png"
            self.ToT1w_3mm_slices = self.basename + "flairToT1w_3mm.png"

    class Bids_statistics(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            self.basedir = Path(os.path.join(basepaths.bidsStatisticsPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))

    def __init__(self, sub, ses, basepaths, basedir="FLAIR", nameFormatter="{subj}_{ses}_{basename}",
                 modalityBeforeSession=False, basename="FLAIR"):
        super().__init__(name="FLAIR")
        if modalityBeforeSession:
            filler = os.path.join(sub, basedir, ses)
        else:
            filler = os.path.join(sub, ses, basedir)

        self.bids = self.Bids(filler, basepaths, sub, ses, nameFormatter, basename)
        self.bids_processed = self.Bids_processed(filler, basepaths, sub, ses, nameFormatter, basename)
        self.bids_statistics = self.Bids_statistics(filler, basepaths, sub, ses, nameFormatter, basename)
        self.meta_QC = self.Meta_QC(filler, basepaths, sub, ses, nameFormatter, basename)

