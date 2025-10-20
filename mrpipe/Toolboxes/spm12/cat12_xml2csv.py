from mrpipe.Toolboxes.Task import Task
import os
from mrpipe.Helper import Helper
from mrpipe.meta import LoggerModule
from mrpipe.meta.PathClass import Path

logger = LoggerModule.Logger()

class CAT12_xml2csv(Task):
    def __init__(self, xml_path, out_dir, name_prepend, scriptPath, outputFiles = None, name="cat12_surf2roi", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.xml_path = xml_path
        self.out_dir = out_dir
        self.name_prepend = name_prepend
        self.scriptPath = scriptPath
        self.outputFiles = outputFiles

        self.command = os.path.join("""matlab -nosplash -nodesktop -r \"try; run('{scriptPath}'); catch ME; end; if exist('ME'); display(ME); display(ME.stack); disp(getReport(ME,'extended')); end; exit\"""")

        # add input and output images
        self.addInFiles([self.xml_path])
        self.addOutFiles([self.outputFiles])
        if not out_dir.exists():
            out_dir.create()

    def getCommand(self):
        self.buildCat12Script()
        command = self.command.format(scriptPath=self.scriptPath)
        return command

    def buildCat12Script(self):
        spm_path = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "spm12")
        schaefer100_17 = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "cat12", "atlases_surfaces", "lh.Schaefer2018_100Parcels_17Networks_order.annot")

        scriptString = """
        addpath('{spm_path}')
        
        matlabbatch{{1}}.spm.tools.cat.tools.calcroi.roi_xml = {{'{xml_path}'}};
        matlabbatch{{1}}.spm.tools.cat.tools.calcroi.point = '.';
        matlabbatch{{1}}.spm.tools.cat.tools.calcroi.outdir = {{'{out_dir}'}};
        matlabbatch{{1}}.spm.tools.cat.tools.calcroi.calcroi_name = '{name_prepend}';
        
        % run matlabbatch
        spm_jobman('run', matlabbatch)
        
        % exit matlab
        pause(5)
        quit
        """.format(xml_path=self.xml_path,
                   spm_path=spm_path,
                   out_dir=self.out_dir,
                   name_prepend=self.name_prepend)
        if self.scriptPath.exists():
            self.scriptPath.remove()
        with open(self.scriptPath, mode='w') as f:
            f.write(scriptString)
