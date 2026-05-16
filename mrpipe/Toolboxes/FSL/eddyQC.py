from typing import List

from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.ImageWithSideCar import ImageWithSideCar
from mrpipe.meta.PathClass import Path


class EDDYDiffusionQC(Task):

    def __init__(self, eddy_basename: Path, eddy_filelist: List[Path], json: Path, inputMask: Path, acqparam: Path, index: Path, bval: Path, bvec: Path,
                 outputDir: Path,  expectedOutputList: List[Path], session, name: str = "eddy", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.eddy_basename = eddy_basename
        self.inputMask = inputMask
        self.bval = bval
        self.bvec = bvec
        self.outputDir = outputDir
        self.acqparam = acqparam
        self.index = index
        self.json = json

        #add input and output images
        self.addInFiles([eddy_filelist, self.inputMask, self.acqparam, self.index, self.bval, self.bvec, self.json])
        self.addOutFiles(expectedOutputList)

    def getCommand(self):
        #eddy_quad temp_eddy -idx index.txt -par acqparams.txt -m temp_b0_hifi_avg_bet_mask.nii.gz -b temp_diffusion.bval -o outputDir
        command = f"eddy_quad {self.eddy_basename} --mask={self.inputMask} --eddyParams={self.acqparam} --eddyIdx={self.index} --output-dir={self.outputDir} --bvecs={self.bvec} --bvals={self.bval} --json={self.json}"
        return command



