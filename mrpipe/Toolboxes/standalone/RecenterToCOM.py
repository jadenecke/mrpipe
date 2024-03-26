from mrpipe.Toolboxes.Task import Task
import os
import mrpipe.Toolboxes
from mrpipe.Helper import Helper
from mrpipe.meta.PathCollection import PathCollection
from mrpipe.meta.PathClass import Path
from mrpipe.meta import LoggerModule
logger = LoggerModule.Logger()


class RecenterToCOM(Task):

    def __init__(self, infile, outfile, abs: bool = False, ncores=1, name: str = "RecenterToCOM", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.ncores = ncores
        self.inputImage = infile
        self.clobber = clobber
        self.outfile = outfile
        self.abs = abs
        self.command = os.path.join(os.path.abspath(os.path.dirname(mrpipe.Toolboxes.__file__)), "submodules", "custom", "RecenterToCOM.py")

        #add input and output images
        self.addInFiles([self.inputImage])
        self.addOutFiles([self.outfile])

    def getCommand(self):
        command = f"python {self.command} -i {self.inputImage} -o {self.outfile}"
        if self.clobber:
            command += f" -c"
        if self.abs:
            command += f" --abs"
        return command

