from mrpipe.modalityModules.ProcessingModule import ProcessingModule
from functools import partial
from mrpipe.schedueler.PipeJob import PipeJob
from mrpipe.schedueler import Slurm
from mrpipe.Toolboxes.ANTSTools.N4BiasFieldCorrect import N4BiasFieldCorrect
from mrpipe.Toolboxes.standalone.HDBet import HDBET
from mrpipe.Toolboxes.standalone.SynthSeg import SynthSeg
from mrpipe.Toolboxes.standalone.QCVis import QCVis
from mrpipe.Toolboxes.FSL.Binarize import Binarize
from mrpipe.Toolboxes.FSL.Split4D import Split4D
from mrpipe.Toolboxes.FSL.Add import Add
from mrpipe.Toolboxes.FSL.Erode import Erode
from mrpipe.Toolboxes.standalone.QCVisSynthSeg import QCVisSynthSeg
from mrpipe.Toolboxes.standalone.RecenterToCOM import RecenterToCOM
from mrpipe.Toolboxes.ANTSTools.AntsRegistrationSyN import AntsRegistrationSyN

class T1w_base(ProcessingModule):
    requiredModalities = ["T1w"]
    moduleDependencies = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)

        # Step 0: recenter Image to center of mass
        self.recenter = PipeJobPartial(name="T1w_base_recenterToCOM", job=SchedulerPartial(
            taskList=[RecenterToCOM(infile=session.subjectPaths.T1w.bids.T1w,
                                    outfile=session.subjectPaths.T1w.bids_processed.recentered,
                                    clobber=True) for session in
                      self.sessions],  # something
            cpusPerTask=1, cpusTotal=self.inputArgs.ncores,
            memPerCPU=2, minimumMemPerNode=4),
                                            env=self.envs.envMRPipe)

        # Step 1: N4 Bias corrections
        self.N4biasCorrect = PipeJobPartial(name="T1w_base_N4biasCorrect", job=SchedulerPartial(
            taskList=[N4BiasFieldCorrect(infile=session.subjectPaths.T1w.bids_processed.recentered,
                                         outfile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected) for session in
                      self.sessions],  # something
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=2, minimumMemPerNode=4),
                                            env=self.envs.envANTS)
        self.N4biasCorrect.setDependencies(self.recenter)

        # Step 2: Brain extraction using hd-bet
        self.hdbet = PipeJobPartial(name="T1w_base_hdbet", job=SchedulerPartial(
            taskList=[HDBET(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                            brain=session.subjectPaths.T1w.bids_processed.hdbet_brain,
                            mask=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                            useGPU=self.inputArgs.ngpus > 0) for session in
                      self.sessions],
            ngpus=self.inputArgs.ngpus), env=self.envs.envHDBET)
        self.hdbet.setDependencies(self.N4biasCorrect)

        #Step 3: Register to MNI
        self.NativeToMNI = PipeJobPartial(name="T1w_base_ToMNI", job=SchedulerPartial(
            taskList=[AntsRegistrationSyN(fixed=session.subjectPaths.T1w.bids_processed.recentered,
                                          moving=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                          outprefix="test",
                                          ncores=2, dim=3, type="s") for session in
                      self.sessions],  # something
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=2, minimumMemPerNode=4),
                                            env=self.envs.envANTS)
        self.NativeToMNI.setDependencies(self.N4biasCorrect)

        ########## QC ###########
        self.qc_vis_hdbet = PipeJobPartial(name="T1w_base_QC_slices_hdbet", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                            mask=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                            image=session.subjectPaths.T1w.meta_QC.hdbet_slices, contrastAdjustment=True) for session in
                      self.sessions]), env=self.envs.envQCVis)
        self.qc_vis_hdbet.setDependencies([self.N4biasCorrect, self.hdbet])



    def setup(self) -> bool:
        self.addPipeJobs()
        return True


class T1w_SynthSeg(ProcessingModule):
    requiredModalities = ["T1w"]
    moduleDependencies = ["T1w_base"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)

        # Synthseg Segmentation
        self.synthseg = PipeJobPartial(name="T1w_base_SynthSeg", job=SchedulerPartial(
            taskList=[SynthSeg(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                               posterior=session.subjectPaths.T1w.bids_processed.synthsegPosterior,
                               posteriorProb=session.subjectPaths.T1w.bids_processed.synthsegPosteriorProbabilities,
                               volumes=session.subjectPaths.T1w.bids_statistics.synthsegVolumes,
                               resample=session.subjectPaths.T1w.bids_processed.synthsegResample,
                               qc=session.subjectPaths.T1w.meta_QC.synthsegQC,
                               useGPU=self.inputArgs.ngpus > 0, ncores=2) for session in
                      self.sessions],
            ngpus=self.inputArgs.ngpus, memPerCPU=8, cpusPerTask=2, minimumMemPerNode=16), env=self.envs.envSynthSeg)
        #has external depencies set in self.setup()

        self.synthsegSplit = PipeJobPartial(name="T1w_base_SynthSegSplit", job=SchedulerPartial(
            taskList=[Split4D(infile=session.subjectPaths.T1w.bids_processed.synthsegPosteriorProbabilities,
                              stem=session.subjectPaths.T1w.bids_processed.synthsegSplitStem,
                              outputNames=[
                                  session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.getAllPaths()]) for
                      session in
                      self.sessions],
            memPerCPU=2, cpusPerTask=2, minimumMemPerNode=8), env=self.envs.envFSL)
        self.synthsegSplit.setDependencies(self.synthseg)


        #Full masks
        self.GMmerge = PipeJobPartial(name="T1w_base_GMmerge", job=SchedulerPartial(
            taskList=[Add(infiles=[
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.left_cerebral_cortex,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.left_cerebellum_cortex,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.left_thalamus,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.left_caudate,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.left_putamen,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.left_pallidum,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.left_hippocampus,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.left_amygdala,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.left_accumbens_area,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.left_ventral_DC,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.right_cerebral_cortex,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.right_cerebellum_cortex,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.right_thalamus,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.right_caudate,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.right_putamen,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.right_pallidum,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.right_hippocampus,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.right_amygdala,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.right_accumbens_area,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.right_ventral_DC
            ],
                output=session.subjectPaths.T1w.bids_processed.synthsegGM) for session in
                self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.GMmerge.setDependencies(self.synthsegSplit)


        self.WMmerge = PipeJobPartial(name="T1w_base_WMmerge", job=SchedulerPartial(
            taskList=[Add(infiles=[
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.left_cerebral_white_matter,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.right_cerebral_white_matter,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.right_cerebellum_white_matter,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.left_cerebellum_white_matter,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.brain_stem
            ],
                output=session.subjectPaths.T1w.bids_processed.synthsegWM) for session in
                self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.WMmerge.setDependencies(self.synthsegSplit)


        self.CSFmerge = PipeJobPartial(name="T1w_base_CSFmerge", job=SchedulerPartial(
            taskList=[Add(infiles=[
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.CSF,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.left_lateral_ventricle,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.right_lateral_ventricle,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.left_inferior_lateral_ventricle,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.right_inferior_lateral_ventricle,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.d3rd_ventricle,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.d4th_ventricle
            ],
                output=session.subjectPaths.T1w.bids_processed.synthsegCSF) for session in
                self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.CSFmerge.setDependencies(self.synthsegSplit)


        self.GMthr0p3 = PipeJobPartial(name="T1w_base_GM_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.maskGM_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.GMthr0p3.setDependencies(self.GMmerge)


        self.GMthr0p3ero1mm = PipeJobPartial(name="T1w_base_GM_thr0p3_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.maskGM_thr0p3,
                            output=session.subjectPaths.T1w.bids_processed.maskGM_thr0p3_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.GMthr0p3ero1mm.setDependencies(self.GMthr0p3)


        self.GMthr0p5 = PipeJobPartial(name="T1w_base_GM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.maskGM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.GMthr0p5.setDependencies(self.GMmerge)


        self.GMthr0p5ero1mm = PipeJobPartial(name="T1w_base_GM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.maskGM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.maskGM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.GMthr0p5ero1mm.setDependencies(self.GMthr0p5)


        self.WMthr0p5 = PipeJobPartial(name="T1w_base_WM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegWM,
                               output=session.subjectPaths.T1w.bids_processed.maskWM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.WMthr0p5.setDependencies(self.WMmerge)


        self.WMthr0p5ero1mm = PipeJobPartial(name="T1w_base_WM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.maskWM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.maskWM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.WMthr0p5ero1mm.setDependencies(self.WMthr0p5)


        self.CSFthr0p9 = PipeJobPartial(name="T1w_base_CSF_thr0p9", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegCSF,
                               output=session.subjectPaths.T1w.bids_processed.maskCSF_thr0p9,
                               threshold=0.9) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.CSFthr0p9.setDependencies(self.CSFmerge)


        self.CSFthr0p9ero1mm = PipeJobPartial(name="T1w_base_CSF_thr0p9_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.maskCSF_thr0p9,
                            output=session.subjectPaths.T1w.bids_processed.maskCSF_thr0p9_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.CSFthr0p9ero1mm.setDependencies(self.CSFthr0p9)

        #cortical Masks
        self.GMCorticalmerge = PipeJobPartial(name="T1w_base_GMCorticalmerge", job=SchedulerPartial(
            taskList=[Add(infiles=[
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.left_cerebral_cortex,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.right_cerebral_cortex
            ],
                output=session.subjectPaths.T1w.bids_processed.synthsegGMCortical) for session in
                self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.GMCorticalmerge.setDependencies(self.synthsegSplit)


        self.WMCorticalmerge = PipeJobPartial(name="T1w_base_WMCorticalmerge", job=SchedulerPartial(
            taskList=[Add(infiles=[
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.left_cerebral_white_matter,
                session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.right_cerebral_white_matter
            ],
                output=session.subjectPaths.T1w.bids_processed.synthsegWMCortical) for session in
                self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.WMCorticalmerge.setDependencies(self.synthsegSplit)


        self.GMCorticalthr0p3 = PipeJobPartial(name="T1w_base_GMCortical_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegGMCortical,
                               output=session.subjectPaths.T1w.bids_processed.maskGMCortical_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.GMCorticalthr0p3.setDependencies(self.GMCorticalmerge)

        self.GMCorticalthr0p3ero1mm = PipeJobPartial(name="T1w_base_GMCortical_thr0p3_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.maskGMCortical_thr0p3,
                            output=session.subjectPaths.T1w.bids_processed.maskGMCortical_thr0p3_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.GMCorticalthr0p3ero1mm.setDependencies(self.GMCorticalthr0p3)

        self.GMCorticalthr0p5 = PipeJobPartial(name="T1w_base_GMCortical_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegGMCortical,
                               output=session.subjectPaths.T1w.bids_processed.maskGMCortical_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.GMCorticalthr0p5.setDependencies(self.GMCorticalmerge)

        self.GMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_base_GMCortical_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.maskGMCortical_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.maskGMCortical_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.GMCorticalthr0p5ero1mm.setDependencies(self.GMCorticalthr0p5)

        self.WMCorticalthr0p5 = PipeJobPartial(name="T1w_base_WMCortical_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegWMCortical,
                               output=session.subjectPaths.T1w.bids_processed.maskWMCortical_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.WMCorticalthr0p5.setDependencies(self.WMCorticalmerge)

        self.WMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_base_WMCortical_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.maskWMCortical_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.maskWMCortical_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.WMCorticalthr0p5ero1mm.setDependencies(self.WMCorticalthr0p5)

        ########## QC ############
        self.qc_vis_GMthr0p3 = PipeJobPartial(name="T1w_base_QC_slices_GMthr0p3", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.synthsegResample,
                            mask=session.subjectPaths.T1w.bids_processed.maskGM_thr0p3,
                            image=session.subjectPaths.T1w.meta_QC.GMthr0p3_slices) for session in
                      self.sessions],
            ngpus=self.inputArgs.ngpus), env=self.envs.envQCVis)
        self.qc_vis_GMthr0p3.setDependencies(self.GMthr0p3)

        self.qc_vis_GMthr0p5 = PipeJobPartial(name="T1w_base_QC_slices_GMthr0p5", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.synthsegResample,
                            mask=session.subjectPaths.T1w.bids_processed.maskGM_thr0p5,
                            image=session.subjectPaths.T1w.meta_QC.GMthr0p5_slices) for session in
                      self.sessions],
            ngpus=self.inputArgs.ngpus), env=self.envs.envQCVis)
        self.qc_vis_GMthr0p5.setDependencies(self.GMthr0p5)

        self.qc_vis_WMthr0p5 = PipeJobPartial(name="T1w_base_QC_slices_WM", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.synthsegResample,
                            mask=session.subjectPaths.T1w.bids_processed.maskWM_thr0p5,
                            image=session.subjectPaths.T1w.meta_QC.WMthr0p5_slices) for session in
                      self.sessions],
            ngpus=self.inputArgs.ngpus), env=self.envs.envQCVis)
        self.qc_vis_WMthr0p5.setDependencies(self.WMthr0p5)

        self.qc_vis_CSFthr0p9 = PipeJobPartial(name="T1w_base_QC_slices_CSF", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.synthsegResample,
                            mask=session.subjectPaths.T1w.bids_processed.maskCSF_thr0p9,
                            image=session.subjectPaths.T1w.meta_QC.CSFthr0p9_slices) for session in
                      self.sessions],
            ngpus=self.inputArgs.ngpus), env=self.envs.envQCVis)
        self.qc_vis_CSFthr0p9.setDependencies(self.CSFthr0p9)

        self.qc_vis_synthseg = PipeJobPartial(name="T1w_base_QC_slices_synthseg", job=SchedulerPartial(
            taskList=[QCVisSynthSeg(infile=session.subjectPaths.T1w.bids_processed.synthsegResample,
                                    mask=session.subjectPaths.T1w.bids_processed.synthsegPosterior,
                                    image=session.subjectPaths.T1w.meta_QC.synthseg_slices,
                                    tempDir=self.inputArgs.scratch) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envQCVis)
        self.qc_vis_synthseg.setDependencies(self.synthseg)

    def setup(self) -> bool:
        #Set external dependencies
        self.synthseg.setDependencies(self.moduleDependenciesDict["T1w_base"].N4biasCorrect)

        self.addPipeJobs()
        return True



class T1w_1mm(ProcessingModule):
    requiredModalities = ["T1w"]
    moduleDependencies = ["T1w_base"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)

    def setup(self) -> bool:
        #Set external dependencies
        # self.synthseg.setDependencies(self.moduleDependenciesDict["T1w_base"].N4biasCorrect)

        self.addPipeJobs()
        return True