from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.PathClass import Path


class TOPUP(Task):

    def __init__(self, inputImage: Path, acqparam: Path, config: Path, outputDir: Path, outputImage: Path, outFieldcoef: Path, outMovepar: Path, session, name: str = "dwidenoise", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputImage = inputImage
        self.outputImage = outputImage
        self.acqparam = acqparam
        self.outputDir = outputDir
        self.config = config
        self.outFieldcoef = outFieldcoef
        self.outMovepar = outMovepar

        #add input and output images
        self.addInFiles([self.inputImage])
        self.addOutFiles([self.outputImage, self.outFieldcoef, self.outMovepar])

    def getCommand(self):
        command = f"topup --imain={self.inputImage} --datain={self.acqparam} --config={self.config} --out={self.outputDir} --iout={self.outputImage}"
        cpusPerTask = getattr(self.parent, "cpusPerTask", None)
        if cpusPerTask:
            command += f" --nthr={cpusPerTask}"
        return command



