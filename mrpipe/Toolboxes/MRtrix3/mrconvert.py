from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.ImageSeries import DWI
from mrpipe.meta.ImageWithSideCar import ImageWithSideCar
from mrpipe.meta.PathClass import Path


class MRCONVERTTOMIF(Task):

    def __init__(self, inputImage: Path, inputJson: Path, inputBval: Path, inputBvec: Path, mifOut: Path, session, name: str = "mrconvertToMif", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputImage = inputImage
        self.inputJson = inputJson
        self.inputBval = inputBval
        self.inputBvec = inputBvec
        self.outputImage = mifOut

        #add input and output images
        self.addInFiles([self.inputImage, self.inputJson, self.inputBval, self.inputBvec])
        self.addOutFiles([self.outputImage])

    def getCommand(self):
        command = f"mrconvert {self.inputImage} -json_import {self.inputJson} -fslgrad {self.inputBvec} {self.inputBval} {self.outputImage}"
        cpusPerTask = getattr(self.parent, "cpusPerTask", None)
        if cpusPerTask:
            command += f" -nthreads {cpusPerTask}"
        if self.clobber:
            command += " -force"
        return command

class MRCONVERTTONIFTI(Task):
    #mrconvert temp-pre_diffusion.mif temp_diffusion.nii.gz -export_grad_fsl temp_diffusion.bvec temp_diffusion.bval -json_export temp_diffusion.json -force
    def __init__(self, dwiIn: Path, imageOut: ImageWithSideCar, bavlOut: Path, bevcOut: Path, session, name: str = "mrconvertToNifti", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputImage = dwiIn
        self.outputImage = imageOut
        self.bavlOut = bavlOut
        self.bevcOut = bevcOut

        # add input and output images
        self.addInFiles([self.inputImage])
        self.addOutFiles([self.outputImage.imagePath, self.outputImage.jsonPath, self.bavlOut, self.bevcOut])

    def getCommand(self):
        command = f"mrconvert {self.inputImage} {self.outputImage.imagePath} -export_grad_fsl {self.bevcOut} {self.bavlOut} -json_export {self.outputImage.jsonPath}"
        cpusPerTask = getattr(self.parent, "cpusPerTask", None)
        if cpusPerTask:
            command += f" -nthreads {cpusPerTask}"
        if self.clobber:
            command += " -force"
        return command


