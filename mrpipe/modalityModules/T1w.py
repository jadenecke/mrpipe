from mrpipe.modalityModules.ProcessingModule import ProcessingModule
from mrpipe.schedueler.PipeJob import PipeJob
from mrpipe.schedueler import Slurm
from mrpipe.Toolboxes.ANTSTools.N4BiasFieldCorrect import N4BiasFieldCorrect
from mrpipe.Toolboxes.standalone.hdbet import HDBET
from mrpipe.Toolboxes.standalone.synthseg import SynthSeg
from mrpipe.Toolboxes.standalone.qcVis import QCVis


class T1w_base(ProcessingModule):
    requiredModalities = ["T1w"]

    def setup(self) -> bool:
        # Step 1: N4 Bias corrections
        N4biasCorrect = PipeJob(name="T1w_base_N4biasCorrect", basepaths=self.basepaths, job=Slurm.Scheduler(
            taskList=[N4BiasFieldCorrect(infile=session.subjectPaths.T1w.bids.T1w,
                                         outfile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected) for session in
                      self.sessions],  # something
            cpusPerTask=2, cpusTotal=self.args.ncores,
            memPerCPU=2, minimumMemPerNode=4),
                                env=self.envs.envANTS, moduleName=self.moduleName)
        self.addPipeJob(N4biasCorrect)

        # Step 2: Brain extraction using hd-bet
        hdbet = PipeJob(name="T1w_base_hdbet", basepaths=self.basepaths, job=Slurm.Scheduler(
            taskList=[HDBET(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                            brain=session.subjectPaths.T1w.bids_processed.hdbet_brain,
                            mask=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                            useGPU=self.args.ngpus > 0) for session in
                      self.sessions],
            cpusPerTask=2, cpusTotal=self.args.ncores,
            memPerCPU=2, minimumMemPerNode=4, ngpus=self.args.ngpus),
                        env=self.envs.envHDBET, moduleName=self.moduleName)
        hdbet.setDependencies(N4biasCorrect)
        self.addPipeJob(hdbet)

        # Step 3: Synthseg Segmentation
        synthseg = PipeJob(name="T1w_base_SynthSeg", basepaths=self.basepaths, job=Slurm.Scheduler(
            taskList=[SynthSeg(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                               posterior=session.subjectPaths.T1w.bids_processed.synthsegPosterior,
                               posteriorProb=session.subjectPaths.T1w.bids_processed.synthsegPosteriorProbabilities,
                               volumes=session.subjectPaths.T1w.bids_statistics.synthsegVolumes,
                               resample=session.subjectPaths.T1w.bids_processed.synthsegResample,
                               qc=session.subjectPaths.T1w.meta_QC.synthsegQC,
                               useGPU=self.args.ngpus > 0, ncores=2) for session in
                      self.sessions],
            cpusPerTask=2, cpusTotal=self.args.ncores,
            memPerCPU=2, minimumMemPerNode=4, ngpus=self.args.ngpus),
                           env=self.envs.envSynthSeg, moduleName=self.moduleName)
        synthseg.setDependencies(N4biasCorrect)
        self.addPipeJob(synthseg)

        ########## QC ###########
        # Step 3: Synthseg Segmentation
        qc_vis_hdbet = PipeJob(name="T1w_base_QC_slices_hdbet", basepaths=self.basepaths, job=Slurm.Scheduler(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                            mask=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                            image=session.subjectPaths.T1w.meta_QC.hdbet_slices) for session in
                      self.sessions],
            cpusPerTask=1, cpusTotal=self.args.ncores,
            memPerCPU=2, minimumMemPerNode=4, ngpus=self.args.ngpus),
                               env=self.envs.envQCVis, moduleName=self.moduleName)
        qc_vis_hdbet.setDependencies([N4biasCorrect, hdbet])
        self.addPipeJob(qc_vis_hdbet)

        qc_vis_synthseg = PipeJob(name="T1w_base_QC_slices_synthseg", basepaths=self.basepaths, job=Slurm.Scheduler(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.synthsegResample,
                            mask=session.subjectPaths.T1w.bids_processed.synthsegPosterior,
                            image=session.subjectPaths.T1w.meta_QC.synthseg_slices,
                            tempDir=self.args.scratch) for session in
                      self.sessions],
            cpusPerTask=1, cpusTotal=self.args.ncores,
            memPerCPU=2, minimumMemPerNode=4, ngpus=self.args.ngpus),
                                  env=self.envs.envQCVis, moduleName=self.moduleName)
        qc_vis_synthseg.setDependencies([synthseg])
        self.addPipeJob(qc_vis_synthseg)

        return True
