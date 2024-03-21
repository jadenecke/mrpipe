from mrpipe.Toolboxes.Task import Task

class Erode(Task):

    def __init__(self, infile, output, size: int, name: str = "erode", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.inputImage = infile
        self.size = size
        self.outputImage = output

        #add input and output images
        self.addInFiles([self.inputImage])
        self.addOutFiles([self.outputImage])

    def getCommand(self):
        command = f"fslmaths {self.inputImage} -kernel sphere {self.size} -ero {self.outputImage}"
        return command



