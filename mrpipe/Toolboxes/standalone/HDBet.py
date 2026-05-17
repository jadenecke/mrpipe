from mrpipe.Toolboxes.Task import Task
import os
from mrpipe.Helper import Helper
import mrpipe.Toolboxes
class HDBET(Task):

    def __init__(self, infile, session, brain, mask, useGPU = False, name: str = "hdbet", verbose=False, clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputImage = infile
        self.outputBrain = brain
        self.outputMask = mask
        self.verbose = verbose
        self.useGPU = useGPU
        #self.command = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "hdbet", "HD_BET", "hd_bet_cli.py")
        self.command = "hd-bet"

        self.addInFiles(infile)
        self.addOutFiles([brain, mask])

    def getCommand(self):
        command = f"{self.command} -i {self.inputImage} -o {self.outputBrain} --save_bet_mask"
        if not self.useGPU:
            command += f" -device cpu --disable_tta"
        if self.verbose:
            command += f" --verbose"
        return command



