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

class PETAV45_base_withT1w(ProcessingModule):
    requiredModalities = ["T1w", "pet_av45"]
    moduleDependencies = ["T1w_1mm"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=4)

        # self.petav45_base_recenter = PipeJobPartial(name="PETAV45_base_recenterToCom", job=SchedulerPartial(
        #     taskList=[RecenterToCOM(infile=session.subjectPaths.pet_av45.bids.PETAV45,
        #                             outfile=session.subjectPaths.pet_av45.bids_processed.PETAV45_recentered
        #                             ) for session in
        #               self.sessions]),
        #                                env=self.envs.envMRPipe)

        self.petav45_base_recenter = PipeJobPartial(name="PETAV45_base_recenterToCom", job=SchedulerPartial(
            taskList=[CP(infile=session.subjectPaths.pet_av45.bids.PETAV45,
                                    outfile=session.subjectPaths.pet_av45.bids_processed.PETAV45_recentered
                                    ) for session in
                      self.sessions]),
                                                    env=self.envs.envMRPipe)

        self.petav45_base_NativeToT1w = PipeJobPartial(name="PETAV45_base_NativeToT1w", job=SchedulerPartial(
            taskList=[AntsRegistrationSyN(fixed=session.subjectPaths.T1w.bids_processed.iso1mm.baseimage,
                                          moving=session.subjectPaths.pet_av45.bids_processed.PETAV45_recentered,
                                          outprefix=session.subjectPaths.pet_av45.bids_processed.toT1w_prefix,
                                          expectedOutFiles=[session.subjectPaths.pet_av45.bids_processed.toT1w_toT1w,
                                                            session.subjectPaths.pet_av45.bids_processed.toT1w_0GenericAffine],
                                          ncores=2, dim=3, type="a") for session in self.sessions]),
                                                  env=self.envs.envANTS)

        self.petav45_base_fromT1w_WHOLECER = PipeJobPartial(name="PETAV45_base_fromT1w_WHOLECER", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=self.templates.cerebellum_whole_eroded,
                                          output=session.subjectPaths.pet_av45.bids_processed.refMask,
                                          reference=session.subjectPaths.pet_av45.bids_processed.PETAV45_recentered,
                                          transforms=[session.subjectPaths.pet_av45.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1InverseWarp],
                                          inverse_transform=[True, True, False],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.petav45_base_fromT1w_schaefer200_17Net = PipeJobPartial(name="PETAV45_base_fromT1w_schaefer200_17Net", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=self.templates.Schaefer2018_200Parcels_17Networks_order_FSLMNI152_1mm,
                                          output=session.subjectPaths.pet_av45.bids_processed.atlas_schaefer200_17Net,
                                          reference=session.subjectPaths.pet_av45.bids_processed.PETAV45_recentered,
                                          transforms=[session.subjectPaths.pet_av45.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1InverseWarp],
                                          inverse_transform=[True, True, False],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.petav45_base_fromT1w_Mindboggle101 = PipeJobPartial(name="PETAV45_base_fromT1w_Mindboggle101", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=self.templates.OASIS_TRT_20_jointfusion_DKT31_CMA_labels_in_MNI152_v2,
                                          output=session.subjectPaths.pet_av45.bids_processed.atlas_mindboggle,
                                          reference=session.subjectPaths.pet_av45.bids_processed.PETAV45_recentered,
                                          transforms=[session.subjectPaths.pet_av45.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1InverseWarp],
                                          inverse_transform=[True, True, False],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.petav45_base_qc_vis_toT1w = PipeJobPartial(name="PETAV45_base_slices_toT1w", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.pet_av45.bids_processed.toT1w_toT1w,
                            mask=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                            image=session.subjectPaths.pet_av45.meta_QC.ToT1w_native_slices, contrastAdjustment=False,
                            outline=True, transparency=True, zoom=1) for session in
                      self.sessions]), env=self.envs.envQCVis)

        self.petav45_base_refvol_mean = PipeJobPartial(name="PETAV45_base_RefVol_mean", job=SchedulerPartial(
            taskList=[FSLStatsToFile(infile=session.subjectPaths.pet_av45.bids_processed.PETAV45_recentered,
                                     output=session.subjectPaths.pet_av45.bids_processed.reMaskVal,
                                     mask=session.subjectPaths.pet_av45.bids_processed.refMask,
                                     options=["-n", "-k", "-M"]) for session in
                      self.sessions]), env=self.envs.envFSL)

        self.petav45_base_suvr = PipeJobPartial(name="PETAV45_base_SUVR", job=SchedulerPartial(
            taskList=[FSLMaths(infiles=[session.subjectPaths.pet_av45.bids_processed.PETAV45_recentered,
                                        session.subjectPaths.pet_av45.bids_processed.reMaskVal],
                                output=session.subjectPaths.pet_av45.bids_processed.SUVR,
                                mathString="{} -div $(cat {})") for session in
                      self.sessions]), env=self.envs.envFSL)

        self.petav45_base_suvr_statsSchaefer200_17 = PipeJobPartial(name="PETAV45_base_SUVR_statsSchaefer200_17", job=SchedulerPartial(
            taskList=[ExtractAtlasValues(infile=session.subjectPaths.pet_av45.bids_processed.SUVR,
                                         atlas=session.subjectPaths.pet_av45.bids_processed.atlas_schaefer200_17Net,
                                         outfile=session.subjectPaths.pet_av45.bids_statistics.SUVR_WHOLECER_Schaefer200_17Net_mean,
                                         func="mean") for session in
                      self.sessions]), env=self.envs.envR)

        self.petav45_base_suvr_statsMindboggle = PipeJobPartial(name="PETAV45_base_SUVR_statsMindboggle", job=SchedulerPartial(
            taskList=[ExtractAtlasValues(infile=session.subjectPaths.pet_av45.bids_processed.SUVR,
                                         atlas=session.subjectPaths.pet_av45.bids_processed.atlas_mindboggle,
                                         outfile=session.subjectPaths.pet_av45.bids_statistics.SUVR_WHOLECER_Mindboggle101_mean,
                                         func="mean") for session in
                      self.sessions]), env=self.envs.envR)

        self.petav45_base_suvrToCentiloid_Schaefer200_17 = PipeJobPartial(name="PETAV45_base_SUVRToCentiloid_Schaefer200_17", job=SchedulerPartial(
            taskList=[SUVRToCentiloid(infile=session.subjectPaths.pet_av45.bids_statistics.SUVR_WHOLECER_Schaefer200_17Net_mean,
                                         outfile=session.subjectPaths.pet_av45.bids_statistics.Centiloid_WHOLECER_Schaefer200_17Net_mean,
                                         tracerName="AV45") for session in
                      self.sessions]), env=self.envs.envR)

        self.petav45_base_suvrToCentiloid_Mindboggle = PipeJobPartial(name="PETAV45_base_SUVRToCentiloid_Mindboggle", job=SchedulerPartial(
            taskList=[SUVRToCentiloid(infile=session.subjectPaths.pet_av45.bids_statistics.SUVR_WHOLECER_Mindboggle101_mean,
                                      outfile=session.subjectPaths.pet_av45.bids_statistics.Centiloid_WHOLECER_Mindboggle101_mean,
                                      tracerName="AV45") for session in
                      self.sessions]), env=self.envs.envR)

    def setup(self) -> bool:
        self.addPipeJobs()
        return True
