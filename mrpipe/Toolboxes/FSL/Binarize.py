from mrpipe.Toolboxes.Task import Task

class Binarize(Task):

    def __init__(self, infile, output, threshold: float, name: str = "binarize", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.inputImage = infile
        self.threshold = threshold
        self.outputImage = output

        #add input and output images
        self.addInFiles([self.inputImage])
        self.addOutFiles([self.outputImage])

    def getCommand(self):
        command = f"fslmaths {self.inputImage} -thr {self.threshold} -bin {self.outputImage}"
        return command



