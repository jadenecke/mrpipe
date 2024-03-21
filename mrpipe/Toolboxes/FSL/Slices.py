from mrpipe.Toolboxes.Task import Task
import mrpipe.Toolboxes.submodules.hdbet as hdb
import os
import mrpipe.Toolboxes
class Slices(Task):

    def __init__(self, infile,  output, overlay=None, scale=1, name: str = "slices", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.inputImage = infile
        self.inputOverlay = overlay
        self.outputImage = output
        self.scale = scale

        #add input and output images
        self.addInFiles([self.inputImage])
        if self.inputOverlay:
            self.addInFiles([self.inputOverlay])
        self.addOutFiles([self.outputImage])

    def getCommand(self):
        command = f"slices {self.inputImage}"
        if self.inputOverlay:
            command += f" {self.inputOverlay}"
        command += f" -s {self.scale} -o {self.outputImage}"
        return command



