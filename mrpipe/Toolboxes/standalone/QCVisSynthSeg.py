from mrpipe.Toolboxes.Task import Task
import os
import mrpipe.Toolboxes

class QCVisSynthSeg(Task):

    def __init__(self, infile, session, mask, image, sliceNumber: int = 12, linesPerDirection = 2, colorLut = None, subject: str = None, tempDir=None, zoom: int = 1, checkerboard=True,  name: str = "QCVisSynthSeg", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputImage = infile
        self.outputImage = image
        self.inputMask = mask
        self.sliceNumber = sliceNumber
        self.linesPerDirection = linesPerDirection
        self.subject = subject
        self.tempDir = tempDir
        self.zoom = zoom
        self.colorLut = colorLut
        self.checkerboard = checkerboard

        if self.colorLut is None:
            self.colorLut = os.path.join(os.path.abspath(os.path.dirname(mrpipe.Toolboxes.__file__)), "submodules", "custom", "synthseg.lut")


        self.command = os.path.join(os.path.abspath(os.path.dirname(mrpipe.Toolboxes.__file__)), "submodules", "custom", "qcVisSynthSeg.sh")

        # add input and output images
        self.addInFiles([self.inputImage, self.inputMask])
        self.addOutFiles([self.outputImage])

    def getCommand(self):
        command = f"bash {self.command} -i {self.inputImage} -m {self.inputMask} -o {self.outputImage} -s {self.sliceNumber} -q {self.colorLut}"
        if self.subjectName:
            command += f" -k {self.subjectName}"
        if self.subjectName:
            command += f" -l {self.sessionName}"
        if self.tempDir:
            command += f"-t {self.tempDir}"
        if self.zoom:
            command += f" -z {self.zoom}"
        if self.checkerboard:
            command += f" -c"
        return command



