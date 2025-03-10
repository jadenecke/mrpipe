from mrpipe.Toolboxes.Task import Task
import os
import mrpipe.Toolboxes
from typing import List
from mrpipe.meta.PathClass import Path
from mrpipe.Helper import Helper
from mrpipe.meta import LoggerModule
logger = LoggerModule.Logger()

class AntsPyNet_WMH_PVS(Task):
    def __init__(self, t1: Path, flairReg: Path, outputTemplate: Path, outputFiles: List[Path], antspynetSIF, algorithms: List[str] = None, name: str = "AntsPyNet", clobber=False):
        super().__init__(name=name, clobber=clobber)

        supportedAlgorithms = ['shivai', 'sysu_media', 'hypermapp3r', 'ants_xnet', 'shiva_pvs']
        self.t1 = t1
        self.flairReg = flairReg
        self.algorithms = algorithms
        if self.algorithms is None:
            self.algorithms = ['hypermapp3r', 'shiva_pvs']
        self.antspynetSIF = antspynetSIF
        self.outputTemplate = outputTemplate
        self.outputFiles = outputFiles
        self.command = ""
        if not all([algorithms in supportedAlgorithms for algorithms in self.algorithms]):
            logger.error("Unsupported unwrapping algorithm: {}, supported algorithms are: {}".format(self.algorithms, supportedAlgorithms))

        #add input and output images
        self.addInFiles([self.t1, self.flairReg])
        self.addOutFiles([self.outputFiles])

    def getCommand(self):
        scriptPath = Path(os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "ANTsPyNet_WMH.py"))
        algorithmsString = "' '".join(self.algorithms)
        command = "singularity run --nv " + \
                  f"-B {self.t1.get_directory()} " + \
                  f"-B {self.flairReg.get_directory()} " + \
                  f"-B {self.outputTemplate.get_directory()} " + \
                  f"-B {scriptPath.get_directory()} " + \
                  f"{self.antspynetSIF} " + \
                  f" {scriptPath} " + \
                  f"-t1 {self.t1} " + \
                  f"-f {self.flairReg} " + \
                  f"-o {self.outputTemplate} " + \
                  f"-p '{algorithmsString}' "
        return command


# singularity run --nv /path/to/antspynet_latest-with-data.sif /path/to/ANTsPyNet_WMH.py
# -t1 mprage_denoised.nii
# -f 3dflair_toT1Warped_denoised.nii
# -o /t1Space_denoised_
# -p 'shivai' 'sysu_media' 'hypermapp3r' 'ants_xnet' 'shiva_pvs'



