from typing import List
from mrpipe.Toolboxes.Task import Task
from mrpipe.Helper import Helper
import os
from mrpipe.meta.PathClass import Path

class SelectAtlasROIs(Task):
    def __init__(self, infile: Path, outfile: Path, ROIs: List[int], binarize: bool = False, name: str = "SelectAtlasROIs", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.inputImage = infile
        self.ROIs = ROIs
        self.binarize = binarize
        self.outputFile = outfile

        #add input and output images
        self.addInFiles([self.inputImage])
        self.addOutFiles(self.outputFile)

    def getCommand(self):
        SelectAtlasROIs = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "SelectAtlasROIs.py")
        command = f"python3 {SelectAtlasROIs} -a {self.inputImage} -o {self.outputFile} -r {self.ROIs}"
        if self.binarize:
            command += " --binarize"
        return command
