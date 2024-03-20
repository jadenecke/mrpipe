from mrpipe.Toolboxes.Task import Task
import mrpipe.Toolboxes.submodules.hdbet as hdb
import os
import mrpipe.Toolboxes
class HDBET(Task):

    def __init__(self, infile, brain, mask, useGPU = False, name: str = "hdbet", verbose=False, clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.addInFiles(infile)
        self.inputImage = infile
        self.addOutFiles([brain, mask])
        self.outputBrain = brain
        self.outputMask = mask
        self.verbose = verbose
        self.useGPU = useGPU
        self.command = os.path.join(os.path.abspath(os.path.dirname(mrpipe.Toolboxes.__file__)), "submodules", "hdbet", "HD_BET", "hd-bet")


    def getCommand(self):
        command = f"{self.command} -i {self.inputImage} -o {self.outputBrain}"
        if not self.useGPU:
            command += f" -device cpu -tta 0"
        if self.verbose:
            command += f" -v"
        return command



