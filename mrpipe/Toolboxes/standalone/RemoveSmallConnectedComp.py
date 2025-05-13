from mrpipe.Toolboxes.Task import Task
from mrpipe.Helper import Helper
from typing import List
import os
from mrpipe.meta.PathClass import StatsFilePath
from mrpipe.meta.PathClass import Path

class RemoveSmallConnectedComp(Task):
    def __init__(self, infile: Path, outfile: Path, min_size=4, connectivity=26, name: str = "RemoveSmallConnectedComp", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.connectivity = connectivity
        self.min_size = min_size
        self.inputImage = infile
        self.outputFile = outfile

        #add input and output images
        self.addInFiles([self.inputImage])
        self.addOutFiles(self.outputFile)

    def getCommand(self):
        rmSmallCCScript = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "RemoveSmallConnectedComp.py")
        command = f"python3 {rmSmallCCScript} -i {self.inputImage} -o {self.outputFile} -s {self.min_size} -c {self.connectivity}"
        return command

