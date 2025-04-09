from mrpipe.Toolboxes.Task import Task
import os
from mrpipe.Helper import Helper
from mrpipe.meta import LoggerModule
from mrpipe.meta.PathClass import Path

logger = LoggerModule.Logger()


class RescaleInKSpace4D(Task):
    def __init__(self, mag4d_path: Path, pha4d_path: Path, mag4d_pathOut: Path, pha4d_pathOut: Path, tukeyStrength: float = 0.2, name="RescaleInKSpace4D", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.mag4d_path = mag4d_path
        self.pha4d_path = pha4d_path
        self.mag4d_pathOut = mag4d_pathOut
        self.pha4d_pathOut = pha4d_pathOut
        if tukeyStrength < 0 or tukeyStrength > 1:
            raise ValueError("tukeyStrength must be between 0 and 1")
        self.tukeyStrength = tukeyStrength

        # Chisep_script_wResolGen(mag_path, phs_path, brainmask_path, csfmask_path, outdir, TEms, B0_direction, CFs, Toolboxes, preString, chiSepDir, vendor)
        self.command = """matlab -nosplash -nodesktop -r \"try; addpath('{scriptpath}'); {command}; catch ME; end; if exist('ME'); display(ME); display(ME.stack); disp(getReport(ME,'extended')); end; exit\""""

        # add input and output images
        self.addInFiles([self.mag4d_path, self.pha4d_path])
        self.addOutFiles([self.mag4d_pathOut, self.pha4d_pathOut])

    def getCommand(self):
        scriptpath = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom")
        command = "rescaleInKSpace4D(" + \
                  "'" + str(self.mag4d_path) + \
                  "', '" + str(self.pha4d_path) + \
                  "', '" + str(self.mag4d_pathOut) + \
                  "', '" + str(self.pha4d_pathOut) + \
                  f"', {self.tukeyStrength})"
        command = self.command.format(command=command, scriptpath=scriptpath)
        return command


