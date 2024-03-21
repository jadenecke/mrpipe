from mrpipe.Toolboxes.Task import Task
import os
import mrpipe.Toolboxes
from mrpipe.Helper import Helper

class Split4D(Task):

    def __init__(self, infile, stem, outputNames=None,  name: str = "binarize", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.inputImage = infile
        self.stem = stem
        self.outputnames = Helper.ensure_list(outputNames, flatten=True)
        self.command = os.path.join(os.path.abspath(os.path.dirname(mrpipe.Toolboxes.__file__)), "submodules", "custom", "split4D.sh")

        #add input and output images
        self.addInFiles([self.inputImage])
        self.addOutFiles([self.outputnames])

    def getCommand(self):
        command = f"bash {self.command} {self.inputImage} {self.stem}"
        if self.outputnames:
            for name in self.outputnames:
                command += f" {name}"
        return command



