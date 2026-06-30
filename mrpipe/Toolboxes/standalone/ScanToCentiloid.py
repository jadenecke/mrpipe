from mrpipe.Toolboxes.Task import Task
import os
import mrpipe.Toolboxes
from mrpipe.meta.PathClass import Path
from mrpipe.meta.Session import Session
from mrpipe.Helper import Helper


class ScanToCentiloid(Task):

    def __init__(self, session: Session, infile: Path, outfile: Path, tracer: str, name: str = "ScanToCentiloid", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputImage = infile
        self.outputImage = outfile
        self.tracer = tracer

        self.command = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "ScanToCentiloid.sh")

        # add input and output images
        self.addInFiles([self.inputImage])
        self.addOutFiles([self.outputImage])

    def getCommand(self):
        command = f"bash {self.command} {self.inputImage} -m {self.tracer} -o {self.outputImage}"
        return command



