from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.PathClass import Path


class MRDEGIBBS(Task):

    def __init__(self, inputImage: Path, outputImage: Path, session, name: str = "mrdegibbs", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputImage = inputImage
        self.outputImage = outputImage

        #add input and output images
        self.addInFiles([self.inputImage])
        self.addOutFiles([self.outputImage])

    def getCommand(self):
        command = f"mrdegibbs {self.inputImage} {self.outputImage}"
        cpusPerTask = getattr(self.parent, "cpusPerTask", None)
        if cpusPerTask:
            command += f" -nthreads {cpusPerTask}"
        if self.clobber:
            command += " -force"
        return command



