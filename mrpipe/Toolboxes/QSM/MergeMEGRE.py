from mrpipe.Toolboxes.Task import Task
import mrpipe.Toolboxes.submodules.hdbet as hdb
import os
import mrpipe.Toolboxes
from mrpipe.meta.ImageSeries import MEGRE
from mrpipe.meta.PathClass import Path
from mrpipe.Helper import Helper


class MergeMEGRE(Task):

    def __init__(self, inputMEGRE: MEGRE, session,  outputMag4d: Path, outputPha4d: Path,
                 tempDir: Path, name: str = "mergeMEGRE", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputMEGRE = inputMEGRE
        self.outputMag4d = outputMag4d
        self.outputPha4d = outputPha4d
        self.tempDir = tempDir

        #add input and output images
        self.addInFiles([self.inputMEGRE])
        self.addOutFiles([self.outputMag4d, self.outputPha4d])

    def getCommand(self):
        script = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "mergeMEGRE.sh")
        reImagConvertScriptPath = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "ReImToMagPhase.R")
        if self.inputMEGRE.useRealImaginary:
            command = f"bash {script} --real {" ".join(self.inputMEGRE.get_real_paths()())} --imag {" ".join(self.inputMEGRE.get_imaginary_paths())} --tmp-dir {self.tempDir} --r-script {reImagConvertScriptPath} --out-mag {self.outputMag4d} --out-pha {self.outputPha4d}"
        else:
            command = f"bash {script} --mag {" ".join(self.inputMEGRE.get_magnitude_paths())} --pha {" ".join(self.inputMEGRE.get_phase_paths())} --out-mag {self.outputMag4d} --out-pha {self.outputPha4d}"
        return command



