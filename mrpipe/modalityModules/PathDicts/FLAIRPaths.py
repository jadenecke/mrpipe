import os.path
from mrpipe.modalityModules.PathDicts.BasePaths import PathBase
from mrpipe.meta.PathClass import Path
from mrpipe.meta.PathCollection import PathCollection
from mrpipe.Toolboxes.standalone.SynthSeg import SynthSeg

class PathDictFLAIR(PathCollection):

    class Bids(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename, WMHMask):
            super().__init__(name="T1w_bids")
            self.basename = Path(os.path.join(basepaths.bidsPath, filler,
                                        nameFormatter.format(subj=sub, ses=ses, basename=basename)))
            self.flair = Path(self.basename + ".nii.gz", shouldExist=True)
            self.WMHMask = Path(WMHMask, shouldExist=True)
            self.json = Path(self.basename + ".json", shouldExist=True)

    class Bids_processed(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="T1w_bidsProcessed")
            self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
            self.flair = Path(self.basename + ".nii.gz")
            self.json = Path(self.basename + ".json")


            self.synthseg = self.SynthSeg(basedir=self.basedir,  sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)
            self.iso1mm = self.Iso1mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)
            self.iso1p5mm = self.Iso2mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)
            self.iso2mm = self.Iso2mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)
            self.iso3mm = self.Iso2mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)

        class Iso1mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                basename = basename + "_iso1mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler + "resample_iso1mm"), isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
                self.baseimage = self.basename + ".nii.gz"

        class Iso1p5mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                basename = basename + "_iso1p5mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler + "resample_iso1p5mm"),
                                    isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
                self.baseimage = self.basename + ".nii.gz"

        class Iso2mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                basename = basename + "_iso2mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler + "resample_iso2mm"),
                                    isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
                self.baseimage = self.basename + ".nii.gz"

        class Iso3mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                basename = basename + "_iso3mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler + "resample_iso3mm"),
                                    isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
                self.baseimage = self.basename + ".nii.gz"

    class Meta_QC(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            self.basedir = Path(os.path.join(basepaths.qcPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename), isDirectory=False)
            self.ToT1w_1mm_slices = self.basename + "nativeToT1w_1mm.png"
            self.ToT1w_1p5mm_slices = self.basename + "nativeToT1w_1p5mm.png"
            self.ToT1w_2mm_slices = self.basename + "nativeToT1w_2mm.png"
            self.ToT1w_3mm_slices = self.basename + "nativeToT1w_3mm.png"

    class Bids_statistics(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            self.basedir = Path(os.path.join(basepaths.bidsStatisticsPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))

    def __init__(self, sub, ses, basepaths, WMHMask, basedir="FLAIR", nameFormatter="{subj}_{ses}_{basename}",
                 modalityBeforeSession=False, basename="FLAIR"):
        super().__init__(name="FLAIR")
        if modalityBeforeSession:
            filler = os.path.join(sub, basedir, ses)
        else:
            filler = os.path.join(sub, ses, basedir)

        self.bids = self.Bids(filler, basepaths, sub, ses, nameFormatter, basename, WMHMask)
        self.bids_processed = self.Bids_processed(filler, basepaths, sub, ses, nameFormatter, basename)
        self.bids_statistics = self.Bids_statistics(filler, basepaths, sub, ses, nameFormatter, basename)
        self.meta_QC = self.Meta_QC(filler, basepaths, sub, ses, nameFormatter, basename)

