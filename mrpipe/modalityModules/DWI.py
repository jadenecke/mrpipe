from mrpipe.Helper import Helper
from mrpipe.Toolboxes.FSL.FSLMaths import FSLMaths
from mrpipe.Toolboxes.FSL.Merge import Merge
from mrpipe.Toolboxes.FSL.topup import TOPUP
from mrpipe.Toolboxes.MRtrix3.mrconvert import MRCONVERTTOMIF, MRCONVERTTONIFTI
from mrpipe.Toolboxes.MRtrix3.dwidenoise import DWIDENOISE
from mrpipe.Toolboxes.MRtrix3.mrdegibbs import MRDEGIBBS
from mrpipe.Toolboxes.MRtrix3.dwiextract import DWIEXTRACTFIRSTB0, DWIEXTRACTMEANB0
from mrpipe.Toolboxes.standalone.HDBet import HDBET
from mrpipe.Toolboxes.standalone.QCVis import QCVis
from mrpipe.Toolboxes.standalone.QCVisWithoutMask import QCVisWithoutMask
from mrpipe.Toolboxes.standalone.generateB0forTopup import B0FORTOPUP
from mrpipe.modalityModules.ProcessingModule import ProcessingModule
from functools import partial
from mrpipe.schedueler.PipeJob import PipeJob
from mrpipe.schedueler import Scheduler
import os


# INFO: field encoding direction from DWI json sidecar, i.e. PhaseEncodingDirection field and its differences for sagittal and axial acquisition schemes:
# https://neurostars.org/t/phaseencodingdirection-in-json-file/20259

# TIP 1: If reverse phase encoding is 4D, it needs to include bval and bvec file, if it only is 3D I assume its b0

class DWI_base(ProcessingModule):
    requiredModalities = ["dwi", "T1w"]
    moduleDependencies = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Scheduler.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=4, partition=self.inputArgs.partition)
        #TODO: PARENTS stuff for n-cpus is not handled at all!
        self.dwi_mergeMif = PipeJobPartial(name="dwi_mergeMif", job=SchedulerPartial(
            taskList=[MRCONVERTTOMIF(dwiin=session.subjectPaths.dwi.bids.dwi,
                                     mifOut=session.subjectPaths.dwi.bids_processed.basemif,
                                     session=session) for session in self.sessions]), env=self.envs.envMRtrixFSL)

        self.dwi_denoise = PipeJobPartial(name="dwi_denoise", job=SchedulerPartial(
            taskList=[DWIDENOISE(inputImage=session.subjectPaths.dwi.bids_processed.basemif,
                                 outputImage=session.subjectPaths.dwi.bids_processed.denoised,
                                 session=session) for session in self.sessions]), env=self.envs.envMRtrixFSL)

        self.dwi_degibbs = PipeJobPartial(name="dwi_degibbs", job=SchedulerPartial(
            taskList=[MRDEGIBBS(inputImage=session.subjectPaths.dwi.bids_processed.denoised,
                                outputImage=session.subjectPaths.dwi.bids_processed.degibbs,
                                session=session) for session in self.sessions]), env=self.envs.envMRtrixFSL)

        self.dwi_extractFirstb0 = PipeJobPartial(name="dwi_extractFirstb0", job=SchedulerPartial(
            taskList=[DWIEXTRACTFIRSTB0(inputImage=session.subjectPaths.dwi.bids_processed.denoised,
                                        outputB0=session.subjectPaths.dwi.bids_processed.firstb0,
                                        session=session) for session in self.sessions]), env=self.envs.envMRtrixFSL)

        self.b0qc = PipeJobPartial(name="dwi_extractFirstb0", job=SchedulerPartial(
            taskList=[DWIEXTRACTFIRSTB0(inputImage=session.subjectPaths.dwi.bids_processed.denoised,
                                        outputB0=session.subjectPaths.dwi.bids_processed.firstb0,
                                        session=session) for session in self.sessions]), env=self.envs.envMRtrixFSL)

        self.dwi_QCFirstb0 = PipeJobPartial(name="dwi_QCFirstb0", job=SchedulerPartial(
            taskList=[QCVisWithoutMask(infile=session.subjectPaths.dwi.bids_processed.firstb0,
                                       image=session.subjectPaths.dwi.Meta_QC.firstb0,
                                       zoom=1,
                                       session=session) for session in self.sessions]), env=self.envs.envQCVis)

        self.dwi_b0ForTopup = PipeJobPartial(name="dwi_extractFirstb0", job=SchedulerPartial(
            taskList=[B0FORTOPUP(inputDWI=session.subjectPaths.dwi.bids.dwi,
                                 inputUnringed=session.subjectPaths.dwi.bids_processed.degibbs,
                                 inputT1w=session.subjectPaths.T1w.bids.T1w.imagePath,
                                 inputB0=session.subjectPaths.dwi.bids_processed.firstb0,
                                 outputB0=session.subjectPaths.dwi.bids_processed.b0ForTopup,
                                 synthB0DiscoSIF=self.libpaths.SynB0Disco,
                                 acqparams=session.subjectPaths.dwi.bids_processed.acqparams,
                                 index=session.subjectPaths.dwi.bids_processed.index,
                                 freesurferLicense=self.libpaths.freesurferLicense,
                                 temp_dir=self.basepaths.scratch.join(f"{session.subjectName}_{session.name}_SynB0Disco", isDirectory=True),
                                 session=session) for session in self.sessions]), env=self.envs.envMRtrixFSLSingularity)

        self.dwi_mergeb0 = PipeJobPartial(name="dwi_mergeb0", job=SchedulerPartial(
            taskList=[Merge(infile=[session.subjectPaths.dwi.bids_processed.firstb0,
                                    session.subjectPaths.dwi.bids_processed.b0ForTopup],
                            output=session.subjectPaths.dwi.bids_processed.b0MergeForTopup,
                            clobber=False,
                            session=session) for session in self.sessions]), env=self.envs.envFSL)

        self.b0qc = PipeJobPartial(name="dwi_extractFirstb0", job=SchedulerPartial(
            taskList=[TOPUP(inputImage=session.subjectPaths.dwi.bids_processed.denoised,
                            acqparam=session.subjectPaths.dwi.bids_processed.acqparams,
                            config=os.path.join(Helper.get_libpath(), "Toolboxes", "configs", "b02b0_1.cnf"),
                            outputDir=session.subjectPaths.dwi.bids_processed.topup_out_basename,
                            outMovepar=session.subjectPaths.dwi.bids_processed.topup_movepar,
                            outFieldcoef=session.subjectPaths.dwi.bids_processed.topup_fieldcoef,
                            outputImage=session.subjectPaths.dwi.bids_processed.topup_b0_hifi,
                            session=session) for session in self.sessions]), env=self.envs.envMRtrixFSL)

        self.dwi_mergeMif = PipeJobPartial(name="dwi_mergeMif", job=SchedulerPartial(
            taskList=[MRCONVERTTONIFTI(dwiIn=session.subjectPaths.dwi.bids.dwi,
                                       imageOut=session.subjectPaths.dwi.bids_processed.degibbs_nifti,
                                       bavlOut=session.subjectPaths.dwi.bids_processed.degibbs_bval,
                                       bevcOut=session.subjectPaths.dwi.bids_processed.degibbs_bvec,
                                       session=session) for session in self.sessions]), env=self.envs.envMRtrixFSL)

        self.T1w_base_cat12_GMWMMask = PipeJobPartial(name="T1w_base_cat12_GMWMMask", job=SchedulerPartial(
            taskList=[FSLMaths(infiles=[session.subjectPaths.dwi.bids_processed.topup_b0_hifi],
                               output=session.subjectPaths.dwi.bids_processed.topup_b0_hifi_mean,
                               mathString="{} -Tmean",
                               session=session) for session in self.sessions]), env=self.envs.envFSL)

        self.hdbet = PipeJobPartial(name="T1w_base_hdbet", job=SchedulerPartial(
            taskList=[HDBET(infile=session.subjectPaths.dwi.bids_processed.topup_b0_hifi_mean,
                            brain=session.subjectPaths.dwi.bids_processed.topup_b0_hifi_mean_stripped,
                            mask=session.subjectPaths.dwi.bids_processed.topup_b0_hifi_mean_mask,
                            useGPU=self.inputArgs.ngpus > 0,
                            session=session) for session in self.sessions],
            ngpus=self.inputArgs.ngpus, memPerCPU=2, cpusPerTask=4, minimumMemPerNode=12), env=self.envs.envHDBET)

        self.qc_vis_hdbet = PipeJobPartial(name="T1w_base_QC_slices_hdbet", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.dwi.bids_processed.topup_b0_hifi_mean,
                            mask=session.subjectPaths.dwi.bids_processed.topup_b0_hifi_mean_mask,
                            image=session.subjectPaths.dwi.Meta_QC.topup_bmask, contrastAdjustment=True,
                            session=session) for session in self.sessions]), env=self.envs.envQCVis)

    def setup(self) -> bool:
        self.addPipeJobs()
        return True
