import os

from typing import Dict

from mrpipe.Helper import Helper
from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.PathClass import Path


class FIBERTRACKING2CONNECTOME(Task):

    def __init__(self, inputWMFOD: Path,  T1_5TTReg: Path, nstreamlines: int, outputbase: Path, scratch: Path, atlases: Dict[str, Path], session, name: str = "fibertracking2connectome", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputWMFOD = inputWMFOD
        self.T1_5TTReg = T1_5TTReg
        self.outputbase = outputbase
        self.scratch = scratch
        self.atlases = atlases
        self.nstreamlines = nstreamlines




        #add input and output images
        self.addInFiles([self.inputWMFOD, self.T1_5TTReg])
        self.addOutFiles([(self.outputbase + atlasname + ".csv") for atlasname in self.atlases.keys()])

    def getCommand(self):
        cpusPerTask = getattr(self.parent, "SLURM_cpusPerTask", None)

        #"Usage: $0 "
        command = "bash " + os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "MRtrix3", "tckgenSiftAnd2Connectome.sh")
        command = command + f" {self.inputWMFOD} {self.T1_5TTReg} {self.nstreamlines} {self.outputbase} {self.scratch}"
        if cpusPerTask:
            command += f" --threads {cpusPerTask}"
        if self.clobber:
            command += " --force"
        for atlasname, atlaspath in self.atlases.items():
            command += f" {atlasname} {atlaspath}"

        return command





