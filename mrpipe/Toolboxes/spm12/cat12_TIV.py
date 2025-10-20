from mrpipe.Toolboxes.Task import Task
import os
from mrpipe.Helper import Helper
from mrpipe.meta import LoggerModule
from mrpipe.meta.PathClass import Path

logger = LoggerModule.Logger()

class CAT12_TIV(Task):
    def __init__(self, xml_tiv, output, scriptPath,  name="cat12_TIV", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.xml_tiv = xml_tiv
        self.output = output

        self.scriptPath = scriptPath
        self.command = os.path.join("""matlab -nosplash -nodesktop -r \"try; run('{scriptPath}'); catch ME; end; if exist('ME'); display(ME); display(ME.stack); disp(getReport(ME,'extended')); end; exit\"""")

        # add input and output images
        self.addInFiles([self.xml_tiv])
        self.addOutFiles([self.output])

    def getCommand(self):
        self.buildCat12Script()
        command = self.command.format(scriptPath=self.scriptPath)
        return command

    def buildCat12Script(self):
        spm_path = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "spm12")

        scriptString = """
        addpath('{spm_path}')
        
        matlabbatch{{1}}.spm.tools.cat.tools.calcvol.data_xml = {{'{xml_tiv}'}};
        matlabbatch{{1}}.spm.tools.cat.tools.calcvol.calcvol_TIV = 0;
        matlabbatch{{1}}.spm.tools.cat.tools.calcvol.calcvol_savenames = 0;
        matlabbatch{{1}}.spm.tools.cat.tools.calcvol.calcvol_name = '{output}';

        % run matlabbatch
        spm_jobman('run', matlabbatch)
        
        % exit matlab
        pause(5)
        quit
        """.format(xml_tiv=self.xml_tiv,
                   spm_path=spm_path,
                   output=self.output
                   )
        if self.scriptPath.exists():
            self.scriptPath.remove()
        with open(self.scriptPath, mode='w') as f:
            f.write(scriptString)
