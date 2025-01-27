from mrpipe.modalityModules.ProcessingModule import ProcessingModule
from functools import partial
from mrpipe.schedueler.PipeJob import PipeJob
from mrpipe.schedueler import Slurm
from mrpipe.Toolboxes.standalone.QCVis import QCVis
from mrpipe.Toolboxes.ANTSTools.AntsRegistrationSyN import AntsRegistrationSyN
from mrpipe.Toolboxes.ANTSTools.AntsApplyTransform import AntsApplyTransforms
from mrpipe.Toolboxes.standalone.cp import CP
from mrpipe.Toolboxes.FSL.FSLStats import FSLStats
from mrpipe.Toolboxes.FSL.FSLMaths import FSLMaths
from mrpipe.Toolboxes.FSL.FSLStats import FSLStatsToFile
from mrpipe.Toolboxes.FSL.FSLStats import FSLStatsWithCenTauRZ
from mrpipe.Toolboxes.standalone.RecenterToCOM import RecenterToCOM
from mrpipe.Toolboxes.standalone.ExtractAtlasValues import ExtractAtlasValues

class PETAV1451_base_withT1w(ProcessingModule):
    requiredModalities = ["T1w", "pet_av1451"]
    moduleDependencies = ["T1w_1mm"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=4)

        # self.petav1451_base_recenter = PipeJobPartial(name="PETAV1451_base_recenterToCom", job=SchedulerPartial(
        #     taskList=[RecenterToCOM(infile=session.subjectPaths.pet_av1451.bids.PETAV1451,
        #                             outfile=session.subjectPaths.pet_av1451.bids_processed.PETAV1451_recentered
        #                             ) for session in
        #               self.sessions]),
        #                                env=self.envs.envMRPipe)

        self.petav1451_base_recenter = PipeJobPartial(name="PETAV1451_base_recenterToCom", job=SchedulerPartial(
            taskList=[CP(infile=session.subjectPaths.pet_av1451.bids.PETAV1451,
                                    outfile=session.subjectPaths.pet_av1451.bids_processed.PETAV1451_recentered
                                    ) for session in
                      self.sessions]),
                                                      env=self.envs.envMRPipe)

        self.petav1451_base_NativeToT1w = PipeJobPartial(name="PETAV1451_base_NativeToT1w", job=SchedulerPartial(
            taskList=[AntsRegistrationSyN(fixed=session.subjectPaths.T1w.bids_processed.iso1mm.baseimage,
                                          moving=session.subjectPaths.pet_av1451.bids_processed.PETAV1451_recentered,
                                          outprefix=session.subjectPaths.pet_av1451.bids_processed.toT1w_prefix,
                                          expectedOutFiles=[session.subjectPaths.pet_av1451.bids_processed.toT1w_toT1w,
                                                            session.subjectPaths.pet_av1451.bids_processed.toT1w_0GenericAffine],
                                          ncores=2, dim=3, type="a") for session in self.sessions]),
                                                  env=self.envs.envANTS)

        self.petav1451_base_fromT1w_INFCER = PipeJobPartial(name="PETAV1451_base_fromT1w_INFCER", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=self.templates.cerebellum_inferiorGM_eroded,
                                          output=session.subjectPaths.pet_av1451.bids_processed.refMask,
                                          reference=session.subjectPaths.pet_av1451.bids_processed.PETAV1451_recentered,
                                          transforms=[session.subjectPaths.pet_av1451.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1InverseWarp],
                                          inverse_transform=[True, True, False],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.petav1451_base_fromT1w_schaefer200_17Net = PipeJobPartial(name="PETAV1451_base_fromT1w_schaefer200_17Net", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=self.templates.Schaefer2018_200Parcels_17Networks_order_FSLMNI152_1mm,
                                          output=session.subjectPaths.pet_av1451.bids_processed.atlas_schaefer200_17Net,
                                          reference=session.subjectPaths.pet_av1451.bids_processed.PETAV1451_recentered,
                                          transforms=[session.subjectPaths.pet_av1451.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1InverseWarp],
                                          inverse_transform=[True, True, False],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.petav1451_base_fromT1w_Mindboggle101 = PipeJobPartial(name="PETAV1451_base_fromT1w_Mindboggle101", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=self.templates.OASIS_TRT_20_jointfusion_DKT31_CMA_labels_in_MNI152_v2,
                                          output=session.subjectPaths.pet_av1451.bids_processed.atlas_mindboggle,
                                          reference=session.subjectPaths.pet_av1451.bids_processed.PETAV1451_recentered,
                                          transforms=[session.subjectPaths.pet_av1451.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1InverseWarp],
                                          inverse_transform=[True, True, False],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.petav1451_base_qc_vis_toT1w = PipeJobPartial(name="PETAV1451_base_slices_toT1w", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.pet_av1451.bids_processed.toT1w_toT1w,
                            mask=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                            image=session.subjectPaths.pet_av1451.meta_QC.ToT1w_native_slices, contrastAdjustment=False,
                            outline=True, transparency=True, zoom=1) for session in
                      self.sessions]), env=self.envs.envQCVis)

        self.petav1451_base_refvol_mean = PipeJobPartial(name="PETAV1451_base_RefVol_mean", job=SchedulerPartial(
            taskList=[FSLStatsToFile(infile=session.subjectPaths.pet_av1451.bids_processed.PETAV1451_recentered,
                                     output=session.subjectPaths.pet_av1451.bids_processed.reMaskVal,
                                     mask=session.subjectPaths.pet_av1451.bids_processed.refMask,
                                     options=["-n", "-k", "-M"]) for session in
                      self.sessions]), env=self.envs.envFSL)

        self.petav1451_base_suvr = PipeJobPartial(name="PETAV1451_base_SUVR", job=SchedulerPartial(
            taskList=[FSLMaths(infiles=[session.subjectPaths.pet_av1451.bids_processed.PETAV1451_recentered,
                                        session.subjectPaths.pet_av1451.bids_processed.reMaskVal],
                                output=session.subjectPaths.pet_av1451.bids_processed.SUVR,
                                mathString="{} -div $(cat {})") for session in
                      self.sessions]), env=self.envs.envFSL)

        self.petav1451_base_suvr_statsSchaefer200_17 = PipeJobPartial(name="PETAV1451_base_SUVR_statsSchaefer200_17", job=SchedulerPartial(
            taskList=[ExtractAtlasValues(infile=session.subjectPaths.pet_av1451.bids_processed.SUVR,
                                         atlas=session.subjectPaths.pet_av1451.bids_processed.atlas_schaefer200_17Net,
                                         outfile=session.subjectPaths.pet_av1451.bids_statistics.SUVR_INFCER_Schaefer200_17Net_mean,
                                         func="mean") for session in
                      self.sessions]), env=self.envs.envR)

        self.petav1451_base_suvr_statsMindboggle = PipeJobPartial(name="PETAV1451_base_SUVR_statsMindboggle", job=SchedulerPartial(
            taskList=[ExtractAtlasValues(infile=session.subjectPaths.pet_av1451.bids_processed.SUVR,
                                         atlas=session.subjectPaths.pet_av1451.bids_processed.atlas_mindboggle,
                                         outfile=session.subjectPaths.pet_av1451.bids_statistics.SUVR_INFCER_Mindboggle101_mean,
                                         func="mean") for session in
                      self.sessions]), env=self.envs.envR)


    def setup(self) -> bool:
        self.addPipeJobs()
        return True



class PETAV1451_native_CenTauRZ(ProcessingModule):
    requiredModalities = ["T1w", "pet_av1451"]
    moduleDependencies = ["T1w_1mm", "PETAV1451_base_withT1w"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=4)

        self.petav1451_centaurz_fromT1w_CenTauR = PipeJobPartial(name="PETAV1451_centaurz_fromT1w_CenTauR", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=self.templates.centaur_CenTauR,
                                          output=session.subjectPaths.pet_av1451.bids_processed.centaur_maskNative_CenTauR,
                                          reference=session.subjectPaths.pet_av1451.bids_processed.PETAV1451_recentered,
                                          transforms=[session.subjectPaths.pet_av1451.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1InverseWarp],
                                          inverse_transform=[True, True, False],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.petav1451_centaurz_stats_CenTauR = PipeJobPartial(name="PETAV1451_centaurz_stats_CenTauR", job=SchedulerPartial(
            taskList=[FSLStats(infile=session.subjectPaths.pet_av1451.bids_processed.SUVR,
                               output=session.subjectPaths.pet_av1451.bids_statistics.centaur_native_SUVR_CenTauR,
                               options=["-k", "-M"],
                               mask=session.subjectPaths.pet_av1451.bids_processed.centaur_maskNative_CenTauR) for
                      session in self.sessions], cpusPerTask=3), env=self.envs.envFSL)

        self.petav1451_centaurz_CTRz_stats_CenTauR = PipeJobPartial(name="PETAV1451_centaurz_CTRz_stats_CenTauR", job=SchedulerPartial(
            taskList=[FSLStatsWithCenTauRZ(infile=session.subjectPaths.pet_av1451.bids_processed.SUVR,
                               output=session.subjectPaths.pet_av1451.bids_statistics.centaur_native_CTRz_CenTauR,
                               options=["-k", "-M"],
                               tracer="FTP", centaurMask="CenTauR",
                               mask=session.subjectPaths.pet_av1451.bids_processed.centaur_maskNative_CenTauR) for
                      session in self.sessions], cpusPerTask=3), env=self.envs.envFSL_R)

        self.petav1451_centaurz_fromT1w_Frontal_CenTauR = PipeJobPartial(name="PETAV1451_centaurz_fromT1w_Frontal_CenTauR", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(
                input=self.templates.centaur_Frontal_CenTauR,
                output=session.subjectPaths.pet_av1451.bids_processed.centaur_maskNative_Frontal_CenTauR,
                reference=session.subjectPaths.pet_av1451.bids_processed.PETAV1451_recentered,
                transforms=[session.subjectPaths.pet_av1451.bids_processed.toT1w_0GenericAffine,
                            session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                            session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1InverseWarp],
                inverse_transform=[True, True, False],
                interpolation="NearestNeighbor",
                verbose=self.inputArgs.verbose <= 30) for session in
                self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.petav1451_centaurz_stats_Frontal_CenTauR = PipeJobPartial(name="PETAV1451_centaurz_stats_Frontal_CenTauR", job=SchedulerPartial(
            taskList=[FSLStats(infile=session.subjectPaths.pet_av1451.bids_processed.SUVR,
                               output=session.subjectPaths.pet_av1451.bids_statistics.centaur_native_SUVR_Frontal_CenTauR,
                               options=["-k", "-M"],
                               mask=session.subjectPaths.pet_av1451.bids_processed.centaur_maskNative_Frontal_CenTauR) for
                      session in self.sessions], cpusPerTask=3), env=self.envs.envFSL)

        self.petav1451_centaurz_CTRz_stats_Frontal_CenTauR = PipeJobPartial(name="PETAV1451_centaurz_CTRz_stats_Frontal_CenTauR", job=SchedulerPartial(
            taskList=[FSLStatsWithCenTauRZ(infile=session.subjectPaths.pet_av1451.bids_processed.SUVR,
                               output=session.subjectPaths.pet_av1451.bids_statistics.centaur_native_CTRz_Frontal_CenTauR,
                               options=["-k", "-M"],
                               tracer="FTP", centaurMask="Frontal_CenTauR",
                               mask=session.subjectPaths.pet_av1451.bids_processed.centaur_maskNative_Frontal_CenTauR) for
                      session in self.sessions], cpusPerTask=3), env=self.envs.envFSL_R)

        self.petav1451_centaurz_fromT1w_Mesial_CenTauR = PipeJobPartial(name="PETAV1451_base_fromT1w_Mesial_CenTauR", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(
                input=self.templates.centaur_Mesial_CenTauR,
                output=session.subjectPaths.pet_av1451.bids_processed.centaur_maskNative_Mesial_CenTauR,
                reference=session.subjectPaths.pet_av1451.bids_processed.PETAV1451_recentered,
                transforms=[session.subjectPaths.pet_av1451.bids_processed.toT1w_0GenericAffine,
                            session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                            session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1InverseWarp],
                inverse_transform=[True, True, False],
                interpolation="NearestNeighbor",
                verbose=self.inputArgs.verbose <= 30) for session in
                self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.petav1451_centaurz_stats_Mesial_CenTauR = PipeJobPartial(name="PETAV1451_centaurz_stats_Mesial_CenTauR", job=SchedulerPartial(
            taskList=[FSLStats(infile=session.subjectPaths.pet_av1451.bids_processed.SUVR,
                               output=session.subjectPaths.pet_av1451.bids_statistics.centaur_native_SUVR_Mesial_CenTauR,
                               options=["-k", "-M"],
                               mask=session.subjectPaths.pet_av1451.bids_processed.centaur_maskNative_Mesial_CenTauR) for
                      session in self.sessions], cpusPerTask=3), env=self.envs.envFSL)

        self.petav1451_centaurz_CTRz_stats_Mesial_CenTauR = PipeJobPartial(name="PETAV1451_centaurz_CTRz_stats_Mesial_CenTauR", job=SchedulerPartial(
            taskList=[FSLStatsWithCenTauRZ(infile=session.subjectPaths.pet_av1451.bids_processed.SUVR,
                               output=session.subjectPaths.pet_av1451.bids_statistics.centaur_native_CTRz_Mesial_CenTauR,
                               options=["-k", "-M"],
                               tracer="FTP", centaurMask="Mesial_CenTauR",
                               mask=session.subjectPaths.pet_av1451.bids_processed.centaur_maskNative_Mesial_CenTauR) for
                      session in self.sessions], cpusPerTask=3), env=self.envs.envFSL_R)

        self.petav1451_centaurz_fromT1w_Meta_CenTauR = PipeJobPartial(name="PETAV1451_base_fromT1w_Meta_CenTauR", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(
                input=self.templates.centaur_Meta_CenTauR,
                output=session.subjectPaths.pet_av1451.bids_processed.centaur_maskNative_Meta_CenTauR,
                reference=session.subjectPaths.pet_av1451.bids_processed.PETAV1451_recentered,
                transforms=[session.subjectPaths.pet_av1451.bids_processed.toT1w_0GenericAffine,
                            session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                            session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1InverseWarp],
                inverse_transform=[True, True, False],
                interpolation="NearestNeighbor",
                verbose=self.inputArgs.verbose <= 30) for session in
                self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.petav1451_centaurz_stats_Meta_CenTauR = PipeJobPartial(name="PETAV1451_centaurz_stats_Meta_CenTauR", job=SchedulerPartial(
            taskList=[FSLStats(infile=session.subjectPaths.pet_av1451.bids_processed.SUVR,
                               output=session.subjectPaths.pet_av1451.bids_statistics.centaur_native_SUVR_Meta_CenTauR,
                               options=["-k", "-M"],
                               mask=session.subjectPaths.pet_av1451.bids_processed.centaur_maskNative_Meta_CenTauR) for
                      session in self.sessions], cpusPerTask=3), env=self.envs.envFSL)

        self.petav1451_centaurz_CTRz_stats_Meta_CenTauR = PipeJobPartial(name="PETAV1451_centaurz_CTRz_stats_Meta_CenTauR", job=SchedulerPartial(
            taskList=[FSLStatsWithCenTauRZ(infile=session.subjectPaths.pet_av1451.bids_processed.SUVR,
                               output=session.subjectPaths.pet_av1451.bids_statistics.centaur_native_CTRz_Meta_CenTauR,
                               options=["-k", "-M"],
                               tracer="FTP", centaurMask="Meta_CenTauR",
                               mask=session.subjectPaths.pet_av1451.bids_processed.centaur_maskNative_Meta_CenTauR) for
                      session in self.sessions], cpusPerTask=3), env=self.envs.envFSL_R)

        self.petav1451_centaurz_fromT1w_TP_CenTauR = PipeJobPartial(name="PETAV1451_base_fromT1w_TP_CenTauR", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(
                input=self.templates.centaur_TP_CenTauR,
                output=session.subjectPaths.pet_av1451.bids_processed.centaur_maskNative_TP_CenTauR,
                reference=session.subjectPaths.pet_av1451.bids_processed.PETAV1451_recentered,
                transforms=[session.subjectPaths.pet_av1451.bids_processed.toT1w_0GenericAffine,
                            session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                            session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1InverseWarp],
                inverse_transform=[True, True, False],
                interpolation="NearestNeighbor",
                verbose=self.inputArgs.verbose <= 30) for session in
                self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.petav1451_centaurz_stats_TP_CenTauR = PipeJobPartial(name="PETAV1451_centaurz_stats_TP_CenTauR", job=SchedulerPartial(
            taskList=[FSLStats(infile=session.subjectPaths.pet_av1451.bids_processed.SUVR,
                               output=session.subjectPaths.pet_av1451.bids_statistics.centaur_native_SUVR_TP_CenTauR,
                               options=["-k", "-M"],
                               mask=session.subjectPaths.pet_av1451.bids_processed.centaur_maskNative_TP_CenTauR) for
                      session in self.sessions], cpusPerTask=3), env=self.envs.envFSL)

        self.petav1451_centaurz_CTRz_stats_TP_CenTauR = PipeJobPartial(name="PETAV1451_centaurz_CTRz_stats_TP_CenTauR", job=SchedulerPartial(
            taskList=[FSLStatsWithCenTauRZ(infile=session.subjectPaths.pet_av1451.bids_processed.SUVR,
                               output=session.subjectPaths.pet_av1451.bids_statistics.centaur_native_CTRz_TP_CenTauR,
                               options=["-k", "-M"],
                               tracer="FTP", centaurMask="TP_CenTauR",
                               mask=session.subjectPaths.pet_av1451.bids_processed.centaur_maskNative_TP_CenTauR) for
                      session in self.sessions], cpusPerTask=3), env=self.envs.envFSL_R)
    def setup(self) -> bool:
        self.addPipeJobs()
        return True
