from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.PathClass import Path
from mrpipe.Helper import Helper
import os


class SUVRToCentiloid(Task):

    def __init__(self, infile: Path, mask: Path, outimage: Path, radius=15, zoom=3, name="VisMicrobleeds", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.infile = infile
        self.mask = mask
        self.outimage = outimage
        self.radius = radius
        self.zoom = zoom

        # add input and output images
        self.addInFiles([self.infile, self.mask])
        self.addOutFiles([self.outimage])

    def getCommand(self):
        command = "python " + os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "VisMicroBleeds.py")
        command += f" -i {self.infile}"
        command += f" -m {self.mask}"
        command += f" -o {self.outimage}"
        command += f" --radius {self.radius}"
        command += f" --zoom {self.zoom}"
        return command
