from mrpipe.Helper import Helper
from mrpipe.Toolboxes.ANTSTools.AntsApplyTransform import AntsApplyTransforms
from mrpipe.Toolboxes.ANTSTools.AntsRegistrationSyN import AntsRegistrationSyN
from mrpipe.Toolboxes.FSL.FSLMaths import FSLMaths
from mrpipe.Toolboxes.FSL.FSLStats import FSLStats
from mrpipe.Toolboxes.FSL.FSLreorient2std import FSLreorient2std
from mrpipe.Toolboxes.FSL.Merge import Merge
from mrpipe.Toolboxes.FSL.dtifit import DTIFIT
from mrpipe.Toolboxes.FSL.eddy import EDDYDiffusion
from mrpipe.Toolboxes.FSL.eddyQC import EDDYDiffusionQC
from mrpipe.Toolboxes.FSL.topup import TOPUP
from mrpipe.Toolboxes.MRtrix3.dwi2fod import DWI2FOD
from mrpipe.Toolboxes.MRtrix3.dwi2response import DWI2RESPONSE
from mrpipe.Toolboxes.MRtrix3.dwi5ttgen import DWI5TTGEN
from mrpipe.Toolboxes.MRtrix3.dwiDenoiseDegibbsForNifti import MRIDWIDENOISEDEGIBBSFromNifti
from mrpipe.Toolboxes.MRtrix3.dwibiascorrect import DWIBiascorrect
from mrpipe.Toolboxes.MRtrix3.fibertracking2connectome import FIBERTRACKING2CONNECTOME
from mrpipe.Toolboxes.MRtrix3.mrconvert import MRCONVERTTOMIF, MRCONVERTTONIFTI
from mrpipe.Toolboxes.MRtrix3.dwidenoise import DWIDENOISE
from mrpipe.Toolboxes.MRtrix3.mrdegibbs import MRDEGIBBS
from mrpipe.Toolboxes.MRtrix3.dwiextract import DWIEXTRACTFIRSTB0, DWIEXTRACTMEANB0, DWIEXTRACTTRACE, DWIEXTRACTForDTI, DWIEXTRACTFIRSTB0FromNifti
from mrpipe.Toolboxes.MRtrix3.mtnormalise import MTNORMALISE
from mrpipe.Toolboxes.MRtrix3.sh2peaks import SH2PEAKS
from mrpipe.Toolboxes.standalone.ExtractAtlasValues import ExtractAtlasValues
from mrpipe.Toolboxes.standalone.HDBet import HDBET
from mrpipe.Toolboxes.standalone.QCVis import QCVis
from mrpipe.Toolboxes.standalone.QCVisWithoutMask import QCVisWithoutMask
from mrpipe.Toolboxes.standalone.Tracking import Tracking
from mrpipe.Toolboxes.standalone.Tractseg import Tractseg
from mrpipe.Toolboxes.standalone.generateB0forTopup import B0FORTOPUP
from mrpipe.meta.PathClass import Path
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
    moduleDependencies = ["T1w_base"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Scheduler.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=4, partition=self.inputArgs.partition)

        # self.dwi_base_mergeMif = PipeJobPartial(name="dwi_base_mergeMif", job=SchedulerPartial(
        #     taskList=[MRCONVERTTOMIF(inputImage=session.subjectPaths.dwi.bids.dwi.getImagepath(),
        #                              inputBval=session.subjectPaths.dwi.bids.dwi.get_bval_path(),
        #                              inputBvec=session.subjectPaths.dwi.bids.dwi.get_bvec_path(),
        #                              inputJson=session.subjectPaths.dwi.bids.dwi.get_image_sidecar(),
        #                              mifOut=session.subjectPaths.dwi.bids_processed.basemif,
        #                              session=session, name="dwi_base_mergeMif") for session in self.sessions]), env=self.envs.envMRtrixFSL)
        #
        # self.dwi_base_denoise = PipeJobPartial(name="dwi_base_denoise", job=SchedulerPartial(
        #     taskList=[DWIDENOISE(inputImage=session.subjectPaths.dwi.bids_processed.basemif,
        #                          outputImage=session.subjectPaths.dwi.bids_processed.denoised,
        #                          session=session) for session in self.sessions],
        #     cpusPerTask=6, memPerCPU=2, minimumMemPerNode=12), env=self.envs.envMRtrixFSL)
        #
        # self.dwi_base_degibbs = PipeJobPartial(name="dwi_base_degibbs", job=SchedulerPartial(
        #     taskList=[MRDEGIBBS(inputImage=session.subjectPaths.dwi.bids_processed.denoised,
        #                         outputImage=session.subjectPaths.dwi.bids_processed.degibbs,
        #                         session=session) for session in self.sessions],
        #     cpusPerTask=6, memPerCPU=2, minimumMemPerNode=12), env=self.envs.envMRtrixFSL)
        #
        # self.dwi_base_convertNifti = PipeJobPartial(name="dwi_base_convertNifti", job=SchedulerPartial(
        #     taskList=[MRCONVERTTONIFTI(dwiIn=session.subjectPaths.dwi.bids_processed.degibbs,
        #                                imageOut=session.subjectPaths.dwi.bids_processed.degibbs_nifti,
        #                                bavlOut=session.subjectPaths.dwi.bids_processed.degibbs_bval,
        #                                bevcOut=session.subjectPaths.dwi.bids_processed.degibbs_bvec,
        #                                session=session) for session in self.sessions]), env=self.envs.envMRtrixFSL)

        self.dwi_denoiseDegibbsFromNifti = PipeJobPartial(name="dwi_denoiseDegibbsFromNifti", job=SchedulerPartial(
            taskList=[MRIDWIDENOISEDEGIBBSFromNifti(inputImage=session.subjectPaths.dwi.bids.dwi.getImagepath(),
                      inputJson=session.subjectPaths.dwi.bids.dwi.get_image_sidecar(),
                      inputBval=session.subjectPaths.dwi.bids.dwi.get_bval_path(),
                      inputBvec=session.subjectPaths.dwi.bids.dwi.get_bvec_path(),
                      outputDenoised=session.subjectPaths.dwi.bids_processed.degibbs_nifti.imagePath,
                      outputjson=session.subjectPaths.dwi.bids_processed.degibbs_nifti.jsonPath,
                      outputBval=session.subjectPaths.dwi.bids_processed.degibbs_bval,
                      outputBvec=session.subjectPaths.dwi.bids_processed.degibbs_bvec,
                      session=session) for session in self.sessions],
        cpusPerTask=6, memPerCPU=2, minimumMemPerNode=12), env=self.envs.envMRtrixFSL)


        self.dwi_base_extractFirstb0FromNifti = PipeJobPartial(name="dwi_base_extractFirstb0FromNifti", job=SchedulerPartial(
            taskList=[DWIEXTRACTFIRSTB0FromNifti(inputImage=session.subjectPaths.dwi.bids_processed.degibbs_nifti.imagePath,
                                                 inputJson=session.subjectPaths.dwi.bids_processed.degibbs_nifti.jsonPath,
                                                 inputBval=session.subjectPaths.dwi.bids_processed.degibbs_bval,
                                                 inputBvec=session.subjectPaths.dwi.bids_processed.degibbs_bvec,
                                        outputB0=session.subjectPaths.dwi.bids_processed.firstb0,
                                        session=session) for session in self.sessions]), env=self.envs.envMRtrixFSL)

        self.dwi_base_QCFirstb0 = PipeJobPartial(name="dwi_base_QCFirstb0", job=SchedulerPartial(
            taskList=[QCVisWithoutMask(infile=session.subjectPaths.dwi.bids_processed.firstb0,
                                       image=session.subjectPaths.dwi.meta_QC.firstb0,
                                       zoom=1,
                                       session=session) for session in self.sessions]), env=self.envs.envQCVis)

        self.dwi_base_b0ForTopup = PipeJobPartial(name="dwi_base_b0ForTopup", job=SchedulerPartial(
            taskList=[B0FORTOPUP(inputDWI=session.subjectPaths.dwi.bids.dwi,
                                 inputT1w=session.subjectPaths.T1w.bids.T1w.imagePath,
                                 inputB0=session.subjectPaths.dwi.bids_processed.firstb0,
                                 outputB0=session.subjectPaths.dwi.bids_processed.b0ForTopup,
                                 Synb0WrapperPath=session.subjectPaths.dwi.bids_processed.synB0_script,
                                 synthB0DiscoSIF=self.libpaths.SynB0Disco,
                                 acqparams=session.subjectPaths.dwi.bids_processed.acqparams,
                                 index=session.subjectPaths.dwi.bids_processed.index,
                                 freesurferLicense=self.libpaths.freesurferLicense,
                                 temp_dir=self.basepaths.scratch.join(f"{session.subjectName}_{session.name}_SynB0Disco", isDirectory=True),
                                 session=session) for session in self.sessions],
            cpusPerTask=6, memPerCPU=3, minimumMemPerNode=16),
                                                  env=self.envs.envMRtrixFSLSingularity)

        self.dwi_base_mergeb0 = PipeJobPartial(name="dwi_base_mergeb0", job=SchedulerPartial(
            taskList=[Merge(infile=[session.subjectPaths.dwi.bids_processed.firstb0,
                                    session.subjectPaths.dwi.bids_processed.b0ForTopup],
                            output=session.subjectPaths.dwi.bids_processed.b0MergeForTopup,
                            clobber=False,
                            session=session) for session in self.sessions]), env=self.envs.envFSL)

        self.dwi_base_topup = PipeJobPartial(name="dwi_base_topup", job=SchedulerPartial(
            taskList=[TOPUP(inputImage=session.subjectPaths.dwi.bids_processed.b0MergeForTopup,
                            acqparam=session.subjectPaths.dwi.bids_processed.acqparams,
                            config=Path(os.path.join(Helper.get_libpath(), "Toolboxes", "configs", "b02b0_1.cnf")),
                            outputDir=session.subjectPaths.dwi.bids_processed.topup_out_basename,
                            outMovepar=session.subjectPaths.dwi.bids_processed.topup_movepar,
                            outFieldcoef=session.subjectPaths.dwi.bids_processed.topup_fieldcoef,
                            outputImage=session.subjectPaths.dwi.bids_processed.topup_b0_hifi,
                            session=session) for session in self.sessions],
            cpusPerTask=6, memPerCPU=3, minimumMemPerNode=16), env=self.envs.envMRtrixFSL)

        self.dwi_base_meanb0ForEddy = PipeJobPartial(name="dwi_base_meanb0ForEddy", job=SchedulerPartial(
            taskList=[FSLMaths(infiles=[session.subjectPaths.dwi.bids_processed.topup_b0_hifi],
                               output=session.subjectPaths.dwi.bids_processed.topup_b0_hifi_mean,
                               mathString="{} -Tmean",
                               session=session) for session in self.sessions]), env=self.envs.envFSL)

        self.dwi_base_hdbet_meanb0ForEddy = PipeJobPartial(name="dwi_base_hdbet_meanb0ForEddy", job=SchedulerPartial(
            taskList=[HDBET(infile=session.subjectPaths.dwi.bids_processed.topup_b0_hifi_mean,
                            brain=session.subjectPaths.dwi.bids_processed.topup_b0_hifi_mean_stripped,
                            mask=session.subjectPaths.dwi.bids_processed.topup_b0_hifi_mean_mask,
                            useGPU=self.inputArgs.ngpus > 0,
                            session=session) for session in self.sessions],
            ngpus=self.inputArgs.ngpus, memPerCPU=2, cpusPerTask=4, minimumMemPerNode=12), env=self.envs.envHDBET)

        self.dwi_base_qc_vis_hdbet = PipeJobPartial(name="dwi_base_qc_vis_hdbet", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.dwi.bids_processed.topup_b0_hifi_mean,
                            mask=session.subjectPaths.dwi.bids_processed.topup_b0_hifi_mean_mask,
                            image=session.subjectPaths.dwi.meta_QC.topup_bmask, contrastAdjustment=True,
                            session=session) for session in self.sessions]), env=self.envs.envQCVis)

        self.dwi_base_eddy = PipeJobPartial(name="dwi_base_eddy", job=SchedulerPartial(
            taskList=[EDDYDiffusion(inputImage=session.subjectPaths.dwi.bids_processed.degibbs_nifti,
                                    inputMask=session.subjectPaths.dwi.bids_processed.topup_b0_hifi_mean_mask,
                                    acqparam=session.subjectPaths.dwi.bids_processed.acqparams,
                                    index=session.subjectPaths.dwi.bids_processed.index,
                                    bval=session.subjectPaths.dwi.bids_processed.degibbs_bval,
                                    bvec=session.subjectPaths.dwi.bids_processed.degibbs_bvec,
                                    topupBasename=session.subjectPaths.dwi.bids_processed.topup_out_basename,
                                    outputBasename=session.subjectPaths.dwi.bids_processed.eddy_out_basename,
                                    expectedOutputList=session.subjectPaths.dwi.bids_processed.eddy_outFileList,
                                    session=session,
                                    repol=True,
                                    data_is_shelled=session.subjectPaths.dwi.bids.dwi.is_shelled,
                                    data_has_slicetiming=session.subjectPaths.dwi.bids.dwi.hasSlicetiming(),
                                    residuals=True,
                                    cnr_maps=True,
                                    sliceMovementCorrection=True) for session in self.sessions],
            ngpus=self.inputArgs.ngpus,
            cpusPerTask=6, memPerCPU=3, minimumMemPerNode=16), env=self.envs.envFSLEddyCuda if self.inputArgs.ngpus else self.envs.envFSL)

        self.dwi_base_eddy_qc = PipeJobPartial(name="dwi_base_eddy_qc", job=SchedulerPartial(
            taskList=[EDDYDiffusionQC(eddy_basename=session.subjectPaths.dwi.bids_processed.eddy_out_basename,
                                      eddy_filelist=session.subjectPaths.dwi.bids_processed.eddy_outFileList,
                                      inputMask=session.subjectPaths.dwi.bids_processed.topup_b0_hifi_mean_mask,
                                      acqparam=session.subjectPaths.dwi.bids_processed.acqparams,
                                      index=session.subjectPaths.dwi.bids_processed.index,
                                      bval=session.subjectPaths.dwi.bids_processed.degibbs_bval,
                                      bvec=session.subjectPaths.dwi.bids_processed.degibbs_bvec,
                                      json=session.subjectPaths.dwi.bids.dwi.get_image_sidecar(),
                                      outputDir=session.subjectPaths.dwi.meta_QC.eddy_qc_Dir,
                                      expectedOutputList=[
                                          session.subjectPaths.dwi.meta_QC.eddy_qc_pdf,
                                          session.subjectPaths.dwi.meta_QC.eddy_qc_json
                                      ],
                                      session=session) for session in self.sessions]), env=self.envs.envFSL)

        self.dwi_base_biascorrect = PipeJobPartial(name="dwi_base_biascorrect", job=SchedulerPartial(
            taskList=[DWIBiascorrect(inputImage=session.subjectPaths.dwi.bids_processed.eddy_imageCorrected,
                                     bval=session.subjectPaths.dwi.bids_processed.degibbs_bval,
                                     bvec=session.subjectPaths.dwi.bids_processed.degibbs_bvec,
                                     outputImage=session.subjectPaths.dwi.bids_processed.N4biascorrected,
                                     scratch=self.basepaths.scratch,
                                     session=session) for session in self.sessions],
            cpusPerTask=6, memPerCPU=2, minimumMemPerNode=12), env=self.envs.envMRtrixFSL)

        self.dwi_base_mergeMifAfterPreproc = PipeJobPartial(name="dwi_base_mergeMifAfterPreproc", job=SchedulerPartial(
            taskList=[MRCONVERTTOMIF(inputImage=session.subjectPaths.dwi.bids_processed.N4biascorrected,
                                     inputBval=session.subjectPaths.dwi.bids_processed.degibbs_bval,
                                     inputBvec=session.subjectPaths.dwi.bids_processed.degibbs_bvec,
                                     inputJson=session.subjectPaths.dwi.bids.dwi.image.jsonPath,
                                     mifOut=session.subjectPaths.dwi.bids_processed.fullyPreprocessedmif,
                                     session=session, name="dwi_base_mergeMifAfterPreproc") for session in self.sessions]), env=self.envs.envMRtrixFSL)

        self.dwi_base_extractMeanb0 = PipeJobPartial(name="dwi_base_extractmeanb0", job=SchedulerPartial(
            taskList=[DWIEXTRACTMEANB0(inputImage=session.subjectPaths.dwi.bids_processed.fullyPreprocessedmif,
                                       outputB0=session.subjectPaths.dwi.bids_processed.meanb0,
                                       session=session) for session in self.sessions]), env=self.envs.envMRtrixFSL)

        self.dwi_base_hdbet_meanb0 = PipeJobPartial(name="dwi_base_hdbet_meanb0", job=SchedulerPartial(
            taskList=[HDBET(infile=session.subjectPaths.dwi.bids_processed.meanb0,
                            brain=session.subjectPaths.dwi.bids_processed.meanb0_stripped,
                            mask=session.subjectPaths.dwi.bids_processed.meanb0_mask,
                            useGPU=self.inputArgs.ngpus > 0,
                            session=session) for session in self.sessions],
            ngpus=self.inputArgs.ngpus, memPerCPU=2, cpusPerTask=4, minimumMemPerNode=12), env=self.envs.envHDBET)

        self.dwi_base_qc_vis_hdbetMeanb0 = PipeJobPartial(name="dwi_base_qc_vis_hdbetMeanb0", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.dwi.bids_processed.meanb0,
                            mask=session.subjectPaths.dwi.bids_processed.meanb0_mask,
                            image=session.subjectPaths.dwi.meta_QC.meanb0_bmask, contrastAdjustment=True,
                            session=session) for session in self.sessions]), env=self.envs.envQCVis)

        self.dwi_base_trace1000 = PipeJobPartial(name="dwi_base_trace1000", job=SchedulerPartial(
            taskList=[DWIEXTRACTTRACE(inputMif=session.subjectPaths.dwi.bids_processed.fullyPreprocessedmif,
                                      outputTrace=session.subjectPaths.dwi.bids_processed.trace1000,
                                      session=session) for session in self.sessions]), env=self.envs.envMRtrixFSL)

        self.dwi_base_extractForDTI = PipeJobPartial(name="dwi_base_extractForDTI", job=SchedulerPartial(
            taskList=[DWIEXTRACTForDTI(inputMif=session.subjectPaths.dwi.bids_processed.fullyPreprocessedmif,
                                       outputImage=session.subjectPaths.dwi.bids_processed.subsetForDTI,
                                       outputBval=session.subjectPaths.dwi.bids_processed.subsetForDIT_bval,
                                       outputBvec=session.subjectPaths.dwi.bids_processed.subsetForDIT_bvec,
                                       session=session) for session in self.sessions]), env=self.envs.envMRtrixFSL)

        self.dwi_dtifit = PipeJobPartial(name="dwi_dtifit", job=SchedulerPartial(
            taskList=[DTIFIT(inputImage=session.subjectPaths.dwi.bids_processed.subsetForDTI,
                             inputMask=session.subjectPaths.dwi.bids_processed.meanb0_mask,
                             bval=session.subjectPaths.dwi.bids_processed.subsetForDIT_bval,
                             bvec=session.subjectPaths.dwi.bids_processed.subsetForDIT_bvec,
                             outputBasename=session.subjectPaths.dwi.bids_processed.dtifit_basename,
                             expectedOutputList=session.subjectPaths.dwi.bids_processed.dtifit_outFileList,
                             session=session) for session in self.sessions]), env=self.envs.envMRtrixFSL)

        #self.dtifit_RD
        self.dwi_base_radialDiffusivity = PipeJobPartial(name="dwi_base_radialDiffusivity", job=SchedulerPartial(
            taskList=[FSLMaths(output=session.subjectPaths.dwi.bids_processed.dtifit_RD,
                                          infiles=[
                                              session.subjectPaths.dwi.bids_processed.dtifit_L2,
                                              session.subjectPaths.dwi.bids_processed.dtifit_L3
                                          ],
                               mathString="{} -add {} -div 2",
                                          session=session) for session in self.sessions],
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=3, minimumMemPerNode=4), env=self.envs.envANTS)

        self.dwi_base_NativeToT1w = PipeJobPartial(name="dwi_base_NativeToT1", job=SchedulerPartial(
            taskList=[AntsRegistrationSyN(fixed=session.subjectPaths.T1w.bids_processed.hdbet_brain,
                                          moving=session.subjectPaths.dwi.bids_processed.meanb0_stripped,
                                          outprefix=session.subjectPaths.dwi.bids_processed.toT1w_prefix,
                                          expectedOutFiles=[session.subjectPaths.dwi.bids_processed.toT1w_0GenericAffine,
                                                            session.subjectPaths.dwi.bids_processed.toT1w_InverseWarped],
                                          ncores=2, dim=3, type="a",
                                          session=session) for session in self.sessions],
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=3, minimumMemPerNode=4), env=self.envs.envANTS)

        self.dwi_base_qc_vis_toT1w = PipeJobPartial(name="dwi_base_slices_toT1w", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.dwi.bids_processed.meanb0,
                            mask=session.subjectPaths.dwi.bids_processed.toT1w_InverseWarped,
                            image=session.subjectPaths.dwi.meta_QC.ToT1w_native_slices,
                            contrastAdjustment=False,
                            outline=True, transparency=False, zoom=1,
                            session=session) for session in self.sessions]), env=self.envs.envQCVis)

        self.dwi_fromT1w_Schaefer200_17Net = PipeJobPartial(name="DWI_fromT1w_Schaefer200_17Net", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.Schaefer2018_200Parcels_17Networks_order_FSLMNI152,
                                          output=session.subjectPaths.dwi.bids_processed.atlas_Schaefer2018_200Parcels_17Networks_order_FSLMNI152,
                                          reference=session.subjectPaths.dwi.bids_processed.meanb0,
                                          transforms=[session.subjectPaths.dwi.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30,
                                          session=session) for session in self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.dwi_fromT1w_Schaefer200_7Net = PipeJobPartial(name="DWI_fromT1w_Schaefer200_7Net", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.Schaefer2018_200Parcels_7Networks_order_FSLMNI152,
                                          output=session.subjectPaths.dwi.bids_processed.atlas_Schaefer2018_200Parcels_7Networks_order_FSLMNI152,
                                          reference=session.subjectPaths.dwi.bids_processed.meanb0,
                                          transforms=[session.subjectPaths.dwi.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30,
                                          session=session) for session in self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.dwi_fromT1w_Schaefer100_7Net = PipeJobPartial(name="DWI_fromT1w_Schaefer100_7Net", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.Schaefer2018_100Parcels_7Networks_order_FSLMNI152,
                                          output=session.subjectPaths.dwi.bids_processed.atlas_Schaefer2018_100Parcels_7Networks_order_FSLMNI152,
                                          reference=session.subjectPaths.dwi.bids_processed.meanb0,
                                          transforms=[session.subjectPaths.dwi.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30,
                                          session=session) for session in self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.dwi_fromT1w_SynthsegMB101 = PipeJobPartial(name="DWI_fromT1w_SynthsegMB101", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosterior,
                                          output=session.subjectPaths.dwi.bids_processed.atlas_synthsegPosterior,
                                          reference=session.subjectPaths.dwi.bids_processed.meanb0,
                                          transforms=[session.subjectPaths.dwi.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30,
                                          session=session) for session in self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.dwi_fromT1w_JHU_1mm = PipeJobPartial(name="DWI_fromT1w_JHU_1mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.JHU_1mm,
                                          output=session.subjectPaths.dwi.bids_processed.atlas_JHU_1mm,
                                          reference=session.subjectPaths.dwi.bids_processed.meanb0,
                                          transforms=[session.subjectPaths.dwi.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30,
                                          session=session) for session in self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.dwi_fromT1w_HammersmithLobar = PipeJobPartial(name="DWIfromT1w_HammersmithLobar", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.HammersmithLobar,
                                          output=session.subjectPaths.dwi.bids_processed.atlas_HammersmithLobar,
                                          reference=session.subjectPaths.dwi.bids_processed.meanb0,
                                          transforms=[session.subjectPaths.dwi.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30,
                                          session=session) for session in self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.dwi__fromT1w_cat12WM = PipeJobPartial(name="DWI_fromT1w_cat12WM", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1_whiteMatterProbability,
                                          output=session.subjectPaths.dwi.bids_processed.cat12_fromT1_whiteMatterProbability,
                                          reference=session.subjectPaths.dwi.bids_processed.meanb0,
                                          transforms=[session.subjectPaths.dwi.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30,
                                          session=session) for session in self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.dwi_fromT1w_synthsegWMCortical = PipeJobPartial(name="DWI_fromT1w_synthsegWMCortical", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.synthsegWMCortical,
                                          output=session.subjectPaths.dwi.bids_processed.synthsegWMCorticalProbability_fromT1w,
                                          reference=session.subjectPaths.dwi.bids_processed.meanb0,
                                          transforms=[session.subjectPaths.dwi.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30,
                                          session=session) for session in self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.dwi_base_atlas_HammersmithLobarWMMasked = PipeJobPartial(name="dwi_base_atlas_HammersmithLobarWMMasked", job=SchedulerPartial(
            taskList=[FSLMaths(output=session.subjectPaths.dwi.bids_processed.atlas_HammersmithLobar_WMMasked,
                               infiles=[
                                   session.subjectPaths.dwi.bids_processed.cat12_fromT1_whiteMatterProbability,
                                   session.subjectPaths.dwi.bids_processed.atlas_HammersmithLobar
                               ],
                               mathString="{} -thr 0.5 -bin -mul {}",
                               session=session) for session in self.sessions],
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=3, minimumMemPerNode=4), env=self.envs.envANTS)

        self.dwi_base_atlas_JHU_1mm_WMMasked = PipeJobPartial(name="dwi_base_atlas_JHU_1mm_WMMasked", job=SchedulerPartial(
            taskList=[FSLMaths(output=session.subjectPaths.dwi.bids_processed.atlas_JHU_1mm_WMMasked,
                               infiles=[
                                   session.subjectPaths.dwi.bids_processed.cat12_fromT1_whiteMatterProbability,
                                   session.subjectPaths.dwi.bids_processed.atlas_JHU_1mm
                               ],
                               mathString="{} -thr 0.5 -bin -mul {}",
                               session=session) for session in self.sessions],
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=3, minimumMemPerNode=4), env=self.envs.envANTS)

        self.dwi_base_synthsegWMCortical_mask = PipeJobPartial(name="dwi_base_synthsegWMCortical_mask", job=SchedulerPartial(
            taskList=[FSLMaths(output=session.subjectPaths.dwi.bids_processed.synthsegWMCortical_mask_fromT1w,
                               infiles=[
                                   session.subjectPaths.dwi.bids_processed.synthsegWMCorticalProbability_fromT1w
                               ],
                               mathString="{} -thr 0.5 -bin",
                               session=session) for session in self.sessions],
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=3, minimumMemPerNode=4), env=self.envs.envANTS)


        for atlas in ["atlas_HammersmithLobar_WMMasked0p5", "atlas_JHU_1mm_WMMasked0p5"]:
            for dti in ["dtifit_MD", "dtifit_RD", "dtifit_FA", "dtifit_AD"]:
                self.__setattr__("dwi_base_" + dti + "_mean_" + atlas,
                                 PipeJobPartial(name="dwi_base_" + dti + "_mean_" + atlas, job=SchedulerPartial(
                        taskList=[ExtractAtlasValues(infile=getattr(session.subjectPaths.dwi.bids_processed, dti),
                                                     atlas=getattr(session.subjectPaths.dwi.bids_processed, atlas),
                                                     outfile=getattr(session.subjectPaths.dwi.bids_statistics, dti + "_mean_" + atlas),
                                                     func="mean",
                                                     session=session) for session in self.sessions]),
                    env=self.envs.envR))

        for dti in ["dtifit_MD", "dtifit_RD", "dtifit_FA", "dtifit_AD"]:
            self.__setattr__("dwi_base_" + dti + "_stats_WMCortical",
                             PipeJobPartial(
                name="dwi_base_" + dti + "_stats_WMCortical", job=SchedulerPartial(
                    taskList=[FSLStats(infile=getattr(session.subjectPaths.dwi.bids_processed, dti),
                                       output=getattr(session.subjectPaths.dwi.bids_statistics, dti + "_mean_WMCortical0p5"),
                                       options=["-k", "-M"],
                                       mask=session.subjectPaths.dwi.bids_processed.synthsegWMCortical_mask_fromT1w,
                                       session=session) for session in self.sessions]),
                env=self.envs.envR))

    def setup(self) -> bool:
        self.addPipeJobs()
        return True

class DWI_dti_wmh(ProcessingModule):
    requiredModalities = ["dwi", "T1w", "flair"]
    moduleDependencies = ["T1w_base", "DWI_base", "FLAIR_base_withT1w"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #remove non-applicable sessions:
        self.sessions = [session for session in self.sessions if session.subjectPaths.dwi.bids.dwi.trackingSuitable()]


        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Scheduler.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=4, partition=self.inputArgs.partition)

        self.dti_wmh_fromFLair_WMH = PipeJobPartial(name="dti_wmh_fromFLair_WMH", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.WMHMask,
                                          output=session.subjectPaths.dwi.bids_processed.fromFlair_WMHMask,
                                          reference=session.subjectPaths.dwi.bids_processed.meanb0,
                                          transforms=[session.subjectPaths.dwi.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True,
                                                             False],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30,
                                          session=session) for session in self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.dti_wmh_synthsegNAWMCortical_mask = PipeJobPartial(name="dti_wmh_synthsegNAWMCortical_mask", job=SchedulerPartial(
            taskList=[FSLMaths(output=session.subjectPaths.dwi.bids_processed.synthsegNAWMCortical_mask,
                               infiles=[
                                   session.subjectPaths.dwi.bids_processed.synthsegWMCortical_mask_fromT1w,
                                   session.subjectPaths.dwi.bids_processed.fromFlair_WMHMask
                               ],
                               mathString="{} -sub {} -thr 0.5 -bin",
                               session=session) for session in self.sessions],
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=3, minimumMemPerNode=4), env=self.envs.envANTS)

        for dti in ["dtifit_MD", "dtifit_RD", "dtifit_FA", "dtifit_AD"]:
            self.__setattr__("dti_wmh_" + dti + "_stats_WMH",
                             PipeJobPartial(name="dti_wmh_" + dti + "_stats_WMH", job=SchedulerPartial(
                    taskList=[FSLStats(infile=getattr(session.subjectPaths.dwi.bids_processed, dti),
                                       output=getattr(session.subjectPaths.dwi.bids_statistics, dti + "_mean_WMH"),
                                       options=["-k", "-M"],
                                       mask=session.subjectPaths.dwi.bids_processed.fromFlair_WMHMask,
                                       session=session) for session in self.sessions]),
                env=self.envs.envR))

        for dti in ["dtifit_MD", "dtifit_RD", "dtifit_FA", "dtifit_AD"]:
            self.__setattr__("dti_wmh_" + dti + "_stats_NAWMCortical0p5",
                             PipeJobPartial(name="dti_wmh_" + dti + "_stats_NAWMCortical0p5", job=SchedulerPartial(
                    taskList=[FSLStats(infile=getattr(session.subjectPaths.dwi.bids_processed, dti),
                                       output=getattr(session.subjectPaths.dwi.bids_statistics, dti + "_mean_NAWMCortical0p5"),
                                       options=["-k", "-M"],
                                       mask=session.subjectPaths.dwi.bids_processed.synthsegNAWMCortical_mask,
                                       session=session) for session in self.sessions]),
                env=self.envs.envR))

    def setup(self) -> bool:
        self.addPipeJobs()
        return True

class DWI_msmt(ProcessingModule):
    requiredModalities = ["dwi", "T1w"]
    moduleDependencies = ["T1w_base", "DWI_base"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #remove non-applicable sessions:
        self.sessions = [session for session in self.sessions if session.subjectPaths.dwi.bids.dwi.trackingSuitable()]


        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Scheduler.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=4, partition=self.inputArgs.partition)

        self.dwi_msmt_DWI2Response = PipeJobPartial(name="dwi_msmt_DWI2Response", job=SchedulerPartial(
            taskList=[DWI2RESPONSE(inputImage=session.subjectPaths.dwi.bids_processed.fullyPreprocessedmif,
                                   responseSFWM=session.subjectPaths.dwi.bids_processed.responseSFWM,
                                   responseGM=session.subjectPaths.dwi.bids_processed.responseGM,
                                   responseCSF=session.subjectPaths.dwi.bids_processed.responseCSF,
                                   mask=session.subjectPaths.dwi.bids_processed.meanb0_mask,
                                   voxelOut=session.subjectPaths.dwi.bids_processed.responseVoxels,
                                   scratch=self.basepaths.scratch,
                                   session=session) for session in self.sessions],
            cpusPerTask=6, memPerCPU=2, minimumMemPerNode=12), env=self.envs.envMRtrixFSL)

        self.dwi_msmt_DWI2FOD = PipeJobPartial(name="dwi_msmt_DWI2FOD", job=SchedulerPartial(
            taskList=[DWI2FOD(inputImage=session.subjectPaths.dwi.bids_processed.fullyPreprocessedmif,
                              responseSFWM=session.subjectPaths.dwi.bids_processed.responseSFWM,
                              responseGM=session.subjectPaths.dwi.bids_processed.responseGM,
                              responseCSF=session.subjectPaths.dwi.bids_processed.responseCSF,
                              mask=session.subjectPaths.dwi.bids_processed.meanb0_mask,
                              responseSFWM_FOD=session.subjectPaths.dwi.bids_processed.responseSFWM_FOD,
                              responseGM_FOD=session.subjectPaths.dwi.bids_processed.responseGM_FOD,
                              responseCSF_FOD=session.subjectPaths.dwi.bids_processed.responseCSF_FOD,
                              session=session) for session in self.sessions],
            cpusPerTask=6, memPerCPU=2, minimumMemPerNode=12), env=self.envs.envMRtrixFSL)

        self.dwi_msmt_mtnormalise = PipeJobPartial(name="dwi_msmt_mtnormalise", job=SchedulerPartial(
            taskList=[MTNORMALISE(responseSFWM_FOD_norm=session.subjectPaths.dwi.bids_processed.responseSFWM_FOD_norm,
                                  responseGM_FOD_norm=session.subjectPaths.dwi.bids_processed.responseGM_FOD_norm,
                                  responseCSF_FOD_norm=session.subjectPaths.dwi.bids_processed.responseCSF_FOD_norm,
                                  mask=session.subjectPaths.dwi.bids_processed.meanb0_mask,
                                  responseSFWM_FOD=session.subjectPaths.dwi.bids_processed.responseSFWM_FOD,
                                  responseGM_FOD=session.subjectPaths.dwi.bids_processed.responseGM_FOD,
                                  responseCSF_FOD=session.subjectPaths.dwi.bids_processed.responseCSF_FOD,
                                  session=session) for session in self.sessions],
            cpusPerTask=6, memPerCPU=2, minimumMemPerNode=12), env=self.envs.envMRtrixFSL)

        self.dwi_msmt_5ttgen = PipeJobPartial(name="dwi_msmt_5ttgen", job=SchedulerPartial(
            taskList=[DWI5TTGEN(inputImage=session.subjectPaths.dwi.bids_processed.toT1w_InverseWarped,
                                outputImage=session.subjectPaths.dwi.bids_processed.msmt_5tt,
                                scratch=self.basepaths.scratch,
                                session=session) for session in self.sessions],
            cpusPerTask=6, memPerCPU=2, minimumMemPerNode=12), env=self.envs.envMRtrixFSL)

        self.dwi_fibertrack2connectome =PipeJobPartial(name="dwi_fibertrack2connectome", job=SchedulerPartial(
            taskList=[FIBERTRACKING2CONNECTOME(inputWMFOD=session.subjectPaths.dwi.bids_processed.responseSFWM_FOD_norm,
                                               T1_5TTReg=session.subjectPaths.dwi.bids_processed.msmt_5tt,
                                               nstreamlines=2000000,
                                               outputbase=session.subjectPaths.dwi.bids_statistics.connectome_basename,
                                               atlases={
                                                   "Schaefer2018_200Parcels_7Networks_order_FSLMNI152": session.subjectPaths.dwi.bids_processed.atlas_Schaefer2018_200Parcels_7Networks_order_FSLMNI152,
                                                   "Schaefer2018_100Parcels_7Networks_order_FSLMNI152": session.subjectPaths.dwi.bids_processed.atlas_Schaefer2018_100Parcels_7Networks_order_FSLMNI152,
                                                   "synthsegPosterior": session.subjectPaths.dwi.bids_processed.atlas_synthsegPosterior,
                                                   "Schaefer2018_200Parcels_17Networks_order_FSLMNI152": session.subjectPaths.dwi.bids_processed.atlas_Schaefer2018_200Parcels_17Networks_order_FSLMNI152
                                               },
                                               scratch=self.basepaths.scratch,
                                               session=session) for session in self.sessions],
            cpusPerTask=8, memPerCPU=2, minimumMemPerNode=16), env=self.envs.envMRtrixFSL)

        self.dwi_msmt_sh2peaks = PipeJobPartial(name="dwi_msmt_sh2peaks", job=SchedulerPartial(
            taskList=[SH2PEAKS(inputImage=session.subjectPaths.dwi.bids_processed.responseSFWM_FOD_norm,
                               outputImage=session.subjectPaths.dwi.bids_processed.msmt_wmfod_peaks,
                               session=session) for session in self.sessions],
            cpusPerTask=4, memPerCPU=2, minimumMemPerNode=8), env=self.envs.envMRtrixFSL)

        self.dwi_msmt_sh2peaks2std = PipeJobPartial(name="dwi_msmt_sh2peaks2std", job=SchedulerPartial(
            taskList=[FSLreorient2std(infile=session.subjectPaths.dwi.bids_processed.msmt_wmfod_peaks,
                                      output=session.subjectPaths.dwi.bids_processed.msmt_wmfod_peaks2std,
                                      session=session) for session in self.sessions],
            cpusPerTask=2, memPerCPU=2, minimumMemPerNode=8), env=self.envs.envMRtrixFSL)

        self.dwi_msmt_topup_b0_hifi_mean_mask2std = PipeJobPartial(name="dwi_msmt_topup_b0_hifi_mean_mask2std", job=SchedulerPartial(
            taskList=[FSLreorient2std(infile=session.subjectPaths.dwi.bids_processed.topup_b0_hifi_mean_mask,
                                      output=session.subjectPaths.dwi.bids_processed.topup_b0_hifi_mean_mask2std,
                                      session=session) for session in self.sessions],
            cpusPerTask=2, memPerCPU=2, minimumMemPerNode=8), env=self.envs.envMRtrixFSL)

        self.dwi_msmt_tractseg_segmentation = PipeJobPartial(name="dwi_msmt_tractseg_segmentation", job=SchedulerPartial(
            taskList=[Tractseg(inputPeaks=session.subjectPaths.dwi.bids_processed.msmt_wmfod_peaks2std,
                               outputDir=session.subjectPaths.dwi.bids_processed.tractseg_dir,
                               outputType="tract_segmentation",
                               mask=session.subjectPaths.dwi.bids_processed.topup_b0_hifi_mean_mask2std,
                                      session=session) for session in self.sessions],
            cpusPerTask=6, memPerCPU=2, minimumMemPerNode=12), env=self.envs.envTractseg)

        self.dwi_msmt_tractseg_endings_segmentation = PipeJobPartial(name="dwi_msmt_tractseg_endings_segmentation", job=SchedulerPartial(
            taskList=[Tractseg(inputPeaks=session.subjectPaths.dwi.bids_processed.msmt_wmfod_peaks2std,
                               outputDir=session.subjectPaths.dwi.bids_processed.tractseg_dir,
                               outputType="endings_segmentation",
                               mask=session.subjectPaths.dwi.bids_processed.topup_b0_hifi_mean_mask2std,
                               session=session) for session in self.sessions],
            cpusPerTask=6, memPerCPU=2, minimumMemPerNode=12), env=self.envs.envTractseg)

        self.dwi_msmt_tractseg_TOM = PipeJobPartial(name="dwi_msmt_tractseg_TOM", job=SchedulerPartial(
            taskList=[Tractseg(inputPeaks=session.subjectPaths.dwi.bids_processed.msmt_wmfod_peaks2std,
                               outputDir=session.subjectPaths.dwi.bids_processed.tractseg_dir,
                               outputType="TOM",
                               mask=session.subjectPaths.dwi.bids_processed.topup_b0_hifi_mean_mask2std,
                               session=session) for session in self.sessions],
            cpusPerTask=6, memPerCPU=2, minimumMemPerNode=12), env=self.envs.envTractseg)

        self.dwi_msmt_tractseg_Tracking = PipeJobPartial(name="dwi_msmt_tractseg_Tracking", job=SchedulerPartial(
            taskList=[Tracking(inputPeaks=session.subjectPaths.dwi.bids_processed.msmt_wmfod_peaks2std,
                               outputDir=session.subjectPaths.dwi.bids_processed.tractseg_dir,
                               session=session) for session in self.sessions],
            cpusPerTask=6, memPerCPU=2, minimumMemPerNode=12), env=self.envs.envTractseg)



    def setup(self) -> bool:
        self.addPipeJobs()
        return True
