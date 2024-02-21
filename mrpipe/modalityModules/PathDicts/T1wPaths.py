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
            self.basename = Path(os.path.join(basepaths.bidsProcessedPath, filler,
                                              nameFormatter.format(subj=sub, ses=ses, basename=basename)))
            self.T1w = Path(self.basename + ".nii.gz")
            self.json = Path(self.basename + ".json")
            self.N4BiasCorrected = Path([self.basename + "_N4.nii.gz"])

    def __init__(self, sub, ses, basepaths, basedir="T1w", nameFormatter="{subj}_{ses}_{basename}",
                 modalityBeforeSession=False, basename="T1w"):
        super().__init__(name="T1w")
        if modalityBeforeSession:
            filler = os.path.join(sub, basedir, ses)
        else:
            filler = os.path.join(sub, ses, basedir)

        self.bids = self.Bids(filler, basepaths, sub, ses, nameFormatter, basename)
        self.bids_processed = self.Bids_processed(filler, basepaths, sub, ses, nameFormatter, basename)


