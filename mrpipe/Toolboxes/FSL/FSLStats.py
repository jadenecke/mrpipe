from mrpipe.Toolboxes.Task import Task
from mrpipe.Helper import Helper
from typing import List
import os
from mrpipe.meta.PathClass import StatsFilePath
from mrpipe.meta.PathClass import Path

class FSLStats(Task):

    def __init__(self, infile: Path, output: StatsFilePath, options: List[str], mask: Path = None,
                 preoptions: List[str] = None, name: str = "FSLStats", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.inputImage = infile
        self.options = Helper.ensure_list(options, flatten=True)
        self.preOptions = Helper.ensure_list(preoptions, flatten=True)
        self.outputFile = output
        self.mask = mask

        #add input and output images
        self.addInFiles([self.inputImage, self.mask])
        self.addOutFiles(self.outputFile)

    def getCommand(self):
        appendToJSON_scriptPath = os.path.join(Helper.get_libpath(), "mrpipe", "submodules", "custom", "appendToJSON.py")
        command = f"{appendToJSON_scriptPath} {self.outputFile.path} {self.outputFile.attributeName} $(fslstats"
        for opt in self.preOptions:
            command += f" {opt}"
        command += f" {self.inputImage.path}"
        for opt in self.options:
            if opt is "-k":
                command += f" -k {self.mask.path}"
            else:
                command += f" {opt}"
        return command



