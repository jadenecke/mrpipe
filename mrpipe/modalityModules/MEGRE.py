from mrpipe.modalityModules.ProcessingModule import ProcessingModule
from functools import partial
from mrpipe.schedueler.PipeJob import PipeJob
from mrpipe.schedueler import Slurm
from mrpipe.Toolboxes.FSL.Merge import Merge
from mrpipe.Toolboxes.ANTSTools.N4BiasFieldCorrect import N4BiasFieldCorrect
from mrpipe.Toolboxes.standalone.QCVis import QCVis
from mrpipe.Toolboxes.ANTSTools.AntsRegistrationSyN import AntsRegistrationSyN
from mrpipe.Toolboxes.ANTSTools.AntsApplyTransform import AntsApplyTransforms
from mrpipe.Toolboxes.standalone.cp import CP
from mrpipe.Toolboxes.QSM.ChiSeperation import ChiSeperation
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

        self.megre_base_bmToMEGRE = PipeJobPartial(name="MEGRE_base_chiNegToT1w", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                                          output=session.subjectPaths.megre.bids_processed.brainMask_toMEGRE,
                                          reference=session.subjectPaths.megre.bids.megre.magnitude[0].imagePath,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="NearestNeighbor",
                                          useInverseTransform=True,
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envANTS)

        # Step 1: Merge phase and magnitude to 4d Images
        self.mergePhase4D = PipeJobPartial(name="MEGRE_base_mergePhase4D", job=SchedulerPartial(
            taskList=[Merge(infile=session.subjectPaths.megre.bids.megre.get_phase_paths(),
                            output=session.subjectPaths.megre.bids_processed.phase4D,
                            clobber=False) for session in
                      self.sessions],
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=4, minimumMemPerNode=8),
                                    env=self.envs.envFSL)

        self.mergeMagnitude4D = PipeJobPartial(name="MEGRE_base_mergeMagnitude4D", job=SchedulerPartial(
            taskList=[Merge(infile=session.subjectPaths.megre.bids.megre.get_magnitude_paths(),
                            output=session.subjectPaths.megre.bids_processed.magnitude4d,
                            clobber=False) for session in
                      self.sessions],
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=4, minimumMemPerNode=8),
                                           env=self.envs.envFSL)

        # Step 2: perform Chi-seperation
        self.chiSep = PipeJobPartial(name="MEGRE_base_chiSep", job=SchedulerPartial(
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

    def setup(self) -> bool:
        self.addPipeJobs()
        return True

