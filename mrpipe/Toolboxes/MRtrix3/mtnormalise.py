from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.PathClass import Path


class MTNORMALISE(Task):

    def __init__(self, responseSFWM_FOD: Path, responseGM_FOD: Path, responseCSF_FOD: Path, responseSFWM_FOD_norm: Path, responseGM_FOD_norm: Path, responseCSF_FOD_norm: Path, mask: Path, session, name: str = "mtnormalise", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.responseSFWM_FOD = responseSFWM_FOD
        self.responseGM_FOD = responseGM_FOD
        self.responseCSF_FOD = responseCSF_FOD
        self.responseSFWM_FOD_norm = responseSFWM_FOD_norm
        self.responseGM_FOD_norm = responseGM_FOD_norm
        self.responseCSF_FOD_norm = responseCSF_FOD_norm
        self.mask = mask


        #add input and output images
        self.addInFiles([self.responseSFWM_FOD, self.responseGM_FOD, self.responseCSF_FOD])
        self.addOutFiles([self.responseSFWM_FOD_norm, self.responseGM_FOD_norm, self.responseCSF_FOD_norm])

    def getCommand(self):
        cpusPerTask = getattr(self.parent, "SLURM_cpusPerTask", None)
        command = f"mtnormalise {self.responseSFWM_FOD} {self.responseSFWM_FOD_norm} {self.responseGM_FOD} {self.responseGM_FOD_norm} {self.responseCSF_FOD} {self.responseCSF_FOD_norm} -mask {self.mask}"
        if cpusPerTask:
            command += f" -nthreads {cpusPerTask}"
        if self.clobber:
            command += " -force"
        return command





