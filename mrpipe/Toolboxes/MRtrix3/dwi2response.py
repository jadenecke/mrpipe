from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.PathClass import Path


class DWI2RESPONSE(Task):

    def __init__(self, inputImage: Path,  responseSFWM: Path, responseGM: Path, responseCSF: Path, mask: Path, voxelOut: Path, scratch: Path, session, name: str = "dwi2response", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputImage = inputImage
        self.responseSFWM = responseSFWM
        self.responseGM = responseGM
        self.responseCSF = responseCSF
        self.mask = mask
        self.voxelOut = voxelOut
        self.scratch = scratch


        #add input and output images
        self.addInFiles([self.inputImage, self.mask])
        self.addOutFiles([self.responseSFWM, self.responseGM, self.responseCSF, self.voxelOut])

    def getCommand(self):
        cpusPerTask = getattr(self.parent, "SLURM_cpusPerTask", None)
        command = f"dwi2response dhollander {self.inputImage} {self.responseSFWM} {self.responseGM} {self.responseCSF} -voxels {self.voxelOut} -mask {self.mask} -scratch {self.scratch}"
        if cpusPerTask:
            command += f" -nthreads {cpusPerTask}"
        if self.clobber:
            command += " -force"
        return command





