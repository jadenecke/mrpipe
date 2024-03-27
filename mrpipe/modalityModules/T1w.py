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
from mrpipe.Toolboxes.FSL.FlirtResampleToTemplate import FlirtResampleToTemplate
from mrpipe.Toolboxes.FSL.FlirtResampleIso import FlirtResampleIso


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
        self.synthseg = PipeJobPartial(name="T1w_SynthSeg_SynthSeg", job=SchedulerPartial(
            taskList=[SynthSeg(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                               posterior=session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosterior,
                               posteriorProb=session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorProbabilities,
                               volumes=session.subjectPaths.T1w.bids_statistics.synthsegVolumes,
                               resample=session.subjectPaths.T1w.bids_processed.synthseg.synthsegResample,
                               qc=session.subjectPaths.T1w.meta_QC.synthsegQC,
                               useGPU=self.inputArgs.ngpus > 0, ncores=2) for session in
                      self.sessions],
            ngpus=self.inputArgs.ngpus, memPerCPU=8, cpusPerTask=2, minimumMemPerNode=16), env=self.envs.envSynthSeg)
        # has external depencies set in self.setup()

        self.synthsegSplit = PipeJobPartial(name="T1w_SynthSeg_SynthSegSplit", job=SchedulerPartial(
            taskList=[Split4D(infile=session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorProbabilities,
                              stem=session.subjectPaths.T1w.bids_processed.synthseg.synthsegSplitStem,
                              outputNames=[
                                  session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.getAllPaths()])
                      for
                      session in
                      self.sessions],
            memPerCPU=2, cpusPerTask=2, minimumMemPerNode=8), env=self.envs.envFSL)
        self.synthsegSplit.setDependencies(self.synthseg)

        # Full masks
        self.GMmerge = PipeJobPartial(name="T1w_SynthSeg_GMmerge", job=SchedulerPartial(
            taskList=[Add(infiles=[
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_cerebral_cortex,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_cerebellum_cortex,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_thalamus,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_caudate,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_putamen,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_pallidum,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_hippocampus,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_amygdala,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_accumbens_area,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_ventral_DC,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_cerebral_cortex,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_cerebellum_cortex,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_thalamus,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_caudate,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_putamen,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_pallidum,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_hippocampus,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_amygdala,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_accumbens_area,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_ventral_DC
            ],
                output=session.subjectPaths.T1w.bids_processed.synthseg.synthsegGM) for session in
                self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.GMmerge.setDependencies(self.synthsegSplit)

        self.WMmerge = PipeJobPartial(name="T1w_SynthSeg_WMmerge", job=SchedulerPartial(
            taskList=[Add(infiles=[
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_cerebral_white_matter,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_cerebral_white_matter,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_cerebellum_white_matter,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_cerebellum_white_matter,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.brain_stem
            ],
                output=session.subjectPaths.T1w.bids_processed.synthseg.synthsegWM) for session in
                self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.WMmerge.setDependencies(self.synthsegSplit)

        self.CSFmerge = PipeJobPartial(name="T1w_SynthSeg_CSFmerge", job=SchedulerPartial(
            taskList=[Add(infiles=[
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.CSF,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_lateral_ventricle,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_lateral_ventricle,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_inferior_lateral_ventricle,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_inferior_lateral_ventricle,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.d3rd_ventricle,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.d4th_ventricle
            ],
                output=session.subjectPaths.T1w.bids_processed.synthseg.synthsegCSF) for session in
                self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.CSFmerge.setDependencies(self.synthsegSplit)

        # cortical Masks
        self.GMCorticalmerge = PipeJobPartial(name="T1w_SynthSeg_GMCorticalmerge", job=SchedulerPartial(
            taskList=[Add(infiles=[
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_cerebral_cortex,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_cerebral_cortex
            ],
                output=session.subjectPaths.T1w.bids_processed.synthseg.synthsegGMCortical) for session in
                self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.GMCorticalmerge.setDependencies(self.synthsegSplit)

        self.WMCorticalmerge = PipeJobPartial(name="T1w_SynthSeg_WMCorticalmerge", job=SchedulerPartial(
            taskList=[Add(infiles=[
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_cerebral_white_matter,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_cerebral_white_matter
            ],
                output=session.subjectPaths.T1w.bids_processed.synthseg.synthsegWMCortical) for session in
                self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.WMCorticalmerge.setDependencies(self.synthsegSplit)

        # Transfrom back to T1 native space
        self.SynthSegToNative_GM = PipeJobPartial(name="T1w_SynthSeg_ToNative_GM", job=SchedulerPartial(
            taskList=[FlirtResampleToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthseg.synthsegGM,
                                              reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                              output=session.subjectPaths.T1w.bids_processed.synthsegGM) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.SynthSegToNative_GM.setDependencies(self.GMmerge)

        self.SynthSegToNative_WM = PipeJobPartial(name="T1w_SynthSeg_ToNative_WM", job=SchedulerPartial(
            taskList=[FlirtResampleToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthseg.synthsegWM,
                                              reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                              output=session.subjectPaths.T1w.bids_processed.synthsegWM) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.SynthSegToNative_WM.setDependencies(self.WMmerge)

        self.SynthSegToNative_CSF = PipeJobPartial(name="T1w_SynthSeg_ToNative_CSF", job=SchedulerPartial(
            taskList=[FlirtResampleToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthseg.synthsegCSF,
                                              reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                              output=session.subjectPaths.T1w.bids_processed.synthsegCSF) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.SynthSegToNative_CSF.setDependencies(self.CSFmerge)

        self.SynthSegToNative_GMCortical = PipeJobPartial(name="T1w_SynthSeg_ToNative_GMCortical", job=SchedulerPartial(
            taskList=[
                FlirtResampleToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthseg.synthsegGMCortical,
                                        reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                        output=session.subjectPaths.T1w.bids_processed.synthsegGMCortical) for session
                in
                self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.SynthSegToNative_GMCortical.setDependencies(self.GMCorticalmerge)

        self.SynthSegToNative_WMCortical = PipeJobPartial(name="T1w_SynthSeg_ToNative_WMCortical", job=SchedulerPartial(
            taskList=[
                FlirtResampleToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthseg.synthsegWMCortical,
                                        reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                        output=session.subjectPaths.T1w.bids_processed.synthsegWMCortical) for session
                in
                self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.SynthSegToNative_WMCortical.setDependencies(self.WMCorticalmerge)

        # Calculate masks from probabilities maps
        self.GMthr0p3 = PipeJobPartial(name="T1w_SynthSeg_GM_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.maskGM_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.GMthr0p3.setDependencies(self.GMmerge)

        self.GMthr0p3ero1mm = PipeJobPartial(name="T1w_SynthSeg_GM_thr0p3_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.maskGM_thr0p3,
                            output=session.subjectPaths.T1w.bids_processed.maskGM_thr0p3_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.GMthr0p3ero1mm.setDependencies(self.GMthr0p3)

        self.GMthr0p5 = PipeJobPartial(name="T1w_SynthSeg_GM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.maskGM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.GMthr0p5.setDependencies(self.GMmerge)

        self.GMthr0p5ero1mm = PipeJobPartial(name="T1w_SynthSeg_GM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.maskGM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.maskGM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.GMthr0p5ero1mm.setDependencies(self.GMthr0p5)

        self.WMthr0p5 = PipeJobPartial(name="T1w_SynthSeg_WM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegWM,
                               output=session.subjectPaths.T1w.bids_processed.maskWM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.WMthr0p5.setDependencies(self.WMmerge)

        self.WMthr0p5ero1mm = PipeJobPartial(name="T1w_SynthSeg_WM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.maskWM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.maskWM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.WMthr0p5ero1mm.setDependencies(self.WMthr0p5)

        self.CSFthr0p9 = PipeJobPartial(name="T1w_SynthSeg_CSF_thr0p9", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegCSF,
                               output=session.subjectPaths.T1w.bids_processed.maskCSF_thr0p9,
                               threshold=0.9) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.CSFthr0p9.setDependencies(self.CSFmerge)

        self.CSFthr0p9ero1mm = PipeJobPartial(name="T1w_SynthSeg_CSF_thr0p9_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.maskCSF_thr0p9,
                            output=session.subjectPaths.T1w.bids_processed.maskCSF_thr0p9_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.CSFthr0p9ero1mm.setDependencies(self.CSFthr0p9)

        self.GMCorticalthr0p3 = PipeJobPartial(name="T1w_SynthSeg_GMCortical_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegGMCortical,
                               output=session.subjectPaths.T1w.bids_processed.maskGMCortical_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.GMCorticalthr0p3.setDependencies(self.GMCorticalmerge)

        self.GMCorticalthr0p3ero1mm = PipeJobPartial(name="T1w_SynthSeg_GMCortical_thr0p3_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.maskGMCortical_thr0p3,
                            output=session.subjectPaths.T1w.bids_processed.maskGMCortical_thr0p3_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.GMCorticalthr0p3ero1mm.setDependencies(self.GMCorticalthr0p3)

        self.GMCorticalthr0p5 = PipeJobPartial(name="T1w_SynthSeg_GMCortical_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegGMCortical,
                               output=session.subjectPaths.T1w.bids_processed.maskGMCortical_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.GMCorticalthr0p5.setDependencies(self.GMCorticalmerge)

        self.GMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_SynthSeg_GMCortical_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.maskGMCortical_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.maskGMCortical_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.GMCorticalthr0p5ero1mm.setDependencies(self.GMCorticalthr0p5)

        self.WMCorticalthr0p5 = PipeJobPartial(name="T1w_SynthSeg_WMCortical_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegWMCortical,
                               output=session.subjectPaths.T1w.bids_processed.maskWMCortical_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.WMCorticalthr0p5.setDependencies(self.WMCorticalmerge)

        self.WMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_SynthSeg_WMCortical_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.maskWMCortical_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.maskWMCortical_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.WMCorticalthr0p5ero1mm.setDependencies(self.WMCorticalthr0p5)

        ########## QC ############
        self.qc_vis_GMthr0p3 = PipeJobPartial(name="T1w_SynthSeg_QC_slices_GMthr0p3", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                            mask=session.subjectPaths.T1w.bids_processed.maskGM_thr0p3,
                            image=session.subjectPaths.T1w.meta_QC.GMthr0p3_slices) for session in
                      self.sessions],
            ngpus=self.inputArgs.ngpus), env=self.envs.envQCVis)
        self.qc_vis_GMthr0p3.setDependencies(self.GMthr0p3)

        self.qc_vis_GMthr0p5 = PipeJobPartial(name="T1w_SynthSeg_QC_slices_GMthr0p5", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                            mask=session.subjectPaths.T1w.bids_processed.maskGM_thr0p5,
                            image=session.subjectPaths.T1w.meta_QC.GMthr0p5_slices) for session in
                      self.sessions],
            ngpus=self.inputArgs.ngpus), env=self.envs.envQCVis)
        self.qc_vis_GMthr0p5.setDependencies(self.GMthr0p5)

        self.qc_vis_WMthr0p5 = PipeJobPartial(name="T1w_SynthSeg_QC_slices_WM", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                            mask=session.subjectPaths.T1w.bids_processed.maskWM_thr0p5,
                            image=session.subjectPaths.T1w.meta_QC.WMthr0p5_slices) for session in
                      self.sessions],
            ngpus=self.inputArgs.ngpus), env=self.envs.envQCVis)
        self.qc_vis_WMthr0p5.setDependencies(self.WMthr0p5)

        self.qc_vis_CSFthr0p9 = PipeJobPartial(name="T1w_SynthSeg_QC_slices_CSF", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                            mask=session.subjectPaths.T1w.bids_processed.maskCSF_thr0p9,
                            image=session.subjectPaths.T1w.meta_QC.CSFthr0p9_slices) for session in
                      self.sessions],
            ngpus=self.inputArgs.ngpus), env=self.envs.envQCVis)
        self.qc_vis_CSFthr0p9.setDependencies(self.CSFthr0p9)

        self.qc_vis_synthseg = PipeJobPartial(name="T1w_SynthSeg_QC_slices_synthseg", job=SchedulerPartial(
            taskList=[QCVisSynthSeg(infile=session.subjectPaths.T1w.bids_processed.synthseg.synthsegResample,
                                    mask=session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosterior,
                                    image=session.subjectPaths.T1w.meta_QC.synthseg_slices,
                                    tempDir=self.inputArgs.scratch) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envQCVis)
        self.qc_vis_synthseg.setDependencies(self.synthseg)

    def setup(self) -> bool:
        # Set external dependencies
        self.synthseg.setDependencies(self.moduleDependenciesDict["T1w_base"].N4biasCorrect)

        self.addPipeJobs()
        return True


class T1w_1mm(ProcessingModule):
    requiredModalities = ["T1w"]
    moduleDependencies = ["T1w_base", "T1w_SynthSeg"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)

        self.T1w_1mm_Native = PipeJobPartial(name="T1w_1mm_baseimage", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                       reference=self.templates.mni152_1mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso1mm.baseimage,
                                       isoRes=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_1mm_Brain = PipeJobPartial(name="T1w_1mm_brain", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.hdbet_brain,
                                       reference=self.templates.mni152_1mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso1mm.brain,
                                       isoRes=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_1mm_BrainMask = PipeJobPartial(name="T1w_1mm_brainMask", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                                       reference=self.templates.mni152_1mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso1mm.brainmask,
                                       isoRes=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        # Register to MNI
        self.T1w_1mm_NativeToMNI = PipeJobPartial(name="T1w_1mm_NativeToMNI", job=SchedulerPartial(
            taskList=[AntsRegistrationSyN(fixed=self.templates.mni152_1mm,
                                          moving=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                          outprefix=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_prefix,
                                          expectedOutFiles=[session.subjectPaths.T1w.bids_processed.iso1mm.MNI_toMNI,
                                                            session.subjectPaths.T1w.bids_processed.iso1mm.MNI_InverseWarped,
                                                            session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                            session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1Warp,
                                                            session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1InverseWarp],
                                          ncores=2, dim=3, type="s") for session in
                      self.sessions],  # something
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=2, minimumMemPerNode=4),
                                                  env=self.envs.envANTS)

        self.T1w_1mm_qc_vis_MNI = PipeJobPartial(name="T1w_1mm_QC_slices_MNI", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_toMNI,
                            mask=self.templates.mni152_brain_mask_1mm,
                            image=session.subjectPaths.T1w.meta_QC.MNI_1mm_slices, contrastAdjustment=False,
                            outline=True, transparency=True) for session in
                      self.sessions]), env=self.envs.envQCVis)
        self.T1w_1mm_qc_vis_MNI.setDependencies(self.T1w_1mm_NativeToMNI)

        # SynthSeg Masks
        self.T1w_1mm_synthsegGM = PipeJobPartial(name="T1w_1mm_synthsegGM", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                                       reference=self.templates.mni152_1mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegGM,
                                       isoRes=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_1mm_synthsegWM = PipeJobPartial(name="T1w_1mm_synthsegWM", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegWM,
                                       reference=self.templates.mni152_1mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegWM,
                                       isoRes=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_1mm_synthsegCSF = PipeJobPartial(name="T1w_1mm_synthsegCSF", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegCSF,
                                       reference=self.templates.mni152_1mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegCSF,
                                       isoRes=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_1mm_synthsegGMCortical = PipeJobPartial(name="T1w_1mm_synthsegGMCortical", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegGMCortical,
                                       reference=self.templates.mni152_1mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegGMCortical,
                                       isoRes=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_1mm_synthsegWMCortical = PipeJobPartial(name="T1w_1mm_synthsegWMCortical", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegWMCortical,
                                       reference=self.templates.mni152_1mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegWMCortical,
                                       isoRes=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        # Calculate masks from probabilities maps
        self.T1w_1mm_GMthr0p3 = PipeJobPartial(name="T1w_1mm_SynthSeg_GM_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso1mm.maskGM_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1mm_GMthr0p3.setDependencies(self.T1w_1mm_synthsegGM)

        self.T1w_1mm_GMthr0p3ero1mm = PipeJobPartial(name="T1w_1mm_SynthSeg_GM_thr0p3_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso1mm.maskGM_thr0p3,
                            output=session.subjectPaths.T1w.bids_processed.iso1mm.maskGM_thr0p3_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1mm_GMthr0p3ero1mm.setDependencies(self.T1w_1mm_GMthr0p3)

        self.T1w_1mm_GMthr0p5 = PipeJobPartial(name="T1w_1mm_SynthSeg_GM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso1mm.maskGM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1mm_GMthr0p5.setDependencies(self.T1w_1mm_synthsegGM)

        self.T1w_1mm_GMthr0p5ero1mm = PipeJobPartial(name="T1w_1mm_SynthSeg_GM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso1mm.maskGM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.iso1mm.maskGM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1mm_GMthr0p5ero1mm.setDependencies(self.T1w_1mm_GMthr0p5)

        self.T1w_1mm_WMthr0p5 = PipeJobPartial(name="T1w_1mm_SynthSeg_WM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegWM,
                               output=session.subjectPaths.T1w.bids_processed.iso1mm.maskWM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1mm_WMthr0p5.setDependencies(self.T1w_1mm_synthsegWM)

        self.T1w_1mm_WMthr0p5ero1mm = PipeJobPartial(name="T1w_1mm_SynthSeg_WM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso1mm.maskWM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.iso1mm.maskWM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1mm_WMthr0p5ero1mm.setDependencies(self.T1w_1mm_WMthr0p5)

        self.T1w_1mm_CSFthr0p9 = PipeJobPartial(name="T1w_1mm_SynthSeg_CSF_thr0p9", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegCSF,
                               output=session.subjectPaths.T1w.bids_processed.iso1mm.maskCSF_thr0p9,
                               threshold=0.9) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1mm_CSFthr0p9.setDependencies(self.T1w_1mm_synthsegCSF)

        self.T1w_1mm_CSFthr0p9ero1mm = PipeJobPartial(name="T1w_1mm_SynthSeg_CSF_thr0p9_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso1mm.maskCSF_thr0p9,
                            output=session.subjectPaths.T1w.bids_processed.iso1mm.maskCSF_thr0p9_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1mm_CSFthr0p9ero1mm.setDependencies(self.T1w_1mm_CSFthr0p9)

        self.T1w_1mm_GMCorticalthr0p3 = PipeJobPartial(name="T1w_1mm_SynthSeg_GMCortical_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegGMCortical,
                               output=session.subjectPaths.T1w.bids_processed.iso1mm.maskGMCortical_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1mm_GMCorticalthr0p3.setDependencies(self.T1w_1mm_synthsegGMCortical)

        self.T1w_1mm_GMCorticalthr0p3ero1mm = PipeJobPartial(name="T1w_1mm_SynthSeg_GMCortical_thr0p3_ero1mm",
                                                             job=SchedulerPartial(
                                                                 taskList=[Erode(
                                                                     infile=session.subjectPaths.T1w.bids_processed.iso1mm.maskGMCortical_thr0p3,
                                                                     output=session.subjectPaths.T1w.bids_processed.iso1mm.maskGMCortical_thr0p3_ero1mm,
                                                                     size=1) for session in
                                                                           self.sessions],
                                                                 cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1mm_GMCorticalthr0p3ero1mm.setDependencies(self.T1w_1mm_GMCorticalthr0p3)

        self.T1w_1mm_GMCorticalthr0p5 = PipeJobPartial(name="T1w_1mm_SynthSeg_GMCortical_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegGMCortical,
                               output=session.subjectPaths.T1w.bids_processed.iso1mm.maskGMCortical_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1mm_GMCorticalthr0p5.setDependencies(self.T1w_1mm_synthsegGMCortical)

        self.T1w_1mm_GMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_1mm_SynthSeg_GMCortical_thr0p5_ero1mm",
                                                             job=SchedulerPartial(
                                                                 taskList=[Erode(
                                                                     infile=session.subjectPaths.T1w.bids_processed.iso1mm.maskGMCortical_thr0p5,
                                                                     output=session.subjectPaths.T1w.bids_processed.iso1mm.maskGMCortical_thr0p5_ero1mm,
                                                                     size=1) for session in
                                                                           self.sessions],
                                                                 cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1mm_GMCorticalthr0p5ero1mm.setDependencies(self.T1w_1mm_GMCorticalthr0p5)

        self.T1w_1mm_WMCorticalthr0p5 = PipeJobPartial(name="T1w_1mm_SynthSeg_WMCortical_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegWMCortical,
                               output=session.subjectPaths.T1w.bids_processed.iso1mm.maskWMCortical_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1mm_WMCorticalthr0p5.setDependencies(self.T1w_1mm_synthsegWMCortical)

        self.T1w_1mm_WMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_1mm_SynthSeg_WMCortical_thr0p5_ero1mm",
                                                             job=SchedulerPartial(
                                                                 taskList=[Erode(
                                                                     infile=session.subjectPaths.T1w.bids_processed.iso1mm.maskWMCortical_thr0p5,
                                                                     output=session.subjectPaths.T1w.bids_processed.iso1mm.maskWMCortical_thr0p5_ero1mm,
                                                                     size=1) for session in
                                                                           self.sessions],
                                                                 cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1mm_WMCorticalthr0p5ero1mm.setDependencies(self.T1w_1mm_WMCorticalthr0p5)

    def setup(self) -> bool:
        # Set external dependencies
        self.T1w_1mm_Native.setDependencies(self.moduleDependenciesDict["T1w_base"].N4biasCorrect)
        self.T1w_1mm_Brain.setDependencies(self.moduleDependenciesDict["T1w_base"].hdbet)
        self.T1w_1mm_BrainMask.setDependencies(self.moduleDependenciesDict["T1w_base"].hdbet)
        self.T1w_1mm_NativeToMNI.setDependencies(self.moduleDependenciesDict["T1w_base"].N4biasCorrect)
        self.T1w_1mm_synthsegGM.setDependencies(self.moduleDependenciesDict["T1w_SynthSeg"].GMmerge)
        self.T1w_1mm_synthsegWM.setDependencies(self.moduleDependenciesDict["T1w_SynthSeg"].WMmerge)
        self.T1w_1mm_synthsegCSF.setDependencies(self.moduleDependenciesDict["T1w_SynthSeg"].CSFmerge)
        self.T1w_1mm_synthsegGMCortical.setDependencies(self.moduleDependenciesDict["T1w_SynthSeg"].GMCorticalmerge)
        self.T1w_1mm_synthsegWMCortical.setDependencies(self.moduleDependenciesDict["T1w_SynthSeg"].WMCorticalmerge)

        self.addPipeJobs()
        return True


class T1w_1p5mm(ProcessingModule):
    requiredModalities = ["T1w"]
    moduleDependencies = ["T1w_base", "T1w_SynthSeg"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)

        self.T1w_1p5mm_Native = PipeJobPartial(name="T1w_1p5mm_baseimage", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                       reference=self.templates.mni152_1p5mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso1p5mm.baseimage,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_1p5mm_Brain = PipeJobPartial(name="T1w_1p5mm_brain", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.hdbet_brain,
                                       reference=self.templates.mni152_1p5mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso1p5mm.brain,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_1p5mm_BrainMask = PipeJobPartial(name="T1w_1p5mm_brainMask", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                                       reference=self.templates.mni152_1p5mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso1p5mm.brainmask,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        # Register to MNI
        self.T1w_1p5mm_NativeToMNI = PipeJobPartial(name="T1w_1p5mm_NativeToMNI", job=SchedulerPartial(
            taskList=[AntsRegistrationSyN(fixed=self.templates.mni152_1p5mm,
                                          moving=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                          outprefix=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_prefix,
                                          expectedOutFiles=[session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_toMNI,
                                                            session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_InverseWarped,
                                                            session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_0GenericAffine,
                                                            session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_1Warp,
                                                            session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_1InverseWarp],
                                          ncores=2, dim=3, type="s") for session in
                      self.sessions],  # something
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=2, minimumMemPerNode=4),
                                                    env=self.envs.envANTS)

        self.T1w_1p5mm_qc_vis_MNI = PipeJobPartial(name="T1w_1p5mm_QC_slices_MNI", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_toMNI,
                            mask=self.templates.mni152_brain_mask_1p5mm,
                            image=session.subjectPaths.T1w.meta_QC.MNI_1p5mm_slices, contrastAdjustment=False,
                            outline=True, transparency=True) for session in
                      self.sessions]), env=self.envs.envQCVis)
        self.T1w_1p5mm_qc_vis_MNI.setDependencies(self.T1w_1p5mm_NativeToMNI)

        # SynthSeg Masks
        self.T1w_1p5mm_synthsegGM = PipeJobPartial(name="T1w_1p5mm_synthsegGM", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                                       reference=self.templates.mni152_1p5mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegGM,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_1p5mm_synthsegWM = PipeJobPartial(name="T1w_1p5mm_synthsegWM", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegWM,
                                       reference=self.templates.mni152_1p5mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegWM,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_1p5mm_synthsegCSF = PipeJobPartial(name="T1w_1p5mm_synthsegCSF", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegCSF,
                                       reference=self.templates.mni152_1p5mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegCSF,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_1p5mm_synthsegGMCortical = PipeJobPartial(name="T1w_1p5mm_synthsegGMCortical", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegGMCortical,
                                       reference=self.templates.mni152_1p5mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegGMCortical,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_1p5mm_synthsegWMCortical = PipeJobPartial(name="T1w_1p5mm_synthsegWMCortical", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegWMCortical,
                                       reference=self.templates.mni152_1p5mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegWMCortical,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        # Calculate masks from probabilities maps
        self.T1w_1p5mm_GMthr0p3 = PipeJobPartial(name="T1w_1p5mm_SynthSeg_GM_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGM_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1p5mm_GMthr0p3.setDependencies(self.T1w_1p5mm_synthsegGM)

        self.T1w_1p5mm_GMthr0p3ero1mm = PipeJobPartial(name="T1w_1p5mm_SynthSeg_GM_thr0p3_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGM_thr0p3,
                            output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGM_thr0p3_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1p5mm_GMthr0p3ero1mm.setDependencies(self.T1w_1p5mm_GMthr0p3)

        self.T1w_1p5mm_GMthr0p5 = PipeJobPartial(name="T1w_1p5mm_SynthSeg_GM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1p5mm_GMthr0p5.setDependencies(self.T1w_1p5mm_synthsegGM)

        self.T1w_1p5mm_GMthr0p5ero1mm = PipeJobPartial(name="T1w_1p5mm_SynthSeg_GM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1p5mm_GMthr0p5ero1mm.setDependencies(self.T1w_1p5mm_GMthr0p5)

        self.T1w_1p5mm_WMthr0p5 = PipeJobPartial(name="T1w_1p5mm_SynthSeg_WM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegWM,
                               output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskWM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1p5mm_WMthr0p5.setDependencies(self.T1w_1p5mm_synthsegWM)

        self.T1w_1p5mm_WMthr0p5ero1mm = PipeJobPartial(name="T1w_1p5mm_SynthSeg_WM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskWM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskWM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1p5mm_WMthr0p5ero1mm.setDependencies(self.T1w_1p5mm_WMthr0p5)

        self.T1w_1p5mm_CSFthr0p9 = PipeJobPartial(name="T1w_1p5mm_SynthSeg_CSF_thr0p9", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegCSF,
                               output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskCSF_thr0p9,
                               threshold=0.9) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1p5mm_CSFthr0p9.setDependencies(self.T1w_1p5mm_synthsegCSF)

        self.T1w_1p5mm_CSFthr0p9ero1mm = PipeJobPartial(name="T1w_1p5mm_SynthSeg_CSF_thr0p9_ero1mm",
                                                        job=SchedulerPartial(
                                                            taskList=[Erode(
                                                                infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskCSF_thr0p9,
                                                                output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskCSF_thr0p9_ero1mm,
                                                                size=1) for session in
                                                                      self.sessions],
                                                            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1p5mm_CSFthr0p9ero1mm.setDependencies(self.T1w_1p5mm_CSFthr0p9)

        self.T1w_1p5mm_GMCorticalthr0p3 = PipeJobPartial(name="T1w_1p5mm_SynthSeg_GMCortical_thr0p3",
                                                         job=SchedulerPartial(
                                                             taskList=[Binarize(
                                                                 infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegGMCortical,
                                                                 output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGMCortical_thr0p3,
                                                                 threshold=0.3) for session in
                                                                       self.sessions],
                                                             cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1p5mm_GMCorticalthr0p3.setDependencies(self.T1w_1p5mm_synthsegGMCortical)

        self.T1w_1p5mm_GMCorticalthr0p3ero1mm = PipeJobPartial(name="T1w_1p5mm_SynthSeg_GMCortical_thr0p3_ero1mm",
                                                               job=SchedulerPartial(
                                                                   taskList=[Erode(
                                                                       infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGMCortical_thr0p3,
                                                                       output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGMCortical_thr0p3_ero1mm,
                                                                       size=1) for session in
                                                                             self.sessions],
                                                                   cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1p5mm_GMCorticalthr0p3ero1mm.setDependencies(self.T1w_1p5mm_GMCorticalthr0p3)

        self.T1w_1p5mm_GMCorticalthr0p5 = PipeJobPartial(name="T1w_1p5mm_SynthSeg_GMCortical_thr0p5",
                                                         job=SchedulerPartial(
                                                             taskList=[Binarize(
                                                                 infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegGMCortical,
                                                                 output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGMCortical_thr0p5,
                                                                 threshold=0.5) for session in
                                                                       self.sessions],
                                                             cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1p5mm_GMCorticalthr0p5.setDependencies(self.T1w_1p5mm_synthsegGMCortical)

        self.T1w_1p5mm_GMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_1p5mm_SynthSeg_GMCortical_thr0p5_ero1mm",
                                                               job=SchedulerPartial(
                                                                   taskList=[Erode(
                                                                       infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGMCortical_thr0p5,
                                                                       output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGMCortical_thr0p5_ero1mm,
                                                                       size=1) for session in
                                                                             self.sessions],
                                                                   cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1p5mm_GMCorticalthr0p5ero1mm.setDependencies(self.T1w_1p5mm_GMCorticalthr0p5)

        self.T1w_1p5mm_WMCorticalthr0p5 = PipeJobPartial(name="T1w_1p5mm_SynthSeg_WMCortical_thr0p5",
                                                         job=SchedulerPartial(
                                                             taskList=[Binarize(
                                                                 infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegWMCortical,
                                                                 output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskWMCortical_thr0p5,
                                                                 threshold=0.5) for session in
                                                                       self.sessions],
                                                             cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1p5mm_WMCorticalthr0p5.setDependencies(self.T1w_1p5mm_synthsegWMCortical)

        self.T1w_1p5mm_WMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_1p5mm_SynthSeg_WMCortical_thr0p5_ero1mm",
                                                               job=SchedulerPartial(
                                                                   taskList=[Erode(
                                                                       infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskWMCortical_thr0p5,
                                                                       output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskWMCortical_thr0p5_ero1mm,
                                                                       size=1) for session in
                                                                             self.sessions],
                                                                   cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_1p5mm_WMCorticalthr0p5ero1mm.setDependencies(self.T1w_1p5mm_WMCorticalthr0p5)

    def setup(self) -> bool:
        # Set external dependencies
        self.T1w_1p5mm_Native.setDependencies(self.moduleDependenciesDict["T1w_base"].N4biasCorrect)
        self.T1w_1p5mm_Brain.setDependencies(self.moduleDependenciesDict["T1w_base"].hdbet)
        self.T1w_1p5mm_BrainMask.setDependencies(self.moduleDependenciesDict["T1w_base"].hdbet)
        self.T1w_1p5mm_NativeToMNI.setDependencies(self.moduleDependenciesDict["T1w_base"].N4biasCorrect)
        self.T1w_1p5mm_synthsegGM.setDependencies(self.moduleDependenciesDict["T1w_SynthSeg"].GMmerge)
        self.T1w_1p5mm_synthsegWM.setDependencies(self.moduleDependenciesDict["T1w_SynthSeg"].WMmerge)
        self.T1w_1p5mm_synthsegCSF.setDependencies(self.moduleDependenciesDict["T1w_SynthSeg"].CSFmerge)
        self.T1w_1p5mm_synthsegGMCortical.setDependencies(self.moduleDependenciesDict["T1w_SynthSeg"].GMCorticalmerge)
        self.T1w_1p5mm_synthsegWMCortical.setDependencies(self.moduleDependenciesDict["T1w_SynthSeg"].WMCorticalmerge)

        self.addPipeJobs()
        return True


class T1w_2mm(ProcessingModule):
    requiredModalities = ["T1w"]
    moduleDependencies = ["T1w_base", "T1w_SynthSeg"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)

        self.T1w_2mm_Native = PipeJobPartial(name="T1w_2mm_baseimage", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                       reference=self.templates.mni152_2mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso2mm.baseimage,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_2mm_Brain = PipeJobPartial(name="T1w_2mm_brain", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.hdbet_brain,
                                       reference=self.templates.mni152_2mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso2mm.brain,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_2mm_BrainMask = PipeJobPartial(name="T1w_2mm_brainMask", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                                       reference=self.templates.mni152_2mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso2mm.brainmask,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        # Register to MNI
        self.T1w_2mm_NativeToMNI = PipeJobPartial(name="T1w_2mm_NativeToMNI", job=SchedulerPartial(
            taskList=[AntsRegistrationSyN(fixed=self.templates.mni152_2mm,
                                          moving=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                          outprefix=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_prefix,
                                          expectedOutFiles=[session.subjectPaths.T1w.bids_processed.iso2mm.MNI_toMNI,
                                                            session.subjectPaths.T1w.bids_processed.iso2mm.MNI_InverseWarped,
                                                            session.subjectPaths.T1w.bids_processed.iso2mm.MNI_0GenericAffine,
                                                            session.subjectPaths.T1w.bids_processed.iso2mm.MNI_1Warp,
                                                            session.subjectPaths.T1w.bids_processed.iso2mm.MNI_1InverseWarp],
                                          ncores=2, dim=3, type="s") for session in
                      self.sessions],  # something
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=2, minimumMemPerNode=4),
                                                  env=self.envs.envANTS)

        self.T1w_2mm_qc_vis_MNI = PipeJobPartial(name="T1w_2mm_QC_slices_MNI", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_toMNI,
                            mask=self.templates.mni152_brain_mask_2mm,
                            image=session.subjectPaths.T1w.meta_QC.MNI_2mm_slices, contrastAdjustment=False,
                            outline=True, transparency=True) for session in
                      self.sessions]), env=self.envs.envQCVis)
        self.T1w_2mm_qc_vis_MNI.setDependencies(self.T1w_2mm_NativeToMNI)

        # SynthSeg Masks        
        self.T1w_2mm_synthsegGM = PipeJobPartial(name="T1w_2mm_synthsegGM", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                                       reference=self.templates.mni152_2mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegGM,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_2mm_synthsegWM = PipeJobPartial(name="T1w_2mm_synthsegWM", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegWM,
                                       reference=self.templates.mni152_2mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegWM,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_2mm_synthsegCSF = PipeJobPartial(name="T1w_2mm_synthsegCSF", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegCSF,
                                       reference=self.templates.mni152_2mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegCSF,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_2mm_synthsegGMCortical = PipeJobPartial(name="T1w_2mm_synthsegGMCortical", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegGMCortical,
                                       reference=self.templates.mni152_2mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegGMCortical,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_2mm_synthsegWMCortical = PipeJobPartial(name="T1w_2mm_synthsegWMCortical", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegWMCortical,
                                       reference=self.templates.mni152_2mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegWMCortical,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        # Calculate masks from probabilities maps
        self.T1w_2mm_GMthr0p3 = PipeJobPartial(name="T1w_2mm_SynthSeg_GM_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso2mm.maskGM_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_2mm_GMthr0p3.setDependencies(self.T1w_2mm_synthsegGM)

        self.T1w_2mm_GMthr0p3ero1mm = PipeJobPartial(name="T1w_2mm_SynthSeg_GM_thr0p3_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso2mm.maskGM_thr0p3,
                            output=session.subjectPaths.T1w.bids_processed.iso2mm.maskGM_thr0p3_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_2mm_GMthr0p3ero1mm.setDependencies(self.T1w_2mm_GMthr0p3)

        self.T1w_2mm_GMthr0p5 = PipeJobPartial(name="T1w_2mm_SynthSeg_GM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso2mm.maskGM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_2mm_GMthr0p5.setDependencies(self.T1w_2mm_synthsegGM)

        self.T1w_2mm_GMthr0p5ero1mm = PipeJobPartial(name="T1w_2mm_SynthSeg_GM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso2mm.maskGM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.iso2mm.maskGM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_2mm_GMthr0p5ero1mm.setDependencies(self.T1w_2mm_GMthr0p5)

        self.T1w_2mm_WMthr0p5 = PipeJobPartial(name="T1w_2mm_SynthSeg_WM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegWM,
                               output=session.subjectPaths.T1w.bids_processed.iso2mm.maskWM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_2mm_WMthr0p5.setDependencies(self.T1w_2mm_synthsegWM)

        self.T1w_2mm_WMthr0p5ero1mm = PipeJobPartial(name="T1w_2mm_SynthSeg_WM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso2mm.maskWM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.iso2mm.maskWM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_2mm_WMthr0p5ero1mm.setDependencies(self.T1w_2mm_WMthr0p5)

        self.T1w_2mm_CSFthr0p9 = PipeJobPartial(name="T1w_2mm_SynthSeg_CSF_thr0p9", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegCSF,
                               output=session.subjectPaths.T1w.bids_processed.iso2mm.maskCSF_thr0p9,
                               threshold=0.9) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_2mm_CSFthr0p9.setDependencies(self.T1w_2mm_synthsegCSF)

        self.T1w_2mm_CSFthr0p9ero1mm = PipeJobPartial(name="T1w_2mm_SynthSeg_CSF_thr0p9_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso2mm.maskCSF_thr0p9,
                            output=session.subjectPaths.T1w.bids_processed.iso2mm.maskCSF_thr0p9_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_2mm_CSFthr0p9ero1mm.setDependencies(self.T1w_2mm_CSFthr0p9)

        self.T1w_2mm_GMCorticalthr0p3 = PipeJobPartial(name="T1w_2mm_SynthSeg_GMCortical_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegGMCortical,
                               output=session.subjectPaths.T1w.bids_processed.iso2mm.maskGMCortical_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_2mm_GMCorticalthr0p3.setDependencies(self.T1w_2mm_synthsegGMCortical)

        self.T1w_2mm_GMCorticalthr0p3ero1mm = PipeJobPartial(name="T1w_2mm_SynthSeg_GMCortical_thr0p3_ero1mm",
                                                             job=SchedulerPartial(
                                                                 taskList=[Erode(
                                                                     infile=session.subjectPaths.T1w.bids_processed.iso2mm.maskGMCortical_thr0p3,
                                                                     output=session.subjectPaths.T1w.bids_processed.iso2mm.maskGMCortical_thr0p3_ero1mm,
                                                                     size=1) for session in
                                                                           self.sessions],
                                                                 cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_2mm_GMCorticalthr0p3ero1mm.setDependencies(self.T1w_2mm_GMCorticalthr0p3)

        self.T1w_2mm_GMCorticalthr0p5 = PipeJobPartial(name="T1w_2mm_SynthSeg_GMCortical_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegGMCortical,
                               output=session.subjectPaths.T1w.bids_processed.iso2mm.maskGMCortical_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_2mm_GMCorticalthr0p5.setDependencies(self.T1w_2mm_synthsegGMCortical)

        self.T1w_2mm_GMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_2mm_SynthSeg_GMCortical_thr0p5_ero1mm",
                                                             job=SchedulerPartial(
                                                                 taskList=[Erode(
                                                                     infile=session.subjectPaths.T1w.bids_processed.iso2mm.maskGMCortical_thr0p5,
                                                                     output=session.subjectPaths.T1w.bids_processed.iso2mm.maskGMCortical_thr0p5_ero1mm,
                                                                     size=1) for session in
                                                                           self.sessions],
                                                                 cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_2mm_GMCorticalthr0p5ero1mm.setDependencies(self.T1w_2mm_GMCorticalthr0p5)

        self.T1w_2mm_WMCorticalthr0p5 = PipeJobPartial(name="T1w_2mm_SynthSeg_WMCortical_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegWMCortical,
                               output=session.subjectPaths.T1w.bids_processed.iso2mm.maskWMCortical_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_2mm_WMCorticalthr0p5.setDependencies(self.T1w_2mm_synthsegWMCortical)

        self.T1w_2mm_WMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_2mm_SynthSeg_WMCortical_thr0p5_ero1mm",
                                                             job=SchedulerPartial(
                                                                 taskList=[Erode(
                                                                     infile=session.subjectPaths.T1w.bids_processed.iso2mm.maskWMCortical_thr0p5,
                                                                     output=session.subjectPaths.T1w.bids_processed.iso2mm.maskWMCortical_thr0p5_ero1mm,
                                                                     size=1) for session in
                                                                           self.sessions],
                                                                 cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_2mm_WMCorticalthr0p5ero1mm.setDependencies(self.T1w_2mm_WMCorticalthr0p5)

    def setup(self) -> bool:
        # Set external dependencies
        self.T1w_2mm_Native.setDependencies(self.moduleDependenciesDict["T1w_base"].N4biasCorrect)
        self.T1w_2mm_Brain.setDependencies(self.moduleDependenciesDict["T1w_base"].hdbet)
        self.T1w_2mm_BrainMask.setDependencies(self.moduleDependenciesDict["T1w_base"].hdbet)
        self.T1w_2mm_NativeToMNI.setDependencies(self.moduleDependenciesDict["T1w_base"].N4biasCorrect)
        self.T1w_2mm_synthsegGM.setDependencies(self.moduleDependenciesDict["T1w_SynthSeg"].GMmerge)
        self.T1w_2mm_synthsegWM.setDependencies(self.moduleDependenciesDict["T1w_SynthSeg"].WMmerge)
        self.T1w_2mm_synthsegCSF.setDependencies(self.moduleDependenciesDict["T1w_SynthSeg"].CSFmerge)
        self.T1w_2mm_synthsegGMCortical.setDependencies(self.moduleDependenciesDict["T1w_SynthSeg"].GMCorticalmerge)
        self.T1w_2mm_synthsegWMCortical.setDependencies(self.moduleDependenciesDict["T1w_SynthSeg"].WMCorticalmerge)

        self.addPipeJobs()
        return True


class T1w_3mm(ProcessingModule):
    requiredModalities = ["T1w"]
    moduleDependencies = ["T1w_base", "T1w_SynthSeg"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)

        self.T1w_3mm_Native = PipeJobPartial(name="T1w_3mm_baseimage", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                       reference=self.templates.mni152_3mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso3mm.baseimage,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_3mm_Brain = PipeJobPartial(name="T1w_3mm_brain", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.hdbet_brain,
                                       reference=self.templates.mni152_3mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso3mm.brain,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_3mm_BrainMask = PipeJobPartial(name="T1w_3mm_brainMask", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                                       reference=self.templates.mni152_3mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso3mm.brainmask,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        # Register to MNI
        self.T1w_3mm_NativeToMNI = PipeJobPartial(name="T1w_3mm_NativeToMNI", job=SchedulerPartial(
            taskList=[AntsRegistrationSyN(fixed=self.templates.mni152_3mm,
                                          moving=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                          outprefix=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_prefix,
                                          expectedOutFiles=[session.subjectPaths.T1w.bids_processed.iso3mm.MNI_toMNI,
                                                            session.subjectPaths.T1w.bids_processed.iso3mm.MNI_InverseWarped,
                                                            session.subjectPaths.T1w.bids_processed.iso3mm.MNI_0GenericAffine,
                                                            session.subjectPaths.T1w.bids_processed.iso3mm.MNI_1Warp,
                                                            session.subjectPaths.T1w.bids_processed.iso3mm.MNI_1InverseWarp],
                                          ncores=2, dim=3, type="s") for session in
                      self.sessions],  # something
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=2, minimumMemPerNode=4),
                                                  env=self.envs.envANTS)

        self.T1w_3mm_qc_vis_MNI = PipeJobPartial(name="T1w_3mm_QC_slices_MNI", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_toMNI,
                            mask=self.templates.mni152_brain_mask_3mm,
                            image=session.subjectPaths.T1w.meta_QC.MNI_3mm_slices, contrastAdjustment=False,
                            outline=True, transparency=True) for session in
                      self.sessions]), env=self.envs.envQCVis)
        self.T1w_3mm_qc_vis_MNI.setDependencies(self.T1w_3mm_NativeToMNI)

        # SynthSeg Masks
        self.T1w_3mm_synthsegGM = PipeJobPartial(name="T1w_3mm_synthsegGM", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                                       reference=self.templates.mni152_3mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegGM,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_3mm_synthsegWM = PipeJobPartial(name="T1w_3mm_synthsegWM", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegWM,
                                       reference=self.templates.mni152_3mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegWM,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_3mm_synthsegCSF = PipeJobPartial(name="T1w_3mm_synthsegCSF", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegCSF,
                                       reference=self.templates.mni152_3mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegCSF,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_3mm_synthsegGMCortical = PipeJobPartial(name="T1w_3mm_synthsegGMCortical", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegGMCortical,
                                       reference=self.templates.mni152_3mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegGMCortical,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_3mm_synthsegWMCortical = PipeJobPartial(name="T1w_3mm_synthsegWMCortical", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegWMCortical,
                                       reference=self.templates.mni152_3mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegWMCortical,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        # Calculate masks from probabilities maps
        self.T1w_3mm_GMthr0p3 = PipeJobPartial(name="T1w_3mm_SynthSeg_GM_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso3mm.maskGM_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_3mm_GMthr0p3.setDependencies(self.T1w_3mm_synthsegGM)

        self.T1w_3mm_GMthr0p3ero1mm = PipeJobPartial(name="T1w_3mm_SynthSeg_GM_thr0p3_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso3mm.maskGM_thr0p3,
                            output=session.subjectPaths.T1w.bids_processed.iso3mm.maskGM_thr0p3_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_3mm_GMthr0p3ero1mm.setDependencies(self.T1w_3mm_GMthr0p3)

        self.T1w_3mm_GMthr0p5 = PipeJobPartial(name="T1w_3mm_SynthSeg_GM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso3mm.maskGM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_3mm_GMthr0p5.setDependencies(self.T1w_3mm_synthsegGM)

        self.T1w_3mm_GMthr0p5ero1mm = PipeJobPartial(name="T1w_3mm_SynthSeg_GM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso3mm.maskGM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.iso3mm.maskGM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_3mm_GMthr0p5ero1mm.setDependencies(self.T1w_3mm_GMthr0p5)

        self.T1w_3mm_WMthr0p5 = PipeJobPartial(name="T1w_3mm_SynthSeg_WM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegWM,
                               output=session.subjectPaths.T1w.bids_processed.iso3mm.maskWM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_3mm_WMthr0p5.setDependencies(self.T1w_3mm_synthsegWM)

        self.T1w_3mm_WMthr0p5ero1mm = PipeJobPartial(name="T1w_3mm_SynthSeg_WM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso3mm.maskWM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.iso3mm.maskWM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_3mm_WMthr0p5ero1mm.setDependencies(self.T1w_3mm_WMthr0p5)

        self.T1w_3mm_CSFthr0p9 = PipeJobPartial(name="T1w_3mm_SynthSeg_CSF_thr0p9", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegCSF,
                               output=session.subjectPaths.T1w.bids_processed.iso3mm.maskCSF_thr0p9,
                               threshold=0.9) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_3mm_CSFthr0p9.setDependencies(self.T1w_3mm_synthsegCSF)

        self.T1w_3mm_CSFthr0p9ero1mm = PipeJobPartial(name="T1w_3mm_SynthSeg_CSF_thr0p9_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso3mm.maskCSF_thr0p9,
                            output=session.subjectPaths.T1w.bids_processed.iso3mm.maskCSF_thr0p9_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_3mm_CSFthr0p9ero1mm.setDependencies(self.T1w_3mm_CSFthr0p9)

        self.T1w_3mm_GMCorticalthr0p3 = PipeJobPartial(name="T1w_3mm_SynthSeg_GMCortical_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegGMCortical,
                               output=session.subjectPaths.T1w.bids_processed.iso3mm.maskGMCortical_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_3mm_GMCorticalthr0p3.setDependencies(self.T1w_3mm_synthsegGMCortical)

        self.T1w_3mm_GMCorticalthr0p3ero1mm = PipeJobPartial(name="T1w_3mm_SynthSeg_GMCortical_thr0p3_ero1mm",
                                                             job=SchedulerPartial(
                                                                 taskList=[Erode(
                                                                     infile=session.subjectPaths.T1w.bids_processed.iso3mm.maskGMCortical_thr0p3,
                                                                     output=session.subjectPaths.T1w.bids_processed.iso3mm.maskGMCortical_thr0p3_ero1mm,
                                                                     size=1) for session in
                                                                           self.sessions],
                                                                 cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_3mm_GMCorticalthr0p3ero1mm.setDependencies(self.T1w_3mm_GMCorticalthr0p3)

        self.T1w_3mm_GMCorticalthr0p5 = PipeJobPartial(name="T1w_3mm_SynthSeg_GMCortical_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegGMCortical,
                               output=session.subjectPaths.T1w.bids_processed.iso3mm.maskGMCortical_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_3mm_GMCorticalthr0p5.setDependencies(self.T1w_3mm_synthsegGMCortical)

        self.T1w_3mm_GMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_3mm_SynthSeg_GMCortical_thr0p5_ero1mm",
                                                             job=SchedulerPartial(
                                                                 taskList=[Erode(
                                                                     infile=session.subjectPaths.T1w.bids_processed.iso3mm.maskGMCortical_thr0p5,
                                                                     output=session.subjectPaths.T1w.bids_processed.iso3mm.maskGMCortical_thr0p5_ero1mm,
                                                                     size=1) for session in
                                                                           self.sessions],
                                                                 cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_3mm_GMCorticalthr0p5ero1mm.setDependencies(self.T1w_3mm_GMCorticalthr0p5)

        self.T1w_3mm_WMCorticalthr0p5 = PipeJobPartial(name="T1w_3mm_SynthSeg_WMCortical_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegWMCortical,
                               output=session.subjectPaths.T1w.bids_processed.iso3mm.maskWMCortical_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_3mm_WMCorticalthr0p5.setDependencies(self.T1w_3mm_synthsegWMCortical)

        self.T1w_3mm_WMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_3mm_SynthSeg_WMCortical_thr0p5_ero1mm",
                                                             job=SchedulerPartial(
                                                                 taskList=[Erode(
                                                                     infile=session.subjectPaths.T1w.bids_processed.iso3mm.maskWMCortical_thr0p5,
                                                                     output=session.subjectPaths.T1w.bids_processed.iso3mm.maskWMCortical_thr0p5_ero1mm,
                                                                     size=1) for session in
                                                                           self.sessions],
                                                                 cpusPerTask=1), env=self.envs.envFSL)
        self.T1w_3mm_WMCorticalthr0p5ero1mm.setDependencies(self.T1w_3mm_WMCorticalthr0p5)

    def setup(self) -> bool:
        # Set external dependencies
        self.T1w_3mm_Native.setDependencies(self.moduleDependenciesDict["T1w_base"].N4biasCorrect)
        self.T1w_3mm_Brain.setDependencies(self.moduleDependenciesDict["T1w_base"].hdbet)
        self.T1w_3mm_BrainMask.setDependencies(self.moduleDependenciesDict["T1w_base"].hdbet)
        self.T1w_3mm_NativeToMNI.setDependencies(self.moduleDependenciesDict["T1w_base"].N4biasCorrect)
        self.T1w_3mm_synthsegGM.setDependencies(self.moduleDependenciesDict["T1w_SynthSeg"].GMmerge)
        self.T1w_3mm_synthsegWM.setDependencies(self.moduleDependenciesDict["T1w_SynthSeg"].WMmerge)
        self.T1w_3mm_synthsegCSF.setDependencies(self.moduleDependenciesDict["T1w_SynthSeg"].CSFmerge)
        self.T1w_3mm_synthsegGMCortical.setDependencies(self.moduleDependenciesDict["T1w_SynthSeg"].GMCorticalmerge)
        self.T1w_3mm_synthsegWMCortical.setDependencies(self.moduleDependenciesDict["T1w_SynthSeg"].WMCorticalmerge)

        self.addPipeJobs()
        return True
