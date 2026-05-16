from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.PathClass import Path


class DWIBiascorrect(Task):

    def __init__(self, inputImage: Path,  bval: Path, bvec: Path, outputImage: Path, scratch: Path, session, name: str = "dwibiascorrect", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputImage = inputImage
        self.bval = bval
        self.bvec = bvec
        self.scratch = scratch
        self.outputImage = outputImage

        #add input and output images
        self.addInFiles([self.inputImage, self.bval, self.bvec])
        self.addOutFiles([self.outputImage])

    def getCommand(self):
        cpusPerTask = getattr(self.parent, "cpusPerTask", None)
        command = f"dwibiascorrect ants {self.inputImage} {self.outputImage} -fslgrad {self.bvec} {self.bval} -scratch {self.scratch}"
        if cpusPerTask:
            command += f" -nthreads {cpusPerTask}"
        if self.clobber:
            command += " -force"
        return command





