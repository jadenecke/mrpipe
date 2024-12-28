from mrpipe.Toolboxes.Task import Task
import os
from mrpipe.Helper import Helper
from mrpipe.meta import LoggerModule
from mrpipe.meta.PathClass import Path

logger = LoggerModule.Logger()


class ChiSeperation(Task):
    def __init__(self, mag4d_path, pha4d_path, brainmask_path, outdir, TEms, b0_direction, CFs, Toolboxes, pre_string,
                 chi_sep_dir, vendor, outfiles, name="chiSep", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.mag4d_path = mag4d_path
        self.pha4d_path = pha4d_path
        self.brainmask_path = brainmask_path
        self.outdir = outdir
        self.TEms = TEms
        self.b0_direction = b0_direction
        self.pre_string = pre_string
        self.chi_sep_dir = chi_sep_dir
        self.vendor = vendor
        self.CFs = CFs
        self.Toolboxes = Toolboxes
        self.outFiles = outfiles


        # Chisep_script_wResolGen(mag_path, phs_path, brainmask_path, csfmask_path, outdir, TEms, B0_direction, CFs, Toolboxes, preString, chiSepDir, vendor)
        self.command = os.path.join(
            """matlab -nosplash -nodesktop -r \"try; addpath('{chiSepPath}'); {command}; catch ME; end; if exist('ME'); display(ME); display(ME.stack); disp(getReport(ME,'extended')); end; exit\"""")

        # add input and output images
        self.addInFiles([self.mag4d_path, self.pha4d_path, self.brainmask_path])
        self.addOutFiles([self.outFiles])

    def getCommand(self):
        chiSepPath = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom")
        command = "Chisep_script_wResolGen(" + \
                  "'" + str(self.mag4d_path) + \
                  "', '" + str(self.pha4d_path) + \
                  "', '" + str(self.brainmask_path) + \
                  "', '" + str(self.outdir) + \
                  "', [" + ", ".join([str(i) for i in self.TEms]) + \
                  "], [" + ", ".join([str(i) for i in self.b0_direction]) + \
                  "], " + str(self.CFs) + \
                  ", {'" + "', '".join([str(p) for p in self.Toolboxes]) + "'}" + \
                  ", '" + str(self.pre_string) +  \
                  "', '" + str(self.chi_sep_dir) + \
                  "', '" + str(self.vendor) + "')"
        command = self.command.format(command=command, chiSepPath=chiSepPath)
        return command

    # matlab -nodesktop -nodisplay -r "addpath('/cluster2/jdenecke/Tools/QSM'); try; Chisep_script_wResolGen('mag4D.nii.gz', 'pha4D.nii.gz', 'bmask.nii.gz', 'bmask.nii.gz', 'output', [6.71,10.62,14.53,18.44,22.35], [0, 0, 1], 123.182053, [0.52,0.52,1.8], {'/cluster2/jdenecke/Forks_n_Stuff/STISuite_V30', '/cluster2/jdenecke/Forks_n_Stuff/MEDI_toolbox', '/cluster2/jdenecke/Forks_n_Stuff/CompileMRI.jl/matlab'}, 'testNewWithResolGen', '/cluster2/jdenecke/Forks_n_Stuff/chi-separationV113/Chisep_Toolbox_v1.1.3', 'Siemens'); catch ME; end; if exist('ME'); display(ME); display(ME.stack); disp(getReport(ME,'extended')); end; exit"
