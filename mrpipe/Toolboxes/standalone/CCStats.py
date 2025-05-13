from mrpipe.Toolboxes.Task import Task
from mrpipe.Helper import Helper
from typing import List
import os
from mrpipe.meta.PathClass import StatsFilePath
from mrpipe.meta.PathClass import Path

class CCStats(Task):
    def __init__(self, infile: Path, output: StatsFilePath, statistic: str, connectivity: int = 26, name: str = "CCStats", clobber=False):
        #possible statistics: "countCC", "minVoxel", "maxVoxel", "meanVoxel", "stdVoxel", "totalVoxel", "minVolume", "maxVolume", "meanVolume", "stdVolume", "totalVolume"
        super().__init__(name=name, clobber=clobber)
        self.connectivity = connectivity
        self.statistic = statistic
        self.inputImage = infile
        self.outputFile = output

        #add input and output images
        self.addInFiles([self.inputImage])
        self.addOutFiles(self.outputFile)

    def getCommand(self):
        appendToJSON_scriptPath = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "appendToJSON.py")
        CCStatsScript = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "CCStats.py")
        command = f"python3 {appendToJSON_scriptPath} {self.outputFile.path} {self.outputFile.attributeName} $(python {CCStatsScript} -i {self.inputImage} -s {self.statistic} -c {self.connectivity})"
        return command

