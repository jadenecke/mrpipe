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



class FLAIR_base(ProcessingModule):
    requiredModalities = ["T1w", "flair"]
    moduleDependencies = ["T1w_base"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)

        self.flair_native_copy = PipeJobPartial(name="FLAIR_native_copy", job=SchedulerPartial(
            taskList=[CP(infile=session.subjectPaths.flair.bids.flair,
                         outfile=session.subjectPaths.flair.bids_processed.flair) for session in
                      self.sessions]), env=self.envs.envMRPipe)

        #copy flair masks is exists
        self.flair_native_copyWMH = PipeJobPartial(name="flair_native_copyWMH", job=SchedulerPartial(
            taskList=[CP(infile=session.subjectPaths.flair.bids.WMHMask,
                         outfile=session.subjectPaths.flair.bids_processed.WMHMask) for session in
                      self.sessions if session.subjectPaths.flair.bids.WMHMask is not None]), env=self.envs.envMRPipe)

        # Step 1: N4 Bias corrections
        self.N4biasCorrect = PipeJobPartial(name="FLAIR_base_N4biasCorrect", job=SchedulerPartial(
            taskList=[N4BiasFieldCorrect(infile=session.subjectPaths.flair.bids.flair,
                                         outfile=session.subjectPaths.flair.bids_processed.N4BiasCorrected) for session in
                      self.sessions]), env=self.envs.envANTS)

        #Step 2: Create Flair mask if it does not exist
        self.flair_native_lstai = PipeJobPartial(name="flair_native_lstai", job=SchedulerPartial(
            taskList=[LSTAI(t1w=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                         flair=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
                            lstaiSIF=self.libpaths.lstai_singularityContainer,
                            tempDir=session.subjectPaths.flair.bids_processed.lstai_tmpDir,
                            outputDir=session.subjectPaths.flair.bids_processed.lstai_outputDir,
                            outputFiles=[session.subjectPaths.flair.bids_processed.lstai_outputMask,
                                         session.subjectPaths.flair.bids_processed.lstai_outputMaskProbabilityTemp]) for session in
                      self.sessions if session.subjectPaths.flair.bids.WMHMask is None],
            ngpus=self.inputArgs.ngpus), env=self.envs.envSingularity)

        self.flair_native_copyWMHlstai = PipeJobPartial(name="flair_native_copyWMHlstai", job=SchedulerPartial(
            taskList=[CP(infile=session.subjectPaths.flair.bids_processed.lstai_outputMaskProbabilityTemp,
                         outfile=session.subjectPaths.flair.bids_processed.lstai_outputMaskProbability) for session in
                      self.sessions if session.subjectPaths.flair.bids.WMHMask is None]), env=self.envs.envMRPipe)

        # Flair mask QC
        self.flair_native_qc_vis_wmhMask = PipeJobPartial(name="FLAIR_native_slices_wmhMask", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
                            mask=session.subjectPaths.flair.bids_processed.lstai_outputMask,
                            image=session.subjectPaths.flair.meta_QC.wmhMask, contrastAdjustment=False,
                            outline=False, transparency=True, zoom=1, sliceNumber=12) for session in
                      self.sessions]), env=self.envs.envQCVis)

    def setup(self) -> bool:
        self.addPipeJobs()
        return True

class FLAIR_ToT1wNative(ProcessingModule):
    requiredModalities = ["T1w", "flair"]
    moduleDependencies = ["FLAIR_base", "T1w_base"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)

        self.flair_NativeToT1w = PipeJobPartial(name="FLAIR_native_NativeToT1", job=SchedulerPartial(
            taskList=[AntsRegistrationSyN(fixed=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                          moving=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
                                          outprefix=session.subjectPaths.flair.bids_processed.toT1w_prefix,
                                          expectedOutFiles=[session.subjectPaths.flair.bids_processed.toT1w_toT1w,
                                                            session.subjectPaths.flair.bids_processed.toT1w_InverseWarped,
                                                            session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          ncores=2, dim=3, type="a") for session in self.sessions],
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=2, minimumMemPerNode=4),
                                                  env=self.envs.envANTS)

        self.flair_native_qc_vis_toT1w = PipeJobPartial(name="FLAIR_native_slices_toT1w", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.flair.bids_processed.toT1w_toT1w,
                            mask=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                            image=session.subjectPaths.flair.meta_QC.ToT1w_native_slices, contrastAdjustment=False,
                            outline=True, transparency=True, zoom=1) for session in
                      self.sessions]), env=self.envs.envQCVis)

        self.flair_native_WMHToT1w = PipeJobPartial(name="FLAIR_native_WMHToT1w", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids.WMHMask,
                                          output=session.subjectPaths.flair.bids_processed.WMHMask_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

    def setup(self) -> bool:

        self.addPipeJobs()
        return True

class FLAIR_ToT1wMNI_1mm(ProcessingModule):
    requiredModalities = ["T1w", "flair"]
    moduleDependencies = ["FLAIR_ToT1wNative", "T1w_1mm"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)

        self.flair_NativeToT1w_1mm = PipeJobPartial(name="FLAIR_NativeToT1w_1mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
                                          output=session.subjectPaths.flair.bids_processed.iso1mm.baseimage,
                                          reference=session.subjectPaths.T1w.bids_processed.iso1mm.baseimage,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.flair_Native_WMHToT1w_1mm = PipeJobPartial(name="FLAIR_Native_WMHToT1w_1mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.WMHMask,
                                          output=session.subjectPaths.flair.bids_processed.iso1mm.WMHMask_toT1,
                                          reference=session.subjectPaths.T1w.bids_processed.iso1mm.baseimage,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)


        #To MNI
        self.flair_NativeToMNI_1mm = PipeJobPartial(name="FLAIR_NativeToMNI_1mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
                                          output=session.subjectPaths.flair.bids_processed.iso1mm.toMNI,
                                          reference=self.templates.mni152_1mm,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1Warp],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.flair_Native_WMHToMNI_1mm = PipeJobPartial(name="FLAIR_Native_WMHToMNI_1mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.WMHMask,
                                          output=session.subjectPaths.flair.bids_processed.iso1mm.WMHMask_toMNI,
                                          reference=self.templates.mni152_1mm,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1Warp],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)


    def setup(self) -> bool:



        self.addPipeJobs()
        return True


class FLAIR_ToT1wMNI_1p5mm(ProcessingModule):
    requiredModalities = ["T1w", "flair"]
    moduleDependencies = ["FLAIR_ToT1wNative", "T1w_1p5mm"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)

        self.flair_NativeToT1w_1p5mm = PipeJobPartial(name="FLAIR_NativeToT1w_1p5mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
                                          output=session.subjectPaths.flair.bids_processed.iso1p5mm.baseimage,
                                          reference=session.subjectPaths.T1w.bids_processed.iso1p5mm.baseimage,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.flair_Native_WMHToT1w_1p5mm = PipeJobPartial(name="FLAIR_Native_WMHToT1w_1p5mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.WMHMask,
                                          output=session.subjectPaths.flair.bids_processed.iso1p5mm.WMHMask_toT1,
                                          reference=session.subjectPaths.T1w.bids_processed.iso1p5mm.baseimage,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        # To MNI
        self.flair_NativeToMNI_1p5mm = PipeJobPartial(name="FLAIR_NativeToMNI_1p5mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed,
                                          output=session.subjectPaths.flair.bids_processed.iso1p5mm.toMNI,
                                          reference=self.templates.mni152_1p5mm,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_1Warp],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.flair_Native_WMHToMNI_1p5mm = PipeJobPartial(name="FLAIR_Native_WMHToMNI_1p5mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.WMHMask,
                                          output=session.subjectPaths.flair.bids_processed.iso1p5mm.WMHMask_toMNI,
                                          reference=self.templates.mni152_1p5mm,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_1Warp],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)


    def setup(self) -> bool:


        self.addPipeJobs()
        return True

class FLAIR_ToT1wMNI_2mm(ProcessingModule):
    requiredModalities = ["T1w", "flair"]
    moduleDependencies = ["FLAIR_ToT1wNative", "T1w_2mm"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)

        self.flair_NativeToT1w_2mm = PipeJobPartial(name="FLAIR_NativeToT1w_2mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
                                          output=session.subjectPaths.flair.bids_processed.iso2mm.baseimage,
                                          reference=session.subjectPaths.T1w.bids_processed.iso2mm.baseimage,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.flair_Native_WMHToT1w_2mm = PipeJobPartial(name="FLAIR_Native_WMHToT1w_2mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.WMHMask,
                                          output=session.subjectPaths.flair.bids_processed.iso2mm.WMHMask_toT1,
                                          reference=session.subjectPaths.T1w.bids_processed.iso2mm.baseimage,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        # To MNI
        self.flair_NativeToMNI_2mm = PipeJobPartial(name="FLAIR_NativeToMNI_2mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
                                          output=session.subjectPaths.flair.bids_processed.iso2mm.toMNI,
                                          reference=self.templates.mni152_2mm,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso2mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso2mm.MNI_1Warp],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.flair_Native_WMHToMNI_2mm = PipeJobPartial(name="FLAIR_Native_WMHToMNI_2mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.WMHMask,
                                          output=session.subjectPaths.flair.bids_processed.iso2mm.WMHMask_toMNI,
                                          reference=self.templates.mni152_2mm,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso2mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso2mm.MNI_1Warp],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)


    def setup(self) -> bool:


        self.addPipeJobs()
        return True


class FLAIR_ToT1wMNI_3mm(ProcessingModule):
    requiredModalities = ["T1w", "flair"]
    moduleDependencies = ["FLAIR_ToT1wNative", "T1w_3mm"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=2, minimumMemPerNode=4)

        self.flair_NativeToT1w_3mm = PipeJobPartial(name="FLAIR_NativeToT1w_3mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
                                          output=session.subjectPaths.flair.bids_processed.iso3mm.baseimage,
                                          reference=session.subjectPaths.T1w.bids_processed.iso3mm.baseimage,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.flair_Native_WMHToT1w_3mm = PipeJobPartial(name="FLAIR_Native_WMHToT1w_3mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.WMHMask,
                                          output=session.subjectPaths.flair.bids_processed.iso3mm.WMHMask_toT1,
                                          reference=session.subjectPaths.T1w.bids_processed.iso3mm.baseimage,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        # To MNI
        self.flair_NativeToMNI_3mm = PipeJobPartial(name="FLAIR_NativeToMNI_3mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
                                          output=session.subjectPaths.flair.bids_processed.iso3mm.toMNI,
                                          reference=self.templates.mni152_3mm,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso3mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso3mm.MNI_1Warp],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        self.flair_Native_WMHToMNI_3mm = PipeJobPartial(name="FLAIR_Native_WMHToMNI_3mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.WMHMask,
                                          output=session.subjectPaths.flair.bids_processed.iso3mm.WMHMask_toMNI,
                                          reference=self.templates.mni152_3mm,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso3mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso3mm.MNI_1Warp],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

    def setup(self) -> bool:


        self.addPipeJobs()
        return True