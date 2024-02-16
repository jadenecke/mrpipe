import os
from mrpipe.meta import PathClass
from types import SimpleNamespace


def createPathDictBase(basePath: str, bidsDirName: str, scratch: str = None) -> dict:
    if not os.path.isdir(basePath):
        raise(OSError.filename(basePath))
    if not os.path.isdir(os.path.join(basePath, bidsDirName)):
        raise(OSError.filename(bidsDirName))

    if not scratch:
        scratch = os.path.join(basePath, "scratch")
    pathDictBase = {
        "bidsPath": PathClass.Path([basePath, bidsDirName], isDirectory=True),
        "bidsProcessedPath": PathClass.Path([basePath, "data_bids_processed"], isDirectory=True),
        "bidsStatisticsPath": PathClass.Path([basePath, "data_bids_statistics"], isDirectory=True),
        "QCPath": PathClass.Path([basePath, "meta_QC"], isDirectory=True),
        "PipePath": PathClass.Path([basePath, "meta_mrpipe"], isDirectory=True),
        "LogPath": PathClass.Path([basePath, "meta_logs"], isDirectory=True),
        "Scratch": PathClass.Path(scratch, isDirectory=True),
    }
    pathDictBase["PipeJobPath"] = PathClass.Path([pathDictBase["PipePath"], "PipeJobs"], isDirectory=True)

    n = SimpleNamespace(**pathDictBase) #make dot notation available for dictionaries
    return n


