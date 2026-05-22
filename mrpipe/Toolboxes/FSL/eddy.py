from typing import List

from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.ImageWithSideCar import ImageWithSideCar
from mrpipe.meta.PathClass import Path


class EDDYDiffusion(Task):

    def __init__(self, inputImage: ImageWithSideCar, inputMask: Path, acqparam: Path, index: Path, bval: Path, bvec: Path, topupBasename:Path,
                 outputBasename: Path,  expectedOutputList: List[Path], session, repol = True, data_is_shelled = True, residuals = True, cnr_maps = True,
                 sliceMovementCorrection=True, name: str = "eddy", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputImage = inputImage
        self.inputMask = inputMask
        self.bval = bval
        self.bvec = bvec
        self.topupBasename = topupBasename
        self.outputBasename = outputBasename
        self.acqparam = acqparam
        self.index = index
        self.repol = repol
        self.residuals = residuals
        self.cnr_maps = cnr_maps
        self.data_is_shelled = data_is_shelled
        self.sliceMovementCorrection = sliceMovementCorrection
        self.expectedOutputList = expectedOutputList

        #add input and output images
        self.addInFiles([self.inputImage.imagePath, self.inputImage.jsonPath, self.inputMask, self.acqparam, self.index, self.bval, self.bvec])
        self.addOutFiles(self.expectedOutputList)

    def getCommand(self):
        for file in self.expectedOutputList:
            if isinstance(file, Path):
                file.remove()

        cpusPerTask = getattr(self.parent, "SLURM_cpusPerTask", None)
        ngpus = getattr(self.parent, "SLURM_ngpus", None)
        if ngpus:
            command = "eddy_cuda"
        else:
            command = "eddy_cpu"

        command += f" diffusion --imain={self.inputImage.imagePath} --mask={self.inputMask} --acqp={self.acqparam} --index={self.index} --out={self.outputBasename} --bvecs={self.bvec} --bvals={self.bval} --topup={self.topupBasename}"
        if self.repol:
            command += f" --repol --json={self.inputImage.jsonPath}"
        if self.residuals:
            command += " --residuals"
        if self.cnr_maps:
            command += " --cnr_maps"
        if self.data_is_shelled:
            command += " --data_is_shelled"
        if self.sliceMovementCorrection:
            command += " --mporder=20 --s2v_niter=5 --s2v_lambda=1 --s2v_interp=trilinear"


        if cpusPerTask and not ngpus:
            command += f" --nthr={cpusPerTask}"
        return command



