import os
from mrpipe.meta.PathClass import Path
from mrpipe.meta.PathCollection import PathCollection


class PathBase(PathCollection):
    def __init__(self, path: str, scratch: str = None):
        basePath: str = os.path.abspath(os.path.join(path, ".."))  # basepath is one up the specified data_bids path
        bidsDirName: str = os.path.basename(path)  # bidsname is the specified directory name

        if not os.path.isdir(basePath):
            raise (OSError.filename(basePath))
        if not os.path.isdir(os.path.join(basePath, bidsDirName)):
            raise (OSError.filename(bidsDirName))
        if not scratch:
            scratch = os.path.join(basePath, "scratch")

        self.basePath = Path(basePath, isDirectory=True)
        self.bidsPath = Path([basePath, bidsDirName], isDirectory=True)
        self.bidsProcessedPath = Path([basePath, "data_bids_processed"], isDirectory=True)
        self.bidsStatisticsPath = Path([basePath, "data_bids_statistics"], isDirectory=True)
        self.qcPath = Path([basePath, "meta_QC"], isDirectory=True)
        self.pipePath = Path([basePath, "meta_mrpipe"], isDirectory=True)
        self.logPath = Path([basePath, "meta_logs"], isDirectory=True)
        self.scratch = Path(scratch, isDirectory=True)
        self.pipeJobPath = Path([self.pipePath, "PipeJobs"], isDirectory=True)
