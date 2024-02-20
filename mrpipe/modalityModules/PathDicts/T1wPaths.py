import os.path
from types import SimpleNamespace
from mrpipe.modalityModules.PathDicts.BasePaths import PathBase
from mrpipe.meta.PathClass import Path
from mrpipe.meta.PathCollection import PathCollection

class PathDictT1w(PathCollection):

    class Bids(PathCollection):
        def __init__(self, filler, basepaths: PathBase, subj, ses, nameFormatter, basename):
            super.__init__(name="T1w_bids")
            self.basename = Path(os.path.join(basepaths.bidsPath, filler,
                                        nameFormatter.format(subj=subj, ses=ses, basename=basename)))
            self.T1w = Path(self.basename + ".nii.gz")
            self.json = Path(self.basename + ".json")



    class Bids_processed(PathCollection):
        def __init__(self, filler, basepaths: PathBase, subj, ses, nameFormatter, basename):
            super.__init__(name="T1w_bidsProcessed")
            self.basename = Path(os.path.join(basepaths.bidsProcessedPath, filler,
                                              nameFormatter.format(subj=subj, ses=ses, basename=basename)))
            self.T1w = Path(self.basename + ".nii.gz")
            self.json = Path(self.basename + ".json")
            self.N4BiasCorrected = Path([self.basename + "_N4.nii.gz"])

    def __init__(self, subj, ses, basepaths, basedir="T1w", nameFormatter="{subj}_{ses}_{basename}",
                 modalityBeforeSession=False, basename="T1w"):
        super.__init__(name="T1w")
        if modalityBeforeSession:
            filler = os.path.join(subj, basedir, ses)
        else:
            filler = os.path.join(subj, ses, basedir)

        self.bids = self.Bids(filler, basepaths, subj, ses, nameFormatter, basename)
        self.bids_processed = self.Bids_processed(filler, basepaths, subj, ses, nameFormatter, basename)


