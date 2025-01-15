from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.PathClass import Path
from mrpipe.Helper import Helper
import os


class SUVRToCentiloid(Task):

    """
    Only works for SUVR files generated by extractAtlasValues, or csv files where the first column is the ROI and the second column is the SUVR value.

    Options:
        -i SUVR.CSV, --in_file=SUVR.CSV Input file name
        -o CENTILOID.CSV, --out=CENTILOID.CSV Output file name
        -t NAME, --tracer=NAME Tracer name, one of [FBB, AV45, NAV4694, PIB]
        -h, --help Show this help message and exit
    """

    def __init__(self, infile: Path, outfile: Path, tracerName: str, name="SUVRToCentiloid", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.infile = infile
        self.outfile = outfile
        self.tracerName = tracerName

        # add input and output images
        self.addInFiles([self.infile])
        self.addOutFiles([self.outfile])


    def getCommand(self):
        command = os.path.join(Helper.get_libpath(), "submodules", "custom", "SUVRToCentiloid.R")
        command += f" -i {self.infile}"
        command += f" -o {self.outfile}"
        command += f" -t {self.tracerName}"
        return command

