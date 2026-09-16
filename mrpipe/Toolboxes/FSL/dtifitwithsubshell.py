from typing import List
import os
from mrpipe.Helper import Helper
from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.ImageWithSideCar import ImageWithSideCar
from mrpipe.meta.PathClass import Path, StatsFilePath
from mrpipe.meta.ImageSeries import DWI


class DTIFITWithSubshell(Task):

    def __init__(self, inputImage: Path,  inputMask: Path, scratch: Path,
                 outputBasename: Path,  expectedOutputList: List[Path], nDirectionsB1000: StatsFilePath, session, name: str = "eddy", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputImage = inputImage
        self.inputMask = inputMask
        self.scratch = scratch
        self.outputBasename = outputBasename
        self.nDirectionsB1000 = nDirectionsB1000

        #add input and output images
        self.addInFiles([self.inputMask, self.inputImage])
        self.addOutFiles([expectedOutputList, self.nDirectionsB1000])

    def getCommand(self):
        self.nDirectionsB1000.writeValue(str(DWI.getNb1000_mif(self.inputImage)))
        script = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "MRtrix3", "dwiDTIFITWithSubselection.sh")
        #return "sleep 0.1"
        # < inputMif > < inputMask > < outputBasename > < scratch >
        command = f"bash {script} {self.inputImage} {self.inputMask} {self.outputBasename} {self.scratch}"
        return command



