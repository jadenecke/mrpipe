import os

from mrpipe.Helper import Helper
from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.ImageSeries import DWI
from mrpipe.meta.ImageWithSideCar import ImageWithSideCar
from mrpipe.meta.PathClass import Path


class MRIDWIDENOISEDEGIBBSFromNifti(Task):

    def __init__(self, inputImage: Path, inputJson: Path, inputBval: Path, inputBvec: Path, outputDenoised: Path, outputjson: Path, outputBval: Path, outputBvec: Path, session, name: str = "mrconvertToMif", clobber=False):
        #<inputNifti> <inputjson> <inputbval> <inputbvec> <outputMif> <scratch> [--threads N] [--force]
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputImage = inputImage
        self.inputJson = inputJson
        self.inputBval = inputBval
        self.inputBvec = inputBvec
        self.outputMif = outputDenoised
        self.scratch = outputjson

        #add input and output images
        self.addInFiles([self.inputImage, self.inputJson, self.inputBval, self.inputBvec])
        self.addOutFiles([self.outputMif])

    def getCommand(self):
        script = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "MRtrix3", "dwiBiasCorrectToMIF.sh")
        command = f"bash {script} {self.inputImage} {self.inputJson} {self.inputBval} {self.inputBvec} {self.outputMif} {self.scratch}"
        return command



