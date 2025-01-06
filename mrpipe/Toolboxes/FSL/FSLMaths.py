from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.PathClass import Path
from typing import List
import re
from mrpipe.meta import LoggerModule
from mrpipe.Helper import Helper
import mrpipe.Toolboxes

logger = LoggerModule.Logger()

"""
Math string example:
{} -add {} -bin 
"""

class FSLMaths(Task):

    def __init__(self, infiles: List[Path], mathString: str, output: Path, name: str = "FSLMaths", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.infiles = infiles
        self.mathString = mathString
        self.outputImage = output

        self.infilePathStrings = [p.path for p in self.infiles]
        Helper.verifyFormattableString(self.infilePathStrings, mathString)

        #add input and output images
        self.addInFiles(self.infiles)
        self.addOutFiles([self.outputImage])

    def getCommand(self) -> str:
        command = f"fslmaths " + self.mathString.format(*self.infiles) + " " + self.outputImage.path
        return command




