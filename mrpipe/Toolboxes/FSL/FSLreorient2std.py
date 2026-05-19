from mrpipe.Toolboxes.Task import Task
from mrpipe.Helper import Helper
from typing import List
import os
from mrpipe.meta.PathClass import StatsFilePath
from mrpipe.meta.PathClass import Path



class FSLreorient2std(Task):
    def __init__(self, session, infile: Path, output: StatsFilePath, name: str = "FSLreorient2std", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputImage = infile
        self.outputFile = output

        #add input and output images
        self.addInFiles([self.inputImage])
        self.addOutFiles(self.outputFile)

    def getCommand(self):
        command = f"fslreorient2std {self.inputImage} {self.outputFile}"
        return command



