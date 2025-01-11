from mrpipe.modalityModules.ProcessingModule import ProcessingModule
from functools import partial
from mrpipe.schedueler.PipeJob import PipeJob
from mrpipe.schedueler import Slurm
from mrpipe.Toolboxes.FSL.Merge import Merge
from mrpipe.Toolboxes.ANTSTools.N4BiasFieldCorrect import N4BiasFieldCorrect
from mrpipe.Toolboxes.standalone.QCVis import QCVis
from mrpipe.Toolboxes.standalone.QCVisWithoutMask import QCVisWithoutMask
from mrpipe.Toolboxes.ANTSTools.AntsRegistrationSyN import AntsRegistrationSyN
from mrpipe.Toolboxes.ANTSTools.AntsApplyTransform import AntsApplyTransforms
from mrpipe.Toolboxes.standalone.cp import CP
from mrpipe.Toolboxes.QSM.ChiSeperation import ChiSeperation
from mrpipe.Toolboxes.FSL.FSLStats import FSLStats
import os
from mrpipe.Helper import Helper

class MEGRE_base(ProcessingModule):
    requiredModalities = ["megre", "T1w"]
    moduleDependencies = ["T1w_base"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)

        # Step 0: transform first Mag to T1 native for brain mask:
        self.megre_base_NativeToT1w = PipeJobPartial(name="MEGRE_base_NativeToT1", job=SchedulerPartial(
            taskList=[AntsRegistrationSyN(fixed=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                          moving=session.subjectPaths.megre.bids.megre.magnitude[0].imagePath,
                                          outprefix=session.subjectPaths.megre.bids_processed.toT1w_prefix,
                                          expectedOutFiles=[session.subjectPaths.megre.bids_processed.toT1w_toT1w,
                                                            session.subjectPaths.megre.bids_processed.toT1w_InverseWarped,
                                                            session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          ncores=2, dim=3, type="a") for session in self.sessions],
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=2, minimumMemPerNode=4),
                                                env=self.envs.envANTS)

        self.megre_base_qc_vis_toT1w = PipeJobPartial(name="MEGRE_base_slices_toT1w", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.megre.bids_processed.toT1w_toT1w,
                            mask=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                            image=session.subjectPaths.megre.meta_QC.ToT1w_native_slices, contrastAdjustment=False,
                            outline=True, transparency=True, zoom=1) for session in
                      self.sessions]), env=self.envs.envQCVis)

        self.megre_base_bmToMEGRE = PipeJobPartial(name="MEGRE_base_BMtoMEGRE", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                                          output=session.subjectPaths.megre.bids_processed.brainMask_toMEGRE,
                                          reference=session.subjectPaths.megre.bids.megre.magnitude[0].imagePath,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="NearestNeighbor",
                                          inverse_transform=[True],
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        # Step 1: Merge phase and magnitude to 4d Images
        self.megre_base_mergePhase4D = PipeJobPartial(name="MEGRE_base_mergePhase4D", job=SchedulerPartial(
            taskList=[Merge(infile=session.subjectPaths.megre.bids.megre.get_phase_paths(),
                            output=session.subjectPaths.megre.bids_processed.phase4D,
                            clobber=False) for session in
                      self.sessions],
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=4, minimumMemPerNode=8),
                                    env=self.envs.envFSL)

        self.megre_base_mergeMagnitude4D = PipeJobPartial(name="MEGRE_base_mergeMagnitude4D", job=SchedulerPartial(
            taskList=[Merge(infile=session.subjectPaths.megre.bids.megre.get_magnitude_paths(),
                            output=session.subjectPaths.megre.bids_processed.magnitude4d,
                            clobber=False) for session in
                      self.sessions],
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=4, minimumMemPerNode=8),
                                           env=self.envs.envFSL)

        # Step 2: perform Chi-seperation
        self.megre_base_chiSep = PipeJobPartial(name="MEGRE_base_chiSep", job=SchedulerPartial(
            taskList=[ChiSeperation(mag4d_path=session.subjectPaths.megre.bids_processed.magnitude4d,
                                    pha4d_path=session.subjectPaths.megre.bids_processed.phase4D,
                                    brainmask_path=session.subjectPaths.megre.bids_processed.brainMask_toMEGRE,
                                    outdir=session.subjectPaths.megre.bids_processed.chiSepDir,
                                    TEms=session.subjectPaths.megre.bids.megre.echoTimes,
                                    b0_direction=session.subjectPaths.megre.bids.megre.get_b0_directions(),
                                    CFs=session.subjectPaths.megre.bids.megre.magnitude[1].getAttribute("ImagingFrequency"),
                                    Toolboxes=[self.libpaths.medi_toolbox,
                                               self.libpaths.sti_suite,
                                               os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "compileMRI"),
                                               #self.libpaths.matlab_onnx, #must be installed through the matlab version, apparently. I did not get it to work if provided as downloaded additional package.
                                               self.libpaths.matlab_ToolsForNifti],
                                    pre_string=session.subjectPaths.megre.bids_processed.baseString,
                                    chi_sep_dir=self.libpaths.chiSepToolbox,
                                    vendor=session.subjectPaths.megre.bids.megre.magnitude[1].getAttribute("Manufacturer"),
                                    outfiles=[session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                              session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                              session.subjectPaths.megre.bids_processed.chiTotal,
                                              session.subjectPaths.megre.bids_processed.QSM,
                                              session.subjectPaths.megre.bids_processed.localfild,
                                              session.subjectPaths.megre.bids_processed.unwrappedPhase,
                                              session.subjectPaths.megre.bids_processed.fieldMap,
                                              session.subjectPaths.megre.bids_processed.B0,
                                              session.subjectPaths.megre.bids_processed.NStd,
                                              session.subjectPaths.megre.bids_processed.BrainMaskAfterVSharp],
                                    clobber=False) for session in
                      self.sessions],
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=4, minimumMemPerNode=8),
                                               env=self.envs.envChiSep)

        # chi Sep QC
        self.megre_base_chiSep_diaQC = PipeJobPartial(name="MEGRE_base_chiSep_diaQC", job=SchedulerPartial(
            taskList=[QCVisWithoutMask(infile=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                            image=session.subjectPaths.megre.meta_QC.chiSepDia_native_slices,
                            zoom=1, sliceNumber=12) for session in
                      self.sessions]), env=self.envs.envQCVis)

        self.megre_base_chiSep_ParaQC = PipeJobPartial(name="MEGRE_base_chiSep_ParaQC", job=SchedulerPartial(
            taskList=[QCVisWithoutMask(infile=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                       image=session.subjectPaths.megre.meta_QC.chiSepPara_native_slices,
                                       zoom=1, sliceNumber=12) for session in
                      self.sessions]), env=self.envs.envQCVis)

        self.megre_base_chiSep_QSMQC = PipeJobPartial(name="MEGRE_base_chiSep_QSMQC", job=SchedulerPartial(
            taskList=[QCVisWithoutMask(infile=session.subjectPaths.megre.bids_processed.QSM,
                                       image=session.subjectPaths.megre.meta_QC.chiSepQSM_native_slices,
                                       zoom=1, sliceNumber=12) for session in
                      self.sessions]), env=self.envs.envQCVis)

    def setup(self) -> bool:
        self.addPipeJobs()
        return True

# TODO: One day, implement chi_sep without T1 brain maks but use hd-bet for betting magnitude brain masks.
class MEGRE_ToT1wNative(ProcessingModule):
    requiredModalities = ["T1w", "megre"]
    moduleDependencies = ["MEGRE_base", "T1w_base"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)

        self.megre_toT1wNative_ChiDia = PipeJobPartial(name="MEGRE_native_DiaToT1w", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.chiDiamagnetic_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.megre_toT1wNative_ChiPara = PipeJobPartial(name="MEGRE_native_ParaToT1w", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.chiParamagnetic_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.megre_toT1wNative_QSM = PipeJobPartial(name="MEGRE_native_QSMToT1w", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.QSM,
                                          output=session.subjectPaths.megre.bids_processed.QSM_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

    def setup(self) -> bool:
        self.addPipeJobs()
        return True

class MEGRE_statsNative(ProcessingModule):
    requiredModalities = ["T1w", "megre"]
    moduleDependencies = ["MEGRE_ToT1wNative", "T1w_base", "MEGRE_base"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)

        self.megre_native_fromT1w_WM = PipeJobPartial(name="MEGRE_native_fromT1w_WM", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.maskWMCortical_thr0p5_ero1mm,
                                          output=session.subjectPaths.megre.bids_processed.fromT1w_WMCortical_thr0p5_ero1mm,
                                          reference=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.megre_NativeToT1w_1mm_ChiDia = PipeJobPartial(name="MEGRE_StatsNative_ChiDia_WM", job=SchedulerPartial(
            taskList=[FSLStats(infile=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                               output=session.subjectPaths.megre.bids_statistics.chiSepResults_chiNeg_mean_WMCortical_0p5_ero1mm,
                               options=["-k", "-M"],
                               mask=session.subjectPaths.megre.bids_processed.fromT1w_WMCortical_thr0p5_ero1mm) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.megre_NativeToT1w_1mm_ChiPara = PipeJobPartial(name="MEGRE_StatsNative_ChiPara_WM", job=SchedulerPartial(
            taskList=[FSLStats(infile=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                               output=session.subjectPaths.megre.bids_statistics.chiSepResults_chiPos_mean_WMCortical_0p5_ero1mm,
                               options=["-k", "-M"],
                               mask=session.subjectPaths.megre.bids_processed.fromT1w_WMCortical_thr0p5_ero1mm) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.megre_NativeToT1w_1mm_QSM = PipeJobPartial(name="MEGRE_StatsNative_QSM_WM", job=SchedulerPartial(
            taskList=[FSLStats(infile=session.subjectPaths.megre.bids_processed.QSM,
                               output=session.subjectPaths.megre.bids_statistics.chiSepResults_QSM_mean_WMCortical_0p5_ero1mm,
                               options=["-k", "-M"],
                               mask=session.subjectPaths.megre.bids_processed.fromT1w_WMCortical_thr0p5_ero1mm) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

    def setup(self) -> bool:
        self.addPipeJobs()
        return True



class MEGRE_statsNative_WMH(ProcessingModule):
    requiredModalities = ["T1w", "megre", "flair"]
    moduleDependencies = ["MEGRE_ToT1wNative", "T1w_base", "MEGRE_base", "FLAIR_base_withT1w"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)

        #transform WMH and NAWM
        self.megre_native_fromFlair_WMH = PipeJobPartial(name="MEGRE_native_fromFlair_WMH", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.WMHMask,
                                          output=session.subjectPaths.megre.bids_processed.fromFlair_WMH,
                                          reference=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          transforms=[
                                              session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine,
                                              session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[False, True],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.megre_native_fromFlair_NAWMCortical_thr0p5_ero1mm = PipeJobPartial(name="MEGRE_native_fromFlair_NAWMCortical_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.fromT1w_NAWMCortical_thr0p5_ero1mm,
                                          output=session.subjectPaths.megre.bids_processed.fromFlair_NAWMCortical_thr0p5_ero1mm,
                                          reference=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          transforms=[
                                              session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine,
                                              session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[False, True],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        #extract Stats from NAWM mask with Dia / Para / QSM
        self.megre_StatsNative_ChiDia_NAWMCortical_0p5_ero1mm = PipeJobPartial(name="MEGRE_StatsNative_ChiDia_NAWMCortical_0p5_ero1mm", job=SchedulerPartial(
            taskList=[FSLStats(infile=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                               output=session.subjectPaths.megre.bids_statistics.chiSepResults_chiNeg_mean_NAWMCortical_0p5_ero1mm,
                               options=["-k", "-M"],
                               mask=session.subjectPaths.megre.bids_processed.fromFlair_NAWMCortical_thr0p5_ero1mm) for
                      session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.megre_StatsNative_ChiPara_NAWMCortical_0p5_ero1mm = PipeJobPartial(name="MEGRE_StatsNative_ChiPara_NAWMCortical_0p5_ero1mm", job=SchedulerPartial(
            taskList=[FSLStats(infile=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                               output=session.subjectPaths.megre.bids_statistics.chiSepResults_chiPos_mean_NAWMCortical_0p5_ero1mm,
                               options=["-k", "-M"],
                               mask=session.subjectPaths.megre.bids_processed.fromFlair_NAWMCortical_thr0p5_ero1mm) for
                      session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.megre_StatsNative_QSM_NAWMCortical_0p5_ero1mm = PipeJobPartial(name="MEGRE_StatsNative_QSM_NAWMCortical_0p5_ero1mm", job=SchedulerPartial(
            taskList=[FSLStats(infile=session.subjectPaths.megre.bids_processed.QSM,
                               output=session.subjectPaths.megre.bids_statistics.chiSepResults_QSM_mean_NAWMCortical_0p5_ero1mm,
                               options=["-k", "-M"],
                               mask=session.subjectPaths.megre.bids_processed.fromFlair_NAWMCortical_thr0p5_ero1mm) for
                      session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        # extract Stats from WMH mask with Dia / Para / QSM
        self.megre_StatsNative_ChiDia_WMH = PipeJobPartial(
            name="MEGRE_StatsNative_ChiDia_WMH", job=SchedulerPartial(
                taskList=[FSLStats(infile=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                   output=session.subjectPaths.megre.bids_statistics.chiSepResults_chiNeg_mean_WMH,
                                   options=["-k", "-M"],
                                   mask=session.subjectPaths.megre.bids_processed.fromFlair_NAWMCortical_thr0p5_ero1mm)
                          for
                          session in
                          self.sessions],
                cpusPerTask=1), env=self.envs.envFSL)

        self.megre_StatsNative_ChiPara_WMH = PipeJobPartial(
            name="MEGRE_StatsNative_ChiPara_WMH", job=SchedulerPartial(
                taskList=[FSLStats(infile=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                   output=session.subjectPaths.megre.bids_statistics.chiSepResults_chiPos_mean_WMH,
                                   options=["-k", "-M"],
                                   mask=session.subjectPaths.megre.bids_processed.fromFlair_NAWMCortical_thr0p5_ero1mm)
                          for
                          session in
                          self.sessions],
                cpusPerTask=1), env=self.envs.envFSL)

        self.megre_StatsNative_QSM_WMH = PipeJobPartial(
            name="MEGRE_StatsNative_QSM_WMH", job=SchedulerPartial(
                taskList=[FSLStats(infile=session.subjectPaths.megre.bids_processed.QSM,
                                   output=session.subjectPaths.megre.bids_statistics.chiSepResults_QSM_mean_WMH,
                                   options=["-k", "-M"],
                                   mask=session.subjectPaths.megre.bids_processed.fromFlair_NAWMCortical_thr0p5_ero1mm)
                          for
                          session in
                          self.sessions],
                cpusPerTask=1), env=self.envs.envFSL)
    def setup(self) -> bool:
        self.addPipeJobs()
        return True

class MEGRE_ToT1wMNI_1mm(ProcessingModule):
    requiredModalities = ["T1w", "megre"]
    moduleDependencies = ["MEGRE_ToT1wNative", "T1w_1mm"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)

        self.megre_NativeToT1w_1mm_ChiDia = PipeJobPartial(name="MEGRE_NativeToT1w_1mm_ChiDia", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso1mm.chiDiamagnetic_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso1mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.megre_NativeToT1w_1mm_ChiPara = PipeJobPartial(name="MEGRE_NativeToT1w_1mm_ChiPara", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso1mm.chiParamagnetic_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso1mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.megre_NativeToT1w_1mm_QSM = PipeJobPartial(name="MEGRE_NativeToT1w_1mm_QSM", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.QSM,
                                          output=session.subjectPaths.megre.bids_processed.iso1mm.QSM_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso1mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)


        # To MNI
        self.megre_NativeToMNI_1mm_ChiDia = PipeJobPartial(name="MEGRE_NativeToMNI_1mm_ChiDia", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso1mm.chiDiamagnetic_toMNI,
                                          reference=self.templates.mni152_1mm,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1Warp],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.megre_NativeToMNI_1mm_ChiPara = PipeJobPartial(name="MEGRE_NativeToMNI_1mm_ChiPara", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso1mm.chiParamagnetic_toMNI,
                                          reference=self.templates.mni152_1mm,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1Warp],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.megre_NativeToMNI_1mm_QSM = PipeJobPartial(name="MEGRE_NativeToMNI_1mm_QSM", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.QSM,
                                          output=session.subjectPaths.megre.bids_processed.iso1mm.QSM_toMNI,
                                          reference=self.templates.mni152_1mm,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1Warp],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

    def setup(self) -> bool:
        self.addPipeJobs()
        return True

class MEGRE_ToT1wMNI_1p5mm(ProcessingModule):
    requiredModalities = ["T1w", "megre"]
    moduleDependencies = ["MEGRE_ToT1wNative", "T1w_1p5mm"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)

        self.megre_NativeToT1w_1p5mm_ChiDia = PipeJobPartial(name="MEGRE_NativeToT1w_1p5mm_ChiDia", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso1p5mm.chiDiamagnetic_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso1p5mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.megre_NativeToT1w_1p5mm_ChiPara = PipeJobPartial(name="MEGRE_NativeToT1w_1p5mm_ChiPara", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso1p5mm.chiParamagnetic_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso1p5mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.megre_NativeToT1w_1p5mm_QSM = PipeJobPartial(name="MEGRE_NativeToT1w_1p5mm_QSM", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.QSM,
                                          output=session.subjectPaths.megre.bids_processed.iso1p5mm.QSM_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso1p5mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)



        # To MNI
        self.megre_NativeToMNI_1p5mm_ChiDia = PipeJobPartial(name="MEGRE_NativeToMNI_1p5mm_ChiDia", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso1p5mm.chiDiamagnetic_toMNI,
                                          reference=self.templates.mni152_1p5mm,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_1Warp],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.megre_NativeToMNI_1p5mm_ChiPara = PipeJobPartial(name="MEGRE_NativeToMNI_1p5mm_ChiPara", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso1p5mm.chiParamagnetic_toMNI,
                                          reference=self.templates.mni152_1p5mm,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_1Warp],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.megre_NativeToMNI_1p5mm_QSM = PipeJobPartial(name="MEGRE_NativeToMNI_1p5mm_QSM", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.QSM,
                                          output=session.subjectPaths.megre.bids_processed.iso1p5mm.QSM_toMNI,
                                          reference=self.templates.mni152_1p5mm,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_1Warp],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

    def setup(self) -> bool:
        self.addPipeJobs()
        return True
    
    
class MEGRE_ToT1wMNI_2mm(ProcessingModule):
    requiredModalities = ["T1w", "megre"]
    moduleDependencies = ["MEGRE_ToT1wNative", "T1w_2mm"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)

        self.megre_NativeToT1w_2mm_ChiDia = PipeJobPartial(name="MEGRE_NativeToT1w_2mm_ChiDia", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso2mm.chiDiamagnetic_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso2mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.megre_NativeToT1w_2mm_ChiPara = PipeJobPartial(name="MEGRE_NativeToT1w_2mm_ChiPara", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso2mm.chiParamagnetic_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso2mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.megre_NativeToT1w_2mm_QSM = PipeJobPartial(name="MEGRE_NativeToT1w_2mm_QSM", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.QSM,
                                          output=session.subjectPaths.megre.bids_processed.iso2mm.QSM_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso2mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)



        # To MNI
        self.megre_NativeToMNI_2mm_ChiDia = PipeJobPartial(name="MEGRE_NativeToMNI_2mm_ChiDia", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso2mm.chiDiamagnetic_toMNI,
                                          reference=self.templates.mni152_2mm,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso2mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso2mm.MNI_1Warp],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.megre_NativeToMNI_2mm_ChiPara = PipeJobPartial(name="MEGRE_NativeToMNI_2mm_ChiPara", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso2mm.chiParamagnetic_toMNI,
                                          reference=self.templates.mni152_2mm,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso2mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso2mm.MNI_1Warp],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.megre_NativeToMNI_2mm_QSM = PipeJobPartial(name="MEGRE_NativeToMNI_2mm_QSM", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.QSM,
                                          output=session.subjectPaths.megre.bids_processed.iso2mm.QSM_toMNI,
                                          reference=self.templates.mni152_2mm,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso2mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso2mm.MNI_1Warp],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

    def setup(self) -> bool:
        self.addPipeJobs()
        return True
    
class MEGRE_ToT1wMNI_3mm(ProcessingModule):
    requiredModalities = ["T1w", "megre"]
    moduleDependencies = ["MEGRE_ToT1wNative", "T1w_3mm"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)

        self.megre_NativeToT1w_3mm_ChiDia = PipeJobPartial(name="MEGRE_NativeToT1w_3mm_ChiDia", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso3mm.chiDiamagnetic_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso3mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.megre_NativeToT1w_3mm_ChiPara = PipeJobPartial(name="MEGRE_NativeToT1w_3mm_ChiPara", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso3mm.chiParamagnetic_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso3mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.megre_NativeToT1w_3mm_QSM = PipeJobPartial(name="MEGRE_NativeToT1w_3mm_QSM", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.QSM,
                                          output=session.subjectPaths.megre.bids_processed.iso3mm.QSM_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso3mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)



        # To MNI
        self.megre_NativeToMNI_3mm_ChiDia = PipeJobPartial(name="MEGRE_NativeToMNI_3mm_ChiDia", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso3mm.chiDiamagnetic_toMNI,
                                          reference=self.templates.mni152_3mm,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso3mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso3mm.MNI_1Warp],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.megre_NativeToMNI_3mm_ChiPara = PipeJobPartial(name="MEGRE_NativeToMNI_3mm_ChiPara", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso3mm.chiParamagnetic_toMNI,
                                          reference=self.templates.mni152_3mm,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso3mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso3mm.MNI_1Warp],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.megre_NativeToMNI_3mm_QSM = PipeJobPartial(name="MEGRE_NativeToMNI_3mm_QSM", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.QSM,
                                          output=session.subjectPaths.megre.bids_processed.iso3mm.QSM_toMNI,
                                          reference=self.templates.mni152_3mm,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso3mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso3mm.MNI_1Warp],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

    def setup(self) -> bool:
        self.addPipeJobs()
        return True