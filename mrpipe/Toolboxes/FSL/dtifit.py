from typing import List

from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.ImageWithSideCar import ImageWithSideCar
from mrpipe.meta.PathClass import Path, StatsFilePath
from mrpipe.meta.ImageSeries import DWI


class DTIFIT(Task):

    def __init__(self, inputImage: Path,  inputMask: Path, bval: Path, bvec: Path,
                 outputBasename: Path,  expectedOutputList: List[Path], nDirectionsB1000: StatsFilePath, session, name: str = "eddy", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputImage = inputImage
        self.inputMask = inputMask
        self.bval = bval
        self.bvec = bvec
        self.outputBasename = outputBasename
        self.nDirectionsB1000 = nDirectionsB1000

        #add input and output images
        self.addInFiles([self.inputMask, self.inputImage, self.bval, self.bvec])
        self.addOutFiles([expectedOutputList, self.nDirectionsB1000])

    def getCommand(self):
        self.nDirectionsB1000.writeValue(DWI.getNb1000(self.bval))
        command = f"dtifit -k {self.inputImage} -o {self.outputBasename} -m {self.inputMask} -r {self.bvec} -b {self.bval}"
        return command



