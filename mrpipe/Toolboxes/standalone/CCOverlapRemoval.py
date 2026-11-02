from mrpipe.Toolboxes.Task import Task
from mrpipe.Helper import Helper
import os
from mrpipe.meta.PathClass import Path

class CCOverlapRemoval(Task):
    def __init__(self, session, infile: Path, mask: Path, outfile: Path, inclusive: bool = False, threshold: float = 0,
                 name: str = "CCOverlapRemoval", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputImage = infile
        self.mask = mask
        self.threshold = threshold
        self.outputFile = outfile
        self.inclusive = inclusive
        assert self.threshold >= 0 and self.threshold <= 1, "Threshold must be between 0 and 1"

        #add input and output images
        self.addInFiles([self.inputImage, self.mask])
        self.addOutFiles(self.outputFile)

    def getCommand(self):
        CCOverlapRemoval = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "CCOverlapRemoval.py")
        command = f"python3 {CCOverlapRemoval} -i {self.inputImage} -r {self.mask} -o {self.outputFile}"
        if self.inclusive:
            command += " --inclusive"
        if self.threshold:
            command += " --threshold"
        return command

