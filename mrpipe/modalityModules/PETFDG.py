from mrpipe.modalityModules.ProcessingModule import ProcessingModule
from functools import partial
from mrpipe.schedueler.PipeJob import PipeJob
from mrpipe.schedueler import Slurm
from mrpipe.Toolboxes.standalone.QCVis import QCVis
from mrpipe.Toolboxes.ANTSTools.AntsRegistrationSyN import AntsRegistrationSyN
from mrpipe.Toolboxes.ANTSTools.AntsApplyTransform import AntsApplyTransforms
from mrpipe.Toolboxes.standalone.cp import CP
from mrpipe.Toolboxes.FSL.FSLMaths import FSLMaths
from mrpipe.Toolboxes.FSL.FSLStats import FSLStatsToFile
from mrpipe.Toolboxes.standalone.RecenterToCOM import RecenterToCOM
from mrpipe.Toolboxes.standalone.ExtractAtlasValues import ExtractAtlasValues
from mrpipe.Toolboxes.standalone.MARS_Brainstem import MARS_Brainstem
from mrpipe.Toolboxes.standalone.SelectAtlasROIs import SelectAtlasROIs

class PETFDG_base_withT1w(ProcessingModule):
    requiredModalities = ["T1w", "pet_fdg"]
    moduleDependencies = ["T1w_1mm"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4, partition=self.inputArgs.partition)

        # self.PETFDG_base_recenter = PipeJobPartial(name="PETFDG_base_recenterToCom", job=SchedulerPartial(
        #     taskList=[RecenterToCOM(infile=session.subjectPaths.pet_fdg.bids.PETFDG,
        #                             outfile=session.subjectPaths.pet_fdg.bids_processed.PETFDG_recentered
        #                             ) for session in
        #               self.sessions]),
        #                                env=self.envs.envMRPipe)

        self.PETFDG_base_recenter = PipeJobPartial(name="PETFDG_base_recenterToCom", job=SchedulerPartial(
            taskList=[CP(infile=session.subjectPaths.pet_fdg.bids.PETFDG.imagePath,
                                    outfile=session.subjectPaths.pet_fdg.bids_processed.PETFDG_recentered
                                    ) for session in
                      self.sessions]),
                                                    env=self.envs.envMRPipe)

        self.PETFDG_base_NativeToT1w = PipeJobPartial(name="PETFDG_base_NativeToT1w", job=SchedulerPartial(
            taskList=[AntsRegistrationSyN(fixed=session.subjectPaths.T1w.bids_processed.iso1mm.baseimage,
                                          moving=session.subjectPaths.pet_fdg.bids_processed.PETFDG_recentered,
                                          outprefix=session.subjectPaths.pet_fdg.bids_processed.toT1w_prefix,
                                          expectedOutFiles=[session.subjectPaths.pet_fdg.bids_processed.toT1w_toT1w,
                                                            session.subjectPaths.pet_fdg.bids_processed.toT1w_0GenericAffine],
                                          ncores=2, dim=3, type="r") for session in self.sessions]),
                                                  env=self.envs.envANTS)

        self.PETFDG_base_MARSBrainstem = PipeJobPartial(name="PETFDG_base_MARSBrainstem", job=SchedulerPartial(
            taskList=[MARS_Brainstem(t1=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                     brainstemSegOut=session.subjectPaths.pet_fdg.bids_processed.brainstemSegmentation_inT1w,
                                     MarsBrainstemSIF=self.libpaths.MarsBrainstemSIF) for session in
                      self.sessions], memPerCPU=2, cpusPerTask=12, minimumMemPerNode=24, ngpus=self.inputArgs.ngpus), env=self.envs.envCuda)

        self.PETFDG_base_selectPons = PipeJobPartial(name="PETFDG_base_selectPons", job=SchedulerPartial(
            taskList=[SelectAtlasROIs(infile=session.subjectPaths.pet_fdg.bids_processed.brainstemSegmentation_inT1w,
                                      outfile=session.subjectPaths.pet_fdg.bids_processed.refMask_inT1w,
                                      ROIs=[2],
                                      binarize=True) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.PETFDG_base_fromT1w_PONS = PipeJobPartial(name="PETFDG_base_fromT1w_PONS", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.pet_fdg.bids_processed.refMask_inT1w,
                                          output=session.subjectPaths.pet_fdg.bids_processed.refMask,
                                          reference=session.subjectPaths.pet_fdg.bids_processed.PETFDG_recentered,
                                          transforms=[session.subjectPaths.pet_fdg.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.PETFDG_base_fromT1w_schaefer200_17Net = PipeJobPartial(name="PETFDG_base_fromT1w_schaefer200_17Net", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.Schaefer2018_200Parcels_17Networks_order_FSLMNI152_1mm_gmMasked,
                                          output=session.subjectPaths.pet_fdg.bids_processed.atlas_schaefer200_17Net,
                                          reference=session.subjectPaths.pet_fdg.bids_processed.PETFDG_recentered,
                                          transforms=[session.subjectPaths.pet_fdg.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.PETFDG_base_fromT1w_Mindboggle101 = PipeJobPartial(name="PETFDG_base_fromT1w_Mindboggle101", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.OASIS_TRT_20_jointfusion_DKT31_CMA_labels_in_MNI152_v2_gmMasked,
                                          output=session.subjectPaths.pet_fdg.bids_processed.atlas_mindboggle,
                                          reference=session.subjectPaths.pet_fdg.bids_processed.PETFDG_recentered,
                                          transforms=[session.subjectPaths.pet_fdg.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.PETFDG_base_qc_vis_toT1w = PipeJobPartial(name="PETFDG_base_slices_toT1w", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.pet_fdg.bids_processed.toT1w_toT1w,
                            mask=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                            image=session.subjectPaths.pet_fdg.meta_QC.ToT1w_native_slices, contrastAdjustment=False,
                            outline=True, transparency=True, zoom=1) for session in
                      self.sessions]), env=self.envs.envQCVis)

        self.PETFDG_base_refvol_mean = PipeJobPartial(name="PETFDG_base_RefVol_mean", job=SchedulerPartial(
            taskList=[FSLStatsToFile(infile=session.subjectPaths.pet_fdg.bids_processed.PETFDG_recentered,
                                     output=session.subjectPaths.pet_fdg.bids_processed.reMaskVal,
                                     mask=session.subjectPaths.pet_fdg.bids_processed.refMask,
                                     options=["-n", "-k", "-M"]) for session in
                      self.sessions]), env=self.envs.envFSL)

        self.PETFDG_base_suvr = PipeJobPartial(name="PETFDG_base_SUVR", job=SchedulerPartial(
            taskList=[FSLMaths(infiles=[session.subjectPaths.pet_fdg.bids_processed.PETFDG_recentered,
                                        session.subjectPaths.pet_fdg.bids_processed.reMaskVal],
                                output=session.subjectPaths.pet_fdg.bids_processed.SUVR,
                                mathString="{} -div $(cat {})") for session in
                      self.sessions]), env=self.envs.envFSL)

        self.PETFDG_base_suvr_statsSchaefer200_17 = PipeJobPartial(name="PETFDG_base_SUVR_statsSchaefer200_17", job=SchedulerPartial(
            taskList=[ExtractAtlasValues(infile=session.subjectPaths.pet_fdg.bids_processed.SUVR,
                                         atlas=session.subjectPaths.pet_fdg.bids_processed.atlas_schaefer200_17Net,
                                         outfile=session.subjectPaths.pet_fdg.bids_statistics.SUVR_PONS_Schaefer200_17Net_mean,
                                         func="mean") for session in
                      self.sessions]), env=self.envs.envR)

        self.PETFDG_base_suvr_statsMindboggle = PipeJobPartial(name="PETFDG_base_SUVR_statsMindboggle", job=SchedulerPartial(
            taskList=[ExtractAtlasValues(infile=session.subjectPaths.pet_fdg.bids_processed.SUVR,
                                         atlas=session.subjectPaths.pet_fdg.bids_processed.atlas_mindboggle,
                                         outfile=session.subjectPaths.pet_fdg.bids_statistics.SUVR_PONS_Mindboggle101_mean,
                                         func="mean") for session in
                      self.sessions]), env=self.envs.envR)



    def setup(self) -> bool:
        self.addPipeJobs()
        return True
