from mrpipe.Toolboxes.Task import Task
from mrpipe.Helper import Helper
from typing import List
import os
from mrpipe.meta.PathClass import StatsFilePath
from mrpipe.meta.PathClass import Path
from mrpipe.meta import LoggerModule

logger = LoggerModule.Logger()


class CCShapeAnalysis(Task):
    def __init__(self, infile: Path, ventricleMask: Path,outputCSV: Path, outputStem: Path = None, outputFiles: List[Path] = [], statistic: str = "all", name: str = "CCShapeAnalysis", clobber=False):
        #possible statistics: 'volume', 'distance', 'fa', 'compactness', 'sphericity', 'circularity', 'solidity', 'none', 'all'
        super().__init__(name=name, clobber=clobber)
        self.ventricleMask = ventricleMask
        self.statistic = statistic
        self.inputImage = infile
        self.outputStem = outputStem
        self.outputCSV = outputCSV
        self.outputFiles = outputFiles

        possible_statistics = ['volume', 'distance', 'fa', 'compactness', 'sphericity', 'circularity', 'solidity']

        #add input and output images
        self.addInFiles([self.inputImage, self.ventricleMask])
        self.addOutFiles([self.outputCSV, self.outputFiles])
        if statistic == "all":
            self.addOutFiles([self.outputCSV,
                             outputStem + "_CC_IDLabel.nii.gz",
                             [outputStem + "_" + s + ".nii.gz" for s in possible_statistics]])
        elif statistic in possible_statistics:
            self.addOutFiles([self.outputCSV,
                             outputStem + "_CC_IDLabel.nii.gz",
                             outputStem + "_" + statistic + ".nii.gz"])
        elif statistic == "none":
            self.addOutFiles([self.outputCSV,
                             outputStem + "_CC_IDLabel.nii.gz"])
        else:
            logger.critical("Invalid 'statistic' argument to CCShapeAnalysis. Possible arguments are: " + str(possible_statistics))

    def getCommand(self):
        CCShapeAnalysisScript = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "CCShapeAnalysis.py")
        command = f"python3 {CCShapeAnalysisScript} -l {self.inputImage} -v {self.ventricleMask} -c {self.outputCSV} -a {self.statistic} -o {self.outputStem}"
        return command

