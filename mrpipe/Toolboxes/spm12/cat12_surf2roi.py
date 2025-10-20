from mrpipe.Toolboxes.Task import Task
import os
from mrpipe.Helper import Helper
from mrpipe.meta import LoggerModule
from mrpipe.meta.PathClass import Path

logger = LoggerModule.Logger()

class CAT12_surf2roi(Task):
    def __init__(self, lh_thickness, scriptPath, outputFiles = None, name="cat12_surf2roi", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.lh_thickness = lh_thickness

        self.scriptPath = scriptPath
        self.command = os.path.join("""matlab -nosplash -nodesktop -r \"try; run('{scriptPath}'); catch ME; end; if exist('ME'); display(ME); display(ME.stack); disp(getReport(ME,'extended')); end; exit\"""")
        self.outputFiles = outputFiles

        # add input and output images
        self.addInFiles([self.lh_thickness])
        self.addOutFiles([self.outputFiles])

    def getCommand(self):
        self.buildCat12Script()
        command = self.command.format(scriptPath=self.scriptPath)
        return command

    def buildCat12Script(self):
        spm_path = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "spm12")
        schaefer100_17 = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "cat12", "atlases_surfaces", "lh.Schaefer2018_100Parcels_17Networks_order.annot")
        schaefer200_17 = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "cat12", "atlases_surfaces", "lh.Schaefer2018_200Parcels_17Networks_order.annot")
        schaefer400_17 = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "cat12", "atlases_surfaces", "lh.Schaefer2018_400Parcels_17Networks_order.annot")
        schaefer600_17 = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "cat12", "atlases_surfaces", "lh.Schaefer2018_600Parcels_17Networks_order.annot")
        aparc_DK40 = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "cat12", "atlases_surfaces", "lh.aparc_DK40.freesurfer.annot")
        aparc_HCP_MMP1 = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "cat12", "atlases_surfaces", "lh.aparc_HCP_MMP1.freesurfer.annot")
        aparc_a2009s = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "cat12", "atlases_surfaces", "lh.aparc_a2009s.freesurfer.annot")

        scriptString = """
        addpath('{spm_path}')
        
        matlabbatch{{1}}.spm.tools.cat.stools.surf2roi.cdata = {{{{'{lh_thickness}'}}}};
        matlabbatch{{1}}.spm.tools.cat.stools.surf2roi.rdata = {{
                                                      '{schaefer100_17}'
                                                      '{schaefer200_17}'
                                                      '{schaefer400_17}'
                                                      '{schaefer600_17}'
                                                      '{aparc_DK40}'
                                                      '{aparc_HCP_MMP1}'
                                                      '{aparc_a2009s}'
                                                      }};
        % run matlabbatch
        spm_jobman('run', matlabbatch)
        
        % exit matlab
        pause(5)
        quit
        """.format(lh_thickness=self.lh_thickness,
                   spm_path=spm_path,
                   # cat12_path=cat12_path,
                   schaefer100_17=schaefer100_17,
                   schaefer200_17=schaefer200_17,
                   schaefer400_17=schaefer400_17,
                   schaefer600_17=schaefer600_17,
                   aparc_DK40=aparc_DK40,
                   aparc_HCP_MMP1=aparc_HCP_MMP1,
                   aparc_a2009s=aparc_a2009s)
        if self.scriptPath.exists():
            self.scriptPath.remove()
        with open(self.scriptPath, mode='w') as f:
            f.write(scriptString)
