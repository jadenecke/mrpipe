import os.path
from mrpipe.modalityModules.PathDicts.BasePaths import PathBase
from mrpipe.meta.PathClass import Path
from mrpipe.meta.PathCollection import PathCollection

class PathDictT1w(PathCollection):

    class Bids(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="T1w_bids")
            self.basename = Path(os.path.join(basepaths.bidsPath, filler,
                                        nameFormatter.format(subj=sub, ses=ses, basename=basename)))
            self.T1w = Path(self.basename + ".nii.gz")
            self.json = Path(self.basename + ".json")

    class Bids_processed(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="T1w_bidsProcessed")
            self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
            self.T1w = Path(self.basename + ".nii.gz")
            self.json = Path(self.basename + ".json")
            self.N4BiasCorrected = self.basename + "_N4.nii.gz"
            self.hdbet_brain = self.basename + "_brain.nii.gz"
            self.hdbet_mask = self.basename + "_brain_mask.nii.gz" #can not be changed because it is not allowed to specify the mask name in hd-bet. However it always will be hdbet-output name with _mask attached.
            self.synthsegDir = self.basedir.join("SynthSeg", isDirectory=True)
            self.synthsegBasename = self.synthsegDir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename), isDirectory=False)
            self.synthsegPosterior = self.synthsegBasename + "_posterior.nii.gz"
            self.synthsegPosteriorProbabilities = self.synthsegBasename + "_posteriorProbabilities.nii.gz"
            self.synthsegResample = self.synthsegBasename + "_resampled.nii.gz"

    class Meta_QC(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            self.basedir = Path(os.path.join(basepaths.qcPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename), isDirectory=False)
            self.synthsegQC = self.basename + "_SynthSegQC_Scores.csv"
            self.hdbet_slices = self.basename + "_hdbet_slices.png"
            self.synthseg_slices = self.basename + "_hdbet_synthseg.png"

    class Bids_statistics(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            self.basedir = Path(os.path.join(basepaths.bidsStatisticsPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
            self.synthsegVolumes = self.basename + "_SynthSeg_Volumes.csv"


    def __init__(self, sub, ses, basepaths, basedir="T1w", nameFormatter="{subj}_{ses}_{basename}",
                 modalityBeforeSession=False, basename="T1w"):
        super().__init__(name="T1w")
        if modalityBeforeSession:
            filler = os.path.join(sub, basedir, ses)
        else:
            filler = os.path.join(sub, ses, basedir)

        self.bids = self.Bids(filler, basepaths, sub, ses, nameFormatter, basename)
        self.bids_processed = self.Bids_processed(filler, basepaths, sub, ses, nameFormatter, basename)
        self.bids_statistics = self.Bids_statistics(filler, basepaths, sub, ses, nameFormatter, basename)
        self.meta_QC = self.Meta_QC(filler, basepaths, sub, ses, nameFormatter, basename)

