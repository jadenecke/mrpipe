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


class T1w_base(ProcessingModule):
    requiredModalities = ["T1w"]

    def setup(self) -> bool:
        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.args.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)

        # Step 1: N4 Bias corrections
        N4biasCorrect = PipeJobPartial(name="T1w_base_N4biasCorrect", job=SchedulerPartial(
            taskList=[N4BiasFieldCorrect(infile=session.subjectPaths.T1w.bids.T1w,
                                         outfile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected) for session in
                      self.sessions],  # something
            cpusPerTask=2, cpusTotal=self.args.ncores,
            memPerCPU=2, minimumMemPerNode=4),
                                       env=self.envs.envANTS)
        self.addPipeJob(N4biasCorrect)

        # Step 2: Brain extraction using hd-bet
        hdbet = PipeJobPartial(name="T1w_base_hdbet", job=SchedulerPartial(
            taskList=[HDBET(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                            brain=session.subjectPaths.T1w.bids_processed.hdbet_brain,
                            mask=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                            useGPU=self.args.ngpus > 0) for session in
                      self.sessions],
            ngpus=self.args.ngpus), env=self.envs.envHDBET)
        hdbet.setDependencies(N4biasCorrect)
        self.addPipeJob(hdbet)

        # Step 3: Synthseg Segmentation
        synthseg = PipeJobPartial(name="T1w_base_SynthSeg", job=SchedulerPartial(
            taskList=[SynthSeg(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                               posterior=session.subjectPaths.T1w.bids_processed.synthsegPosterior,
                               posteriorProb=session.subjectPaths.T1w.bids_processed.synthsegPosteriorProbabilities,
                               volumes=session.subjectPaths.T1w.bids_statistics.synthsegVolumes,
                               resample=session.subjectPaths.T1w.bids_processed.synthsegResample,
                               qc=session.subjectPaths.T1w.meta_QC.synthsegQC,
                               useGPU=self.args.ngpus > 0, ncores=2) for session in
                      self.sessions],
            ngpus=self.args.ngpus, memPerCPU=8, cpusPerTask=2, minimumMemPerNode=16), env=self.envs.envSynthSeg)
        synthseg.setDependencies(N4biasCorrect)
        self.addPipeJob(synthseg)

        synthsegSplit = PipeJobPartial(name="T1w_base_SynthSegSplit", job=SchedulerPartial(
            taskList=[Split4D(infile=session.subjectPaths.T1w.bids_processed.synthsegPosteriorProbabilities,
                              stem=session.subjectPaths.T1w.bids_processed.synthsegSplitStem,
                              outputNames=[
                                  session.subjectPaths.T1w.bids_processed.synthsegPosteriorPathNames.getAllPaths()]) for
                      session in
                      self.sessions],
            memPerCPU=2, cpusPerTask=2, minimumMemPerNode=8), env=self.envs.envFSL)
        synthsegSplit.setDependencies(synthseg)
        self.addPipeJob(synthsegSplit)

        # Step 4: Create GM/WM/CSF Maps, Mask and eroded versions
        GMmerge = PipeJobPartial(name="T1w_base_GMmerge", job=SchedulerPartial(
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
        GMmerge.setDependencies(synthsegSplit)
        self.addPipeJob(GMmerge)

        WMmerge = PipeJobPartial(name="T1w_base_WMmerge", job=SchedulerPartial(
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
        WMmerge.setDependencies(synthsegSplit)
        self.addPipeJob(WMmerge)

        CSFmerge = PipeJobPartial(name="T1w_base_CSFmerge", job=SchedulerPartial(
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
        CSFmerge.setDependencies(synthsegSplit)
        self.addPipeJob(CSFmerge)

        GMthr0p3 = PipeJobPartial(name="T1w_base_GM_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.maskGM_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        GMthr0p3.setDependencies(GMmerge)
        self.addPipeJob(GMthr0p3)

        GMthr0p3ero1mm = PipeJobPartial(name="T1w_base_GM_thr0p3_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.maskGM_thr0p3_ero1mm,
                               size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        GMthr0p3ero1mm.setDependencies(GMthr0p3)
        self.addPipeJob(GMthr0p3ero1mm)

        GMthr0p5 = PipeJobPartial(name="T1w_base_GM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.maskGM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        GMthr0p5.setDependencies(GMmerge)
        self.addPipeJob(GMthr0p5)

        GMthr0p5ero1mm = PipeJobPartial(name="T1w_base_GM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.maskGM_thr0p5_ero1mm,
                               size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        GMthr0p5ero1mm.setDependencies(GMthr0p5)
        self.addPipeJob(GMthr0p5ero1mm)

        WMthr0p5 = PipeJobPartial(name="T1w_base_WM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegWM,
                               output=session.subjectPaths.T1w.bids_processed.maskWM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        WMthr0p5.setDependencies(WMmerge)
        self.addPipeJob(WMthr0p5)

        WMthr0p5ero1mm = PipeJobPartial(name="T1w_base_WM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                            output=session.subjectPaths.T1w.bids_processed.maskWM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        WMthr0p5ero1mm.setDependencies(WMthr0p5)
        self.addPipeJob(WMthr0p5ero1mm)

        CSFthr0p9 = PipeJobPartial(name="T1w_base_CSF_thr0p9", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegWM,
                               output=session.subjectPaths.T1w.bids_processed.maskCSF_thr0p9,
                               threshold=0.9) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        CSFthr0p9.setDependencies(CSFmerge)
        self.addPipeJob(CSFthr0p9)

        CSFthr0p9ero1mm = PipeJobPartial(name="T1w_base_CSF_thr0p9_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                            output=session.subjectPaths.T1w.bids_processed.maskCSF_thr0p9_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)
        CSFthr0p9ero1mm.setDependencies(CSFthr0p9)
        self.addPipeJob(CSFthr0p9ero1mm)







        ########## QC ###########
        qc_vis_hdbet = PipeJobPartial(name="T1w_base_QC_slices_hdbet", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                            mask=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                            image=session.subjectPaths.T1w.meta_QC.hdbet_slices) for session in
                      self.sessions],
            ngpus=self.args.ngpus), env=self.envs.envQCVis)
        qc_vis_hdbet.setDependencies([N4biasCorrect, hdbet])
        self.addPipeJob(qc_vis_hdbet)

        qc_vis_GMthr0p3 = PipeJobPartial(name="T1w_base_QC_slices_GMthr0p3", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.synthsegPosterior,
                            mask=session.subjectPaths.T1w.bids_processed.maskGM_thr0p3,
                            image=session.subjectPaths.T1w.meta_QC.GMthr0p3_slices) for session in
                      self.sessions],
            ngpus=self.args.ngpus), env=self.envs.envQCVis)
        qc_vis_GMthr0p3.setDependencies(GMthr0p3)
        self.addPipeJob(qc_vis_GMthr0p3)

        qc_vis_GMthr0p5 = PipeJobPartial(name="T1w_base_QC_slices_GMthr0p5", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.synthsegPosterior,
                            mask=session.subjectPaths.T1w.bids_processed.maskGM_thr0p5,
                            image=session.subjectPaths.T1w.meta_QC.GMthr0p5_slices) for session in
                      self.sessions],
            ngpus=self.args.ngpus), env=self.envs.envQCVis)
        qc_vis_GMthr0p5.setDependencies(GMthr0p5)
        self.addPipeJob(qc_vis_GMthr0p5)

        qc_vis_WMthr0p5 = PipeJobPartial(name="T1w_base_QC_slices_WM", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.synthsegPosterior,
                            mask=session.subjectPaths.T1w.bids_processed.maskWM_thr0p5,
                            image=session.subjectPaths.T1w.meta_QC.WMthr0p5_slices) for session in
                      self.sessions],
            ngpus=self.args.ngpus), env=self.envs.envQCVis)
        qc_vis_WMthr0p5.setDependencies(WMthr0p5)
        self.addPipeJob(qc_vis_WMthr0p5)

        qc_vis_CSFthr0p9 = PipeJobPartial(name="T1w_base_QC_slices_CSF", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.synthsegPosterior,
                            mask=session.subjectPaths.T1w.bids_processed.maskCSF_thr0p9,
                            image=session.subjectPaths.T1w.meta_QC.CSFthr0p9_slices) for session in
                      self.sessions],
            ngpus=self.args.ngpus), env=self.envs.envQCVis)
        qc_vis_CSFthr0p9.setDependencies(CSFthr0p9)
        self.addPipeJob(qc_vis_CSFthr0p9)

        qc_vis_synthseg = PipeJobPartial(name="T1w_base_QC_slices_synthseg", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.synthsegResample,
                            mask=session.subjectPaths.T1w.bids_processed.synthsegPosterior,
                            image=session.subjectPaths.T1w.meta_QC.synthseg_slices,
                            tempDir=self.args.scratch) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envQCVis)
        qc_vis_synthseg.setDependencies([synthseg])
        self.addPipeJob(qc_vis_synthseg)

        return True
