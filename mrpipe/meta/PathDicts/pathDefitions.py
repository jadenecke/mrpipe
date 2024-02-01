import os

class PathDefinition:

    def __init__(self, path: str, isDirectory = False, create = False):
        self.path = path
        self.isDirectory = isDirectory
        return(self)

    def exists(self):


def createPathDictBase(basePath: str, bidsDirName: str, subjectID: str) -> dict:
    if not basePath.isdir():
        raise(OSError.filename(basePath))
    if not bidsDirName.isdir():
        raise(OSError.filename(bidsDirName))
    pathDictBase = {
        "bidsPath": os.path.join(basePath, bidsDirName),
        "bidsProcessedPath": os.path.join(basePath, "data_bids_processed"),
        "bidsStatisticsPath": os.path.join(basePath, "data_bids_statistics"),
        "QCPath": os.path.join(basePath, "meta_QC"),
        "jobPath": os.path.join(basePath, "meta_jobFiles"),
        "LogPath": os.path.join(basePath, "meta_logs"),
    }
    return pathDictBase


