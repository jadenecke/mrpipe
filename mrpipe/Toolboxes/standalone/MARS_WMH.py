from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.PathClass import Path
from mrpipe.meta import LoggerModule

logger = LoggerModule.Logger()

class MARS_WMH(Task):
    def __init__(self, t1: Path, flairReg: Path, wmhMaskOut: Path, MarsWMHSIF: Path, name: str = "MARS-WMH", clobber=False):
        super().__init__(name=name, clobber=clobber)

        self.t1 = t1
        self.flairReg = flairReg
        self.MarsWMHSIF = MarsWMHSIF
        self.wmhMaskOut = wmhMaskOut
        self.command = ""

        #add input and output images
        self.addInFiles([self.t1, self.flairReg])
        self.addOutFiles([self.wmhMaskOut])

    def getCommand(self):
        command = "singularity run --nv " + \
                  f"-B {self.t1.get_directory()} " + \
                  f"-B {self.flairReg.get_directory()} " + \
                  f"-B {self.wmhMaskOut.get_directory()} " + \
                  f"{self.MarsWMHSIF} " + \
                  f"--t1 {self.t1} " + \
                  f"--flair {self.flairReg} " + \
                  f"-o {self.wmhMaskOut} " + \
                  "--skipRegistration --saveStatistics --omitQC"
        return command


# singularity run --nv /path/to/antspynet_latest-with-data.sif /path/to/ANTsPyNet_WMH.py
# -t1 mprage_denoised.nii
# -f 3dflair_toT1Warped_denoised.nii
# -o /t1Space_denoised_
# -p 'shivai' 'sysu_media' 'hypermapp3r' 'ants_xnet' 'shiva_pvs'



