from mrpipe.Toolboxes.Task import Task
from mrpipe.Helper import Helper
import os
from mrpipe.meta.PathClass import Path

class ReduceToLargestCC(Task):
    def __init__(self, infile: Path, outfile: Path, name: str = "ReduceToLargestCC", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.inputImage = infile
        self.outputFile = outfile

        #add input and output images
        self.addInFiles([self.inputImage])
        self.addOutFiles(self.outputFile)

    def getCommand(self):
        ReduceToLargestCC = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "ReduceToLargestCC.py")
        command = f"python3 {ReduceToLargestCC} -i {self.inputImage} -o {self.outputFile}"
        return command
