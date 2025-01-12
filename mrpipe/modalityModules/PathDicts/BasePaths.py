import os
from mrpipe.meta.PathClass import Path
from mrpipe.meta.PathCollection import PathCollection
from mrpipe.meta import LoggerModule

logger = LoggerModule.Logger()

class PathBase(PathCollection):
    def __init__(self, path: str, scratch: str = None):
        basePath: str = os.path.abspath(os.path.join(path, os.pardir))  # basepath is one up the specified data_bids path
        bidsDirName: str = os.path.basename(path)  # bidsname is the specified directory name

        if not os.path.isdir(basePath):
            raise (OSError.filename(basePath))
        if not os.path.isdir(os.path.join(basePath, bidsDirName)):
            raise (OSError.filename(bidsDirName))

        self.basePath = Path(basePath, isDirectory=True)
        self.bidsPath = Path([basePath, bidsDirName], isDirectory=True)
        self.bidsProcessedPath = Path([basePath, "data_bids_processed"], isDirectory=True, create = True)
        self.bidsStatisticsPath = Path([basePath, "data_bids_statistics"], isDirectory=True, create = True)
        self.qcPath = Path([basePath, "meta_QC"], isDirectory=True, create = True)
        self.pipePath = Path([basePath, "meta_mrpipe"], isDirectory=True, create = True)
        self.logPath = Path([basePath, "meta_logs"], isDirectory=True, create = True)
        # self.scratch = Path(scratch, isDirectory=True, create=False)
        self.pipeJobPath = Path([self.pipePath, "PipeJobs"], isDirectory=True, create = True)
        self.libPathFile = self.pipePath.join("LibPaths.yml")
        self.filePatternsPath = self.pipePath.join("filePatterns.json")
        self.configPath = self.pipePath.join("config.json")

        #Set and read in attributes universal to all Pathcollections
        PathCollection.configPath = self.configPath
        PathCollection.filePatternPath = self.filePatternsPath
        logger.process(f"PathDicts.BasePaths file pattern path after setting: {PathCollection.filePatternPath}")
        PathCollection.filePatternsFromJson()
        PathCollection.configFromJSON()

