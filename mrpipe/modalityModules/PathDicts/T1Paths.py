import os.path
from types import SimpleNamespace

from mrpipe.meta import PathClass


def createPathDictT1(subj, ses, basepaths, basedir="T1w", nameFormatter="{subj}_{ses}_{basename}", modalityBeforeSession=False, basename="T1w"):
    if modalityBeforeSession:
        filler = os.path.join(subj, basedir, ses)
    else:
        filler = os.path.join(subj, ses, basedir)
    baseT1wName_bids = os.path.join(basepaths.bidsPath, filler, nameFormatter.format(subj=subj, ses=ses, basename=basename))
    baseT1wName_bidsProcessd = os.path.join(basepaths.bidsProcessedPath, filler, nameFormatter.format(subj=subj, ses=ses, basename=basename))

    pathDictT1_bids = {"basename": PathClass.Path(baseT1wName_bids),
                       "T1w": PathClass.Path(baseT1wName_bids + ".nii.gz")}

    pathDictT1_bidsProcessed = {"basename": PathClass.Path(baseT1wName_bidsProcessd),
                                "T1w": PathClass.Path(baseT1wName_bidsProcessd + ".nii.gz")}
    pathDictT1_bidsProcessed["N4BiasCorrected"] = PathClass.Path([baseT1wName_bidsProcessd + "_N4.nii.gz"])

    pathDictT1 = {"bids": SimpleNamespace(**pathDictT1_bids),
                  "bids_processed": SimpleNamespace(**pathDictT1_bidsProcessed)}
    n = SimpleNamespace(**pathDictT1)  # make dot notation available for dictionaries
    return n
