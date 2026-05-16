from typing import List

from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.ImageWithSideCar import ImageWithSideCar
from mrpipe.meta.PathClass import Path


class DTIFIT(Task):

    def __init__(self, inputImage: Path,  inputMask: Path, bval: Path, bvec: Path,
                 outputBasename: Path,  expectedOutputList: List[Path], session, name: str = "eddy", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputImage = inputImage
        self.inputMask = inputMask
        self.bval = bval
        self.bvec = bvec
        self.outputBasename = outputBasename

        #add input and output images
        self.addInFiles([self.inputMask, self.acqparam, self.index, self.bval, self.bvec, self.json])
        self.addOutFiles(expectedOutputList)

    def getCommand(self):
        # dtifit -k sub-${id}_ses-${visit}_dwi_temp.nii.gz -o sub-${id}_ses-${visit}_dti -m sub-${id}_ses-${visit}_dwi-mask.nii.gz
        # -r sub-${id}_ses-${visit}_dwi_temp.bvec -b sub-${id}_ses-${visit}_dwi_temp.bval
        command = f"dtifit -k {self.eddy_basename} -o {self.outputBasename} -m {self.inputMask} -r {self.bvec} -b {self.bval}"
        return command



