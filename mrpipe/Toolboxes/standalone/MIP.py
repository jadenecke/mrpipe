from mrpipe.Toolboxes.Task import Task
import os
from mrpipe.Helper import Helper
from mrpipe.meta import LoggerModule
import sys


logger = LoggerModule.Logger()

class MIP(Task):
    #parser.add_argument('-i', '--input_file', dest='input_file', type=str, help='Path to the input NIfTI file.')
    # parser.add_argument('-o', '--output_file', dest='output_file', type=str, help='Path to the output NIfTI file.')
    # parser.add_argument('-p', '--projection_type', dest='projection_type', type=str, choices=['max', 'min'], help='Type of projection: max or min.', default = "min")
    # parser.add_argument('-z', '--z_stack_height', dest='z_stack_height', type=float, help='Z-stack height in millimeters.', default=8)
    def __init__(self, infile, outfile, projection_type: str = "min", z_stack_height: int = 8, name="MIP", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.infile = infile
        self.outfile = outfile
        self.projection_type = projection_type
        self.z_stack_height = z_stack_height

        if self.projection_type not in ["min", "max"]:
            logger.critical(f"Invalid projection type for MIP: Either 'min' or 'max' allowed, but got {self.projection_type}")
            sys.exit(1)

        # add input and output images
        self.addInFiles([self.infile])
        self.addOutFiles([self.outfile])

    def getCommand(self):
        command = "python " + os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "mip.py")
        command += f" -i {self.infile}"
        command += f" -o {self.outfile}"
        command += f" --projection_type {self.projection_type}"
        command += f" --z_stack_height {self.z_stack_height}"
        return command


