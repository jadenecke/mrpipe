from mrpipe.Toolboxes.Task import Task
import os
import mrpipe.Toolboxes

class QCVis(Task):

    def __init__(self, infile, mask, image, sliceNumber: int = 6, subject: str = None, session: str = None, tempDir=None, zoom: int = 1, checkerboard=False, outline=True, contrastAdjustment=False, transparency=None, name: str = "QCVis", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.inputImage = infile
        self.outputImage = image
        self.inputMask = mask
        self.sliceNumber = sliceNumber
        self.subject = subject
        self.session = session
        self.tempDir = tempDir
        self.zoom = zoom
        self.checkerboard = checkerboard
        self.outline = outline
        self.contrastAdjustment = contrastAdjustment
        self.transparency = transparency
        if transparency is None:
            if self.outline:
                self.transparency = False
            else:
                self.transparency = True

        self.command = os.path.join(os.path.abspath(os.path.dirname(mrpipe.Toolboxes.__file__)), "submodules", "custom", "qcVis.sh")

        # add input and output images
        self.addInFiles([self.inputImage, self.inputMask])
        self.addOutFiles([self.outputImage])

    def getCommand(self):
        command = f"bash {self.command} -i {self.inputImage} -m {self.inputMask} -o {self.outputImage} -s {self.sliceNumber}"
        if self.subject:
            command += f" -k {self.subject}"
        if self.session:
            command += f" -l {self.session}"
        if self.tempDir:
            command += f"-t {self.tempDir}"
        if self.zoom:
            command += f" -z {self.zoom}"
        if self.checkerboard:
            command += f" -c"
        if self.outline:
            command += " -n"
        if self.contrastAdjustment:
            command += " -y"
        return command



