from mrpipe.Toolboxes.Task import Task
import os
from mrpipe.Helper import Helper
from mrpipe.meta import LoggerModule
from mrpipe.meta.PathClass import Path

logger = LoggerModule.Logger()

class CAT12(Task):
    def __init__(self, t1w, scriptPath, name="cat12", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.t1w = t1w
        if isinstance(self.t1w, Path):
            self.t1w.unzipFile()
        else:
            logger.error("Can't run cat12 because t1w input file is not a PathClass; Cannot unzip file. Module will fail if file is zipped. Path: {self.T1w}")
        self.scriptPath = scriptPath
        self.command = os.path.join("""matlab -nosplash -nodesktop -r \"try; run('{scriptPath}'); catch ME; end; if exist('ME'); display(ME); display(ME.stack); disp(getReport(ME,'extended')); end; exit\"""")

        # add input and output images
        self.addInFiles([self.t1w])
        self.addOutFiles([self.scriptPath])

    def getCommand(self):
        self.buildCat12Script()
        #TODO for whatever reason, cat12 does not produce a pdf/png output report. everything else runs fine but for QC reasons it woulde be real‚y nice to have.
        command = self.command.format(scriptPath=self.scriptPath)
        return command

    def buildCat12Script(self):
        spm_path = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "spm12")
        #cat12_path = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "cat12")
        TPM_path = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "spm12", "tpm", "TPM.nii")
        template_path = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "cat12", "templates_MNI152NLin2009cAsym", "Template_0_GS.nii")

        scriptString = """
        addpath('{spm_path}')
        
        matlabbatch{{1}}.spm.tools.cat.estwrite.data = {{'{t1w},1'}};
        matlabbatch{{1}}.spm.tools.cat.estwrite.data_wmh = {{''}};
        matlabbatch{{1}}.spm.tools.cat.estwrite.nproc = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.useprior = '';
        matlabbatch{{1}}.spm.tools.cat.estwrite.opts.tpm = {{'{TPM_path}'}};
        matlabbatch{{1}}.spm.tools.cat.estwrite.opts.affreg = 'mni';
        matlabbatch{{1}}.spm.tools.cat.estwrite.opts.biasacc = 0.5;
        matlabbatch{{1}}.spm.tools.cat.estwrite.extopts.restypes.optimal = [1 0.3];
        matlabbatch{{1}}.spm.tools.cat.estwrite.extopts.setCOM = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.extopts.APP = 1070;
        matlabbatch{{1}}.spm.tools.cat.estwrite.extopts.affmod = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.extopts.LASstr = 0.5;
        matlabbatch{{1}}.spm.tools.cat.estwrite.extopts.LASmyostr = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.extopts.gcutstr = 2;
        matlabbatch{{1}}.spm.tools.cat.estwrite.extopts.WMHC = 2;
        matlabbatch{{1}}.spm.tools.cat.estwrite.extopts.registration.shooting.shootingtpm = {{'{template_path}'}};
        matlabbatch{{1}}.spm.tools.cat.estwrite.extopts.registration.shooting.regstr = 0.5;
        matlabbatch{{1}}.spm.tools.cat.estwrite.extopts.vox = 1.0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.extopts.bb = 12;
        matlabbatch{{1}}.spm.tools.cat.estwrite.extopts.SRP = 22;
        matlabbatch{{1}}.spm.tools.cat.estwrite.extopts.ignoreErrors = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.BIDS.BIDSno = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.surface = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.surf_measures = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.ROImenu.atlases.neuromorphometrics = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.ROImenu.atlases.lpba40 = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.ROImenu.atlases.cobra = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.ROImenu.atlases.hammers = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.ROImenu.atlases.thalamus = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.ROImenu.atlases.suit = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.ROImenu.atlases.ibsr = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.ROImenu.atlases.ownatlas = {{''}};
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.GM.native = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.GM.mod = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.GM.dartel = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.WM.native = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.WM.mod = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.WM.dartel = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.CSF.native = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.CSF.warped = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.CSF.mod = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.CSF.dartel = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.ct.native = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.ct.warped = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.ct.dartel = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.pp.native = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.pp.warped = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.pp.dartel = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.WMH.native = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.WMH.warped = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.WMH.mod = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.WMH.dartel = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.SL.native = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.SL.warped = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.SL.mod = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.SL.dartel = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.TPMC.native = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.TPMC.warped = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.TPMC.mod = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.TPMC.dartel = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.atlas.native = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.label.native = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.label.warped = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.label.dartel = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.labelnative = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.bias.warped = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.las.native = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.las.warped = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.las.dartel = 0;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.jacobianwarped = 1;
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.warps = [1 1];
        matlabbatch{{1}}.spm.tools.cat.estwrite.output.rmat = 0;
        
        % run matlabbatch
        spm_jobman('run', matlabbatch)
        
        % exit matlab
        pause(5)
        quit
        """.format(t1w=self.t1w,
                   spm_path=spm_path,
                   #cat12_path=cat12_path,
                   TPM_path=TPM_path,
                   template_path=template_path)
        if self.scriptPath.exists():
            self.scriptPath.remove()
        with open(self.scriptPath, mode='w') as f:
            f.write(scriptString)
