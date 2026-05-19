from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.PathClass import Path


class DWI5TTGEN(Task):

    def __init__(self, inputImage: Path, outputImage: Path, scratch, session, name: str = "dwi5ttgen", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputImage = inputImage
        self.outputImage = outputImage
        self.scratch = scratch


        #add input and output images
        self.addInFiles([self.inputImage])
        self.addOutFiles([self.outputImage])

    def getCommand(self):
        cpusPerTask = getattr(self.parent, "SLURM_cpusPerTask", None)
        command = f"5ttgen fsl {self.inputImage} {self.outputImage} -premasked -scratch {self.scratch}"
        if cpusPerTask:
            command += f" -nthreads {cpusPerTask}"
        if self.clobber:
            command += " -force"
        return command





