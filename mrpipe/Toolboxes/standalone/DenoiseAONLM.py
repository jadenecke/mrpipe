from mrpipe.Toolboxes.Task import Task
import os
from mrpipe.Helper import Helper
from mrpipe.meta import LoggerModule

logger = LoggerModule.Logger()

class DenoiseAONLM(Task):
    def __init__(self, infile, outfile, packagepath=os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "MRIDenoisingPackage_r01_pcode"),
                 riccian=True, name="MRIDenoiseAONLM", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.infile = infile
        self.outfile = outfile
        self.packagepath = packagepath
        self.riccian = riccian

        # Chisep_script_wResolGen(mag_path, phs_path, brainmask_path, csfmask_path, outdir, TEms, B0_direction, CFs, Toolboxes, preString, chiSepDir, vendor)
        self.command = """matlab -nosplash -nodesktop -r \"try; addpath('{packagepath}'); {command}; catch ME; end; if exist('ME'); display(ME); display(ME.stack); disp(getReport(ME,'extended')); end; exit\""""

        # add input and output images
        self.addInFiles([self.infile])
        self.addOutFiles([self.outfile])

    def getCommand(self):
        #TODO I added compression to the matlab sccript, so the correct files should be produced now, but double check later.
        riccian = self.riccian
        matlabInsert = "denoise_AONLM_cmd(" + \
                  "'" + str(self.infile) + \
                  "', '" + str(self.outfile.get_fullpath_sans_ending()) + \
                  "', " + str(int(self.riccian)) + \
                  ", '" + str(self.packagepath) + \
                  "')"
        # logger.process(matlabInsert)
        # logger.process(self.command)
        command = self.command.format(command=matlabInsert, packagepath=self.packagepath)
        return command
