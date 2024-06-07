from mrpipe.Toolboxes.Task import Task
import os
import mrpipe.Toolboxes

class magPhaseToReIm(Task):

    def __init__(self, mag, phase, real, imaginary, name="magPhaseToReIm", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.mag = mag
        self.phase = phase
        self.real = real
        self.imaginary = imaginary
        self.command = os.path.join(os.path.abspath(os.path.dirname(mrpipe.Toolboxes.__file__)), "submodules", "custom",
                                    "magPhaseToReIm.R")

        # add input and output images
        self.addInFiles([self.mag, self.phase])
        self.addOutFiles([self.real, self.imaginary])

    def getCommand(self):
        command = f"{self.command} -m {self.mag} -p {self.phase} -r {self.real} -i {self}"
        return command



