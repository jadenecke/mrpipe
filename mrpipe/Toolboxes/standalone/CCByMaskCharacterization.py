from mrpipe.Toolboxes.Task import Task
from mrpipe.Helper import Helper
import os
from typing import List
from mrpipe.meta.PathClass import Path

class CCByMaskCharacterization(Task):
    def __init__(self, inCCFile: Path, masks: List[Path], outCSV: Path, mask_names: List[str] = None, name: str = "CCByMaskCharacterization", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.inCCFile = inCCFile
        self.masks = masks
        self.outCSV = outCSV
        self.mask_names = mask_names
        if self.mask_names is not None:
            assert len(self.mask_names) == len(self.masks), "Mask names and masks must have the same length."

        #add input and output images
        self.addInFiles([self.inCCFile, self.masks])
        self.addOutFiles(self.outCSV)

    def getCommand(self):
        CCByMaskCharacterization = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "CCByMaskCharacterization.py")
        command = f"python3 {CCByMaskCharacterization} -c {self.inCCFile} -r " + " ".join([str(p) for p in self.masks]) + f" -o {self.outCSV}"
        if self.mask_names is not None:
            command += f" --mask_names {' '.join(self.mask_names)}"
        return command

