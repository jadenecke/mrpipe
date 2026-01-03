from mrpipe.modalityModules.ProcessingModule import ProcessingModule
from functools import partial
from mrpipe.schedueler.PipeJob import PipeJob
from mrpipe.schedueler import Slurm
from mrpipe.Toolboxes.ANTSTools.N4BiasFieldCorrect import N4BiasFieldCorrect
from mrpipe.Toolboxes.standalone.QCVis import QCVis
from mrpipe.Toolboxes.ANTSTools.AntsRegistrationSyN import AntsRegistrationSyN
from mrpipe.Toolboxes.ANTSTools.AntsApplyTransform import AntsApplyTransforms
from mrpipe.Toolboxes.standalone.cp import CP
from mrpipe.Toolboxes.standalone.lesionSegmentationToolAI import LSTAI
from mrpipe.Toolboxes.FSL.FSLMaths import FSLMaths
from mrpipe.Toolboxes.FSL.FSLStats import FSLStatsToFile
from mrpipe.Toolboxes.standalone.RecenterToCOM import RecenterToCOM
from mrpipe.Toolboxes.standalone.ExtractAtlasValues import ExtractAtlasValues
from mrpipe.Toolboxes.standalone.SUVRToCentiloid import SUVRToCentiloid
from mrpipe.Toolboxes.standalone.CAT12_WarpToTemplate import CAT12_WarpToTemplate
from mrpipe.Toolboxes.standalone.CAT12_WarpToTemplate import ValidCat12Interps

class PETNAV4694_base_withT1w(ProcessingModule):
    requiredModalities = ["T1w", "pet_nav4694"]
    moduleDependencies = ["T1w_1mm"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4, partition=self.inputArgs.partition)

        # self.petnav4694_base_recenter = PipeJobPartial(name="PETNAV4694_base_recenterToCom", job=SchedulerPartial(
        #     taskList=[RecenterToCOM(infile=session.subjectPaths.pet_nav4694.bids.PETNAV4694,
        #                             outfile=session.subjectPaths.pet_nav4694.bids_processed.PETNAV4694_recentered
        #                             ) for session in
        #               self.sessions]),
        #                                env=self.envs.envMRPipe)

        self.petnav4694_base_recenter = PipeJobPartial(name="PETNAV4694_base_recenterToCom", job=SchedulerPartial(
            taskList=[CP(infile=session.subjectPaths.pet_nav4694.bids.PETNAV4694.imagePath,
                                    outfile=session.subjectPaths.pet_nav4694.bids_processed.PETNAV4694_recentered
                                    ) for session in
                      self.sessions]),
                                                       env=self.envs.envMRPipe)

        self.petnav4694_base_NativeToT1w = PipeJobPartial(name="PETNAV4694_base_NativeToT1w", job=SchedulerPartial(
            taskList=[AntsRegistrationSyN(fixed=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                          moving=session.subjectPaths.pet_nav4694.bids_processed.PETNAV4694_recentered,
                                          outprefix=session.subjectPaths.pet_nav4694.bids_processed.toT1w_prefix,
                                          expectedOutFiles=[session.subjectPaths.pet_nav4694.bids_processed.toT1w_toT1w,
                                                            session.subjectPaths.pet_nav4694.bids_processed.toT1w_0GenericAffine],
                                          ncores=2, dim=3, type="r") for session in self.sessions]),
                                                  env=self.envs.envANTS)

        self.petnav4694_base_fromMNI_WHOLECER = PipeJobPartial(name="PETNAV4694_base_fromMNI_WHOLECER", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=self.templates.cerebellum_whole_eroded,
                                          tempdir=self.basepaths.scratch,
                                           outfile=session.subjectPaths.pet_nav4694.bids_processed.refMask_inT1w,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_InverseWarp,
                                           interp=ValidCat12Interps.nearestNeighbor,
                                           voxelsize=1) for session in self.sessions], cpusPerTask=3), env=self.envs.envSPM12)

        self.petnav4694_base_fromT1w_WHOLECER = PipeJobPartial(name="PETNAV4694_base_fromT1w_WHOLECER", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.pet_nav4694.bids_processed.refMask_inT1w,
                                          output=session.subjectPaths.pet_nav4694.bids_processed.refMask,
                                          reference=session.subjectPaths.pet_nav4694.bids_processed.PETNAV4694_recentered,
                                          transforms=[session.subjectPaths.pet_nav4694.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.petnav4694_base_fromT1w_schaefer200_17Net = PipeJobPartial(name="PETNAV4694_base_fromT1w_schaefer200_17Net", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.Schaefer2018_200Parcels_17Networks_order_FSLMNI152_gmMasked,
                                          output=session.subjectPaths.pet_nav4694.bids_processed.atlas_schaefer200_17Net,
                                          reference=session.subjectPaths.pet_nav4694.bids_processed.PETNAV4694_recentered,
                                          transforms=[session.subjectPaths.pet_nav4694.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.petnav4694_base_fromT1w_Mindboggle101 = PipeJobPartial(name="PETNAV4694_base_fromT1w_Mindboggle101", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.OASIS_TRT_20_jointfusion_DKT31_CMA_labels_in_MNI152_v2_gmMasked,
                                          output=session.subjectPaths.pet_nav4694.bids_processed.atlas_mindboggle,
                                          reference=session.subjectPaths.pet_nav4694.bids_processed.PETNAV4694_recentered,
                                          transforms=[session.subjectPaths.pet_nav4694.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.petnav4694_base_qc_vis_toT1w = PipeJobPartial(name="PETNAV4694_base_slices_toT1w", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.pet_nav4694.bids_processed.toT1w_toT1w,
                            mask=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                            image=session.subjectPaths.pet_nav4694.meta_QC.ToT1w_native_slices, contrastAdjustment=False,
                            outline=True, transparency=True, zoom=1) for session in
                      self.sessions]), env=self.envs.envQCVis)

        self.petnav4694_base_qc_vis_RefRegion = PipeJobPartial(name="PETNAV4694_base_slices_RefRegion", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.pet_nav4694.bids_processed.PETNAV4694_recentered,
                            mask=session.subjectPaths.pet_nav4694.bids_processed.refMask,
                            image=session.subjectPaths.pet_nav4694.meta_QC.refMask_native_slices, contrastAdjustment=True,
                            outline=True, transparency=True, zoom=1) for session in
                      self.sessions]), env=self.envs.envQCVis)

        self.petnav4694_base_refvol_mean = PipeJobPartial(name="PETNAV4694_base_RefVol_mean", job=SchedulerPartial(
            taskList=[FSLStatsToFile(infile=session.subjectPaths.pet_nav4694.bids_processed.PETNAV4694_recentered,
                                     output=session.subjectPaths.pet_nav4694.bids_processed.reMaskVal,
                                     mask=session.subjectPaths.pet_nav4694.bids_processed.refMask,
                                     options=["-n", "-k", "-M"]) for session in
                      self.sessions]), env=self.envs.envFSL)

        self.petnav4694_base_suvr = PipeJobPartial(name="PETNAV4694_base_SUVR", job=SchedulerPartial(
            taskList=[FSLMaths(infiles=[session.subjectPaths.pet_nav4694.bids_processed.PETNAV4694_recentered,
                                        session.subjectPaths.pet_nav4694.bids_processed.reMaskVal],
                                output=session.subjectPaths.pet_nav4694.bids_processed.SUVR,
                                mathString="{} -div $(cat {})") for session in
                      self.sessions]), env=self.envs.envFSL)

        self.petnav4694_base_suvr_statsSchaefer200_17 = PipeJobPartial(name="PETNAV4694_base_SUVR_statsSchaefer200_17", job=SchedulerPartial(
            taskList=[ExtractAtlasValues(infile=session.subjectPaths.pet_nav4694.bids_processed.SUVR,
                                         atlas=session.subjectPaths.pet_nav4694.bids_processed.atlas_schaefer200_17Net,
                                         outfile=session.subjectPaths.pet_nav4694.bids_statistics.SUVR_WHOLECER_Schaefer200_17Net_mean,
                                         func="mean") for session in
                      self.sessions]), env=self.envs.envR)

        self.petnav4694_base_suvr_statsMindboggle = PipeJobPartial(name="PETNAV4694_base_SUVR_statsMindboggle", job=SchedulerPartial(
            taskList=[ExtractAtlasValues(infile=session.subjectPaths.pet_nav4694.bids_processed.SUVR,
                                         atlas=session.subjectPaths.pet_nav4694.bids_processed.atlas_mindboggle,
                                         outfile=session.subjectPaths.pet_nav4694.bids_statistics.SUVR_WHOLECER_Mindboggle101_mean,
                                         func="mean") for session in
                      self.sessions]), env=self.envs.envR)

        self.petnav4694_base_suvrToCentiloid_Schaefer200_17 = PipeJobPartial(name="PETNAV4694_base_SUVRToCentiloid_Schaefer200_17", job=SchedulerPartial(
            taskList=[SUVRToCentiloid(infile=session.subjectPaths.pet_nav4694.bids_statistics.SUVR_WHOLECER_Schaefer200_17Net_mean,
                                         outfile=session.subjectPaths.pet_nav4694.bids_statistics.Centiloid_WHOLECER_Schaefer200_17Net_mean,
                                         tracerName="NAV4694") for session in
                      self.sessions]), env=self.envs.envR)

        self.petnav4694_base_suvrToCentiloid_Mindboggle = PipeJobPartial(name="PETNAV4694_base_SUVRToCentiloid_Mindboggle", job=SchedulerPartial(
            taskList=[SUVRToCentiloid(infile=session.subjectPaths.pet_nav4694.bids_statistics.SUVR_WHOLECER_Mindboggle101_mean,
                                      outfile=session.subjectPaths.pet_nav4694.bids_statistics.Centiloid_WHOLECER_Mindboggle101_mean,
                                      tracerName="NAV4694") for session in
                      self.sessions]), env=self.envs.envR)

    def setup(self) -> bool:
        self.addPipeJobs()
        return True
