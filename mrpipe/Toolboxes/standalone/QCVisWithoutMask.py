from mrpipe.Toolboxes.Task import Task
import os
import mrpipe.Toolboxes

class QCVisWithoutMask(Task):

    def __init__(self, infile, image, sliceNumber: int = 6, subject: str = None, session: str = None, tempDir=None,
                 line_breaks_per_dimension = 1, zoom: float = 1, name: str = "QCVisWithoutMask", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.inputImage = infile
        self.outputImage = image
        self.sliceNumber = sliceNumber
        self.subject = subject
        self.session = session
        self.tempDir = tempDir
        self.line_breaks_per_dimension = line_breaks_per_dimension
        self.zoom = zoom

        self.command = os.path.join(os.path.abspath(os.path.dirname(mrpipe.Toolboxes.__file__)), "submodules", "custom", "qcVisWithoutMask.sh")

        # add input and output images
        self.addInFiles([self.inputImage])
        self.addOutFiles([self.outputImage])

    def getCommand(self):
        command = f"bash {self.command} -i {self.inputImage} -o {self.outputImage} -s {self.sliceNumber} -b {self.line_breaks_per_dimension}"
        if self.subject:
            command += f" -k {self.subject}"
        if self.session:
            command += f" -l {self.session}"
        if self.tempDir:
            command += f"-t {self.tempDir}"
        if self.zoom:
            command += f" -z {self.zoom}"
        return command



