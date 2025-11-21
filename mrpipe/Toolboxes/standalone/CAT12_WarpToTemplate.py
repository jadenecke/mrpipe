from mrpipe.Toolboxes.Task import Task
import os
from mrpipe.Helper import Helper
from mrpipe.meta import LoggerModule
from enum import Enum

logger = LoggerModule.Logger()
class ValidCat12Interps(Enum):
    nearestNeighbor = 0
    trilinear = 1
    bspline_2nd = 2
    bspline_3rd = 3
    bspline_4th = 4
    bspline_5th = 5
    bspline_6th = 6
    bspline_7th = 7

class CAT12_WarpToTemplate(Task):
    def __init__(self, infile, warpfile, outfile, interp: ValidCat12Interps = ValidCat12Interps.bspline_3rd, packagepathScript=os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom"),
                 packagepathSPM12=os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "spm12"), voxelsize=None,
                 name="CAT12_WarpToTemplate", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.infile = infile
        self.warpfile = warpfile
        self.outfile = outfile
        self.interp = interp
        self.packagepathScript = packagepathScript
        self.packagepathSPM12 = packagepathSPM12
        if voxelsize is None:
            self.voxelsize = "NaN"
        else:
            self.voxelsize = float(voxelsize)

        # Chisep_script_wResolGen(mag_path, phs_path, brainmask_path, csfmask_path, outdir, TEms, B0_direction, CFs, Toolboxes, preString, chiSepDir, vendor)
        self.command = """matlab -nosplash -nodesktop -r \"try; addpath('{packagepathScript}'); addpath('{packagepathSPM12}'); {command}; catch ME; end; if exist('ME'); display(ME); display(ME.stack); disp(getReport(ME,'extended')); end; exit\""""

        # add input and output images
        self.addInFiles([self.infile, self.warpfile])
        self.addOutFiles([self.outfile])

    def getCommand(self):
        matlabInsert = "Cat12_WarpToTemplate(" + \
                       "'" + str(self.infile) + \
                       "', '" + str(self.warpfile) + \
                       "', '" + str(self.outfile) + \
                       "', " + str(self.interp.value) + \
                       "', " + str(self.voxelsize) + \
                       ")"

        command = self.command.format(command=matlabInsert, packagepathScript=self.packagepathScript, packagepathSPM12=self.packagepathSPM12)
        return command
