from mrpipe.Toolboxes.Task import Task
from mrpipe.Helper import Helper
import os
from typing import List
from mrpipe.meta.PathClass import Path

class CCByMaskCharacterization(Task):
    def __init__(self, inCCFile: Path, masks: List[Path], outCSV: Path, name: str = "CCOverlapRemoval", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.inCCFile = inCCFile
        self.masks = masks
        self.outCSV = outCSV

        #add input and output images
        self.addInFiles([self.inCCFile, self.masks])
        self.addOutFiles(self.outCSV)

    def getCommand(self):
        CCByMaskCharacterization = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "CCByMaskCharacterization.py")
        command = f"python3 {CCByMaskCharacterization} -c {self.inCCFile} -r {self.mask} -o {self.outCSV}"
        return command

