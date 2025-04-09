from mrpipe.Toolboxes.Task import Task
from mrpipe.Helper import Helper
from typing import List
import os
from mrpipe.meta.PathClass import StatsFilePath
from mrpipe.meta.PathClass import Path

class CCC(Task):
    def __init__(self, infile: Path, output: StatsFilePath, name: str = "CountConnectedComponents", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.inputImage = infile
        self.outputFile = output


        #add input and output images
        self.addInFiles([self.inputImage])
        self.addOutFiles(self.outputFile)

    def getCommand(self):
        appendToJSON_scriptPath = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "appendToJSON.py")
        CCCScript = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "CountConnectedComponents.py")
        command = f"python3 {appendToJSON_scriptPath} {self.outputFile.path} {self.outputFile.attributeName} $(python {CCCScript} -m {self.inputImage.pathself.inputImage.path})"
        return command

