from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.PathClass import Path


class DWI2FOD(Task):

    def __init__(self, inputImage: Path, responseSFWM: Path, responseGM: Path, responseCSF: Path, responseWM_FOD: Path, responseGM_FOD: Path, responseCSF_FOD: Path, mask: Path, session, name: str = "dwi2fod", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputImage = inputImage
        self.responseSFWM = responseSFWM
        self.responseGM = responseGM
        self.responseCSF = responseCSF
        self.responseSFWM_FOD = responseWM_FOD
        self.responseGM_FOD = responseGM_FOD
        self.responseCSF_FOD = responseCSF_FOD
        self.mask = mask


        #add input and output images
        self.addInFiles([self.inputImage, self.responseSFWM, self.responseGM, self.responseCSF])
        self.addOutFiles([self.responseSFWM_FOD, self.responseGM_FOD, self.responseCSF_FOD])

    def getCommand(self):
        cpusPerTask = getattr(self.parent, "SLURM_cpusPerTask", None)
        command = f"dwi2fod msmt_csd {self.inputImage} {self.responseSFWM} {self.responseSFWM_FOD} {self.responseGM} {self.responseGM_FOD} {self.responseCSF} {self.responseCSF_FOD} -mask {self.mask}"
        if cpusPerTask:
            command += f" -nthreads {cpusPerTask}"
        if self.clobber:
            command += " -force"
        return command





