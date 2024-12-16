from mrpipe.Toolboxes.Task import Task
import mrpipe.Toolboxes.submodules.hdbet as hdb
import os
import mrpipe.Toolboxes
class Merge(Task):

    def __init__(self, infile,  output, dim="-t",  name: str = "merge", clobber=False):
        super().__init__(name=name, clobber=clobber)
        if dim not in ["-t", "-x", "-y", "-z"]:
            raise ValueError(f"dim must be either -t, -x, -y, -z on image {infile}")
        self.inputImageVector = infile
        self.dim = dim
        self.outputImage = output

        #add input and output images
        self.addInFiles([self.inputImageVector])
        self.addOutFiles([self.outputImage])

    def getCommand(self):
        command = f"fslmerge {self.dim} {self.outputImage} "
        for image in self.inputImageVector:
            command = command + f" {str(image)}"
        return command



