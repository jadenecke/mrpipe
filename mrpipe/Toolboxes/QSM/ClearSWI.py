from mrpipe.Toolboxes.Task import Task
import os
import mrpipe.Toolboxes
from typing import List
from mrpipe.meta.PathClass import Path
from mrpipe.meta import LoggerModule
logger = LoggerModule.Logger()

class ClearSWI(Task):

    def __init__(self, mag4d_path: Path, pha4d_path: Path, TEms: List[float], outputDir: Path,  outputFiles: List[Path], clearswiSIF, unwrapping_algorithm: str = "romeo", name: str = "clearswi", clobber=False):
        super().__init__(name=name, clobber=clobber)
        supportedUnwrappingAlgorithms = ["romeo", "laplacian", "laplacianslice"]
        self.mag4d_path = mag4d_path
        self.pha4d_path = pha4d_path
        self.TEms = TEms
        self.unwrapping_algorithm = unwrapping_algorithm
        self.clearswiSIF = clearswiSIF
        self.outputDir = outputDir
        self.outputFiles = outputFiles
        self.command = ""
        if self.unwrapping_algorithm not in supportedUnwrappingAlgorithms:
            logger.error("Unsupported unwrapping algorithm: {}, supported algorithms are: {}".format(self.unwrapping_algorithm, supportedUnwrappingAlgorithms))

        #add input and output images
        self.addInFiles([self.mag4d_path, self.pha4d_path])
        self.addOutFiles([self.outputFiles])

    def getCommand(self):
        command = "singularity run --nv " + \
                  f"-B {self.mag4d_path.get_directory()} " + \
                  f"-B {self.pha4d_path.get_directory()} " + \
                  f"-B {self.outputDir} " + \
                  f"{self.clearswiSIF} " + \
                  f"-m {self.mag4d_path} " + \
                  f"-p {self.pha4d_path} " + \
                  f"-o {self.outputDir}" + \
                  f"-t {self.TEms} " + \
                  f"--unwrapping-algorithm {self.unwrapping_algorithm} " + \
                  "-v"
        return command






