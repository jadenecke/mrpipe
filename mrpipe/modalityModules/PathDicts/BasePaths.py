import os
from mrpipe.meta.PathClass import Path
from mrpipe.meta.PathCollection import PathCollection


class PathBase(PathCollection):
    def __init__(self, basePath: str, bidsDirName: str, scratch: str = None):
        if not os.path.isdir(basePath):
            raise (OSError.filename(basePath))
        if not os.path.isdir(os.path.join(basePath, bidsDirName)):
            raise (OSError.filename(bidsDirName))
        if not scratch:
            scratch = os.path.join(basePath, "scratch")

        self.bidsPath = Path([basePath, bidsDirName], isDirectory=True)
        self.bidsProcessedPath = Path([basePath, "data_bids_processed"], isDirectory=True)
        self.bidsStatisticsPath = Path([basePath, "data_bids_statistics"], isDirectory=True)
        self.QCPath = Path([basePath, "meta_QC"], isDirectory=True)
        self.PipePath = Path([basePath, "meta_mrpipe"], isDirectory=True)
        self.LogPath = Path([basePath, "meta_logs"], isDirectory=True)
        self.Scratch = Path(scratch, isDirectory=True)
        self.PipeJobPath = Path([self.PipePath, "PipeJobs"], isDirectory=True)


