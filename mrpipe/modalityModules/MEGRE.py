from mrpipe.modalityModules.ProcessingModule import ProcessingModule
from functools import partial
from mrpipe.schedueler.PipeJob import PipeJob
from mrpipe.schedueler import Slurm
from mrpipe.Toolboxes.FSL.Merge import Merge
from mrpipe.Toolboxes.FSL.FlirtResampleToTemplate import FlirtResampleToTemplate
from mrpipe.Toolboxes.standalone.QCVis import QCVis
from mrpipe.Toolboxes.standalone.QCVisWithoutMask import QCVisWithoutMask
from mrpipe.Toolboxes.standalone.MIP import MIP
from mrpipe.Toolboxes.standalone.VisMicroBleeds import VisMicroBleeds
from mrpipe.Toolboxes.standalone.CCByMaskCharacterization import CCByMaskCharacterization
from mrpipe.Toolboxes.standalone.CCOverlapRemoval import CCOverlapRemoval
from mrpipe.Toolboxes.ANTSTools.AntsRegistrationSyN import AntsRegistrationSyN
from mrpipe.Toolboxes.ANTSTools.AntsApplyTransform import AntsApplyTransforms
from mrpipe.Toolboxes.QSM.ChiSeperation import ChiSeperation
from mrpipe.Toolboxes.FSL.FSLStats import FSLStats
from mrpipe.Toolboxes.FSL.FSLMaths import FSLMaths
from mrpipe.Toolboxes.QSM.ClearSWI import ClearSWI
from mrpipe.Toolboxes.QSM.ShivaiCMB import ShivaiCMB
from mrpipe.Toolboxes.standalone.CountConnectedComponents import CCC
from mrpipe.Toolboxes.QSM.RescaleInKSpace4D import RescaleInKSpace4D
from mrpipe.Toolboxes.FSL.ROI import ROI
from mrpipe.Toolboxes.standalone.CAT12_WarpToTemplate import CAT12_WarpToTemplate
#from mrpipe.Toolboxes.standalone.
#TODO MIP
from mrpipe.Toolboxes.standalone.ExtractAtlasValues import ExtractAtlasValues
import os
from mrpipe.Helper import Helper


class MEGRE_base(ProcessingModule):
    requiredModalities = ["megre"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=16, partition=self.inputArgs.partition)


        # Step 1: Merge phase and magnitude to 4d Images
        self.megre_base_mergePhase4D = PipeJobPartial(name="MEGRE_base_mergePhase4D", job=SchedulerPartial(
            taskList=[Merge(infile=session.subjectPaths.megre.bids.megre.get_phase_paths(),
                            output=session.subjectPaths.megre.bids_processed.phase4D,
                            clobber=False) for session in
                      self.sessions],
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=3, minimumMemPerNode=12),
                                    env=self.envs.envFSL)

        self.megre_base_mergeMagnitude4D = PipeJobPartial(name="MEGRE_base_mergeMagnitude4D", job=SchedulerPartial(
            taskList=[Merge(infile=session.subjectPaths.megre.bids.megre.get_magnitude_paths(),
                            output=session.subjectPaths.megre.bids_processed.magnitude4d,
                            clobber=False) for session in
                      self.sessions],
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=3, minimumMemPerNode=12), env=self.envs.envFSL)

        self.megre_base_clearswi = PipeJobPartial(name="MEGRE_base_clearswi", job=SchedulerPartial(
            taskList=[ClearSWI(mag4d_path=session.subjectPaths.megre.bids_processed.magnitude4d,
                               pha4d_path=session.subjectPaths.megre.bids_processed.phase4D,
                               TEms=[x * 1000 for x in session.subjectPaths.megre.bids.megre.echoTimes],
                               outputDir=session.subjectPaths.megre.bids_processed.clearswiDir,
                               outputFiles=[session.subjectPaths.megre.bids_processed.clearswi,
                                            session.subjectPaths.megre.bids_processed.clearswiSettings],
                               clearswiSIF=self.libpaths.clearswi_singularityContainer,
                               unwrapping_algorithm="laplacian",
                               clobber=False) for session in
                      self.sessions],
            cpusPerTask=6, cpusTotal=self.inputArgs.ncores,
            memPerCPU=3, minimumMemPerNode=16), env=self.envs.envSingularity)

        # self.megre_base_clearswi_mip = PipeJobPartial(name="MEGRE_base_clearswi_mip", job=SchedulerPartial(
        #     taskList=[Merge(infile=session.subjectPaths.megre.bids.megre.get_magnitude_paths(),
        #                     output=session.subjectPaths.megre.bids_processed.magnitude4d,
        #                     clobber=False) for session in
        #               self.sessions],
        #     cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
        #     memPerCPU=4, minimumMemPerNode=8), env=self.envs.envFSL)

    def setup(self) -> bool:
        self.addPipeJobs()
        return True

class MEGRE_ToT1(ProcessingModule):
    requiredModalities = ["megre", "T1w"]
    moduleDependencies = ["T1w_base", "MEGRE_base"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=16, partition=self.inputArgs.partition)

        # Step 0: transform first Mag to T1 native for brain mask:
        self.megre_base_NativeToT1w = PipeJobPartial(name="MEGRE_base_NativeToT1", job=SchedulerPartial(
            taskList=[AntsRegistrationSyN(fixed=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                          moving=session.subjectPaths.megre.bids.megre.magnitude[0].imagePath,
                                          outprefix=session.subjectPaths.megre.bids_processed.toT1w_prefix,
                                          expectedOutFiles=[session.subjectPaths.megre.bids_processed.toT1w_toT1w,
                                                            session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          ncores=2, dim=3, type="a") for session in self.sessions],
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=3, minimumMemPerNode=4),
                                                     env=self.envs.envANTS)

        self.megre_base_qc_vis_toT1w = PipeJobPartial(name="MEGRE_base_slices_toT1w", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.megre.bids_processed.toT1w_toT1w,
                            mask=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                            image=session.subjectPaths.megre.meta_QC.ToT1w_native_slices, contrastAdjustment=False,
                            outline=True, transparency=True, zoom=1) for session in
                      self.sessions]), env=self.envs.envQCVis)

    def setup(self) -> bool:
        self.addPipeJobs()
        return True


class MEGRE_CMB(ProcessingModule):
    requiredModalities = ["megre", "T1w"]
    moduleDependencies = ["MEGRE_ToT1", "T1w_SynthSeg"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=16, partition=self.inputArgs.partition)


        self.megre_cmb_fromT1w_T1 = PipeJobPartial(name="MEGRE_cmb_fromT1w_T1", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                          output=session.subjectPaths.megre.bids_processed.fromT1w_T1w,
                                          reference=session.subjectPaths.megre.bids.megre.magnitude[0].imagePath,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_cmb_fromT1w_SynthSeg = PipeJobPartial(name="MEGRE_cmb_fromT1w_SynthSeg", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosterior,
                                          output=session.subjectPaths.megre.bids_processed.fromT1w_synthSeg,
                                          reference=session.subjectPaths.megre.bids.megre.magnitude[0].imagePath,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)


        self.megre_cmb_shivaiCMB = PipeJobPartial(name="MEGRE_cmb_shivaiCMB", job=SchedulerPartial(
            taskList=[ShivaiCMB(subSesString=session.subjectPaths.megre.bids_processed.baseString,
                                swi=session.subjectPaths.megre.bids_processed.clearswi,
                                t1=session.subjectPaths.megre.bids_processed.fromT1w_T1w,
                                segmentation=session.subjectPaths.megre.bids_processed.fromT1w_synthSeg,
                                tempInDir=self.basepaths.scratch.join(session.subjectPaths.megre.bids_processed.baseString + "_shivaiCMB", isDirectory=True, create=True),
                                outputDir=session.subjectPaths.megre.bids_processed.shivai_outputDir,
                                outputFiles=[session.subjectPaths.megre.bids_processed.shivai_CMB_Probability_SegSpace,
                                             session.subjectPaths.megre.bids_processed.shivai_CMB_QC,
                                             session.subjectPaths.megre.bids_processed.shivai_CMB_Mask_segSapce],
                                shivaiSIF=self.libpaths.shivaiSIF,
                                shivaiModelDir=self.libpaths.shivaiModelDir,
                                shivaiConfig=self.libpaths.shivaiConfig,
                                predictionType="CMB",
                                ncores=4,
                            clobber=False) for session in
                      self.sessions],
            cpusPerTask=4, cpusTotal=self.inputArgs.ncores,
            memPerCPU=3, minimumMemPerNode=12, ngpus=self.inputArgs.ngpus),
                                    env=self.envs.envSingularity)

        self.megre_cmb_shivaiCMB_rerunToFix = PipeJobPartial(name="MEGRE_cmb_shivaiCMB_rerunToFix", job=SchedulerPartial(
            taskList=[ShivaiCMB(subSesString=session.subjectPaths.megre.bids_processed.baseString,
                                swi=session.subjectPaths.megre.bids_processed.clearswi,
                                t1=session.subjectPaths.megre.bids_processed.fromT1w_T1w,
                                segmentation=session.subjectPaths.megre.bids_processed.fromT1w_synthSeg,
                                tempInDir=self.basepaths.scratch.join(session.subjectPaths.megre.bids_processed.baseString + "_shivaiCMB", isDirectory=True, create=True),
                                outputDir=session.subjectPaths.megre.bids_processed.shivai_outputDir,
                                outputFiles=[session.subjectPaths.megre.bids_processed.shivai_CMB_Probability_SegSpace,
                                             session.subjectPaths.megre.bids_processed.shivai_CMB_QC,
                                             session.subjectPaths.megre.bids_processed.shivai_CMB_Mask_segSapce],
                                shivaiSIF=self.libpaths.shivaiSIFLatest,
                                shivaiModelDir=self.libpaths.shivaiModelDir,
                                shivaiConfig=self.libpaths.shivaiConfig,
                                predictionType="CMB",
                                ncores=4,
                                clobber=False) for session in
                      self.sessions],
            cpusPerTask=4, cpusTotal=self.inputArgs.ncores,
            memPerCPU=3, minimumMemPerNode=12, ngpus=self.inputArgs.ngpus),
                                                  env=self.envs.envSingularity)

        self.megre_cmb_mip = PipeJobPartial(name="MEGRE_cmb_MIP", job=SchedulerPartial(
            taskList=[MIP(infile=session.subjectPaths.megre.bids_processed.clearswi,
                          outfile=session.subjectPaths.megre.bids_processed.clearswi_mip_calculated
                          ) for session in self.sessions],
            cpusPerTask=2), env=self.envs.envMRPipe)

        self.megre_cmb_shivaiCMB_mask_resampleToSWI = PipeJobPartial(name="MEGRE_cmb_shivaiCMB_mask_resampleToSWI", job=SchedulerPartial(
            taskList=[FlirtResampleToTemplate(infile=session.subjectPaths.megre.bids_processed.shivai_CMB_Mask_segSapce,
                                              reference=session.subjectPaths.megre.bids_processed.clearswi,
                                              output=session.subjectPaths.megre.bids_processed.shivai_CMB_Mask_labels,
                                              interpolation="nearestneighbour" ) for session in self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.megre_cmb_shivaiCMB_prob_resampleToSWI = PipeJobPartial(name="MEGRE_cmb_shivaiCMB_prob_resampleToSWI", job=SchedulerPartial(
            taskList=[FlirtResampleToTemplate(infile=session.subjectPaths.megre.bids_processed.shivai_CMB_Probability_SegSpace,
                                              reference=session.subjectPaths.megre.bids_processed.clearswi,
                                              output=session.subjectPaths.megre.bids_processed.shivai_CMB_Probability,
                                              interpolation="spline") for session in self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        #warp TPMs from T1w to create masks
        self.megre_cmb_fromT1w_GMWM = PipeJobPartial(name="MEGRE_cmb_fromT1w_GMWM", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.synthseg.synthsegGMWM,
                                          output=session.subjectPaths.megre.bids_processed.fromT1w_GMWM,
                                          reference=session.subjectPaths.megre.bids_processed.clearswi,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions], cpusPerTask=2), env=self.envs.envANTS)

        self.megre_cmb_fromT1w_LatVent = PipeJobPartial(name="MEGRE_cmb_fromT1w_LatVent", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.synthseg.synthsegLV,
                                          output=session.subjectPaths.megre.bids_processed.fromT1w_LatVent,
                                          reference=session.subjectPaths.megre.bids_processed.clearswi,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions], cpusPerTask=2), env=self.envs.envANTS)

        self.megre_cmb_fromT1w_Cerebellum = PipeJobPartial(name="MEGRE_cmb_fromT1w_Cerebellum", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.synthseg.synthsegCerebellum,
                                          output=session.subjectPaths.megre.bids_processed.fromT1w_Cerebellum,
                                          reference=session.subjectPaths.megre.bids_processed.clearswi,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions], cpusPerTask=2), env=self.envs.envANTS)

        self.megre_cmb_fromT1w_GMCortical = PipeJobPartial(name="MEGRE_cmb_fromT1w_GMCortical", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.synthseg.synthsegGMCortical,
                                          output=session.subjectPaths.megre.bids_processed.fromT1w_GMCortical,
                                          reference=session.subjectPaths.megre.bids_processed.clearswi,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions], cpusPerTask=2), env=self.envs.envANTS)

        #create masks from TPMs:
        self.megre_cmb_fromT1w_GMWMMask = PipeJobPartial(name="megre_cmb_fromT1w_GMWMMask", job=SchedulerPartial(
            taskList=[FSLMaths(infiles=[session.subjectPaths.megre.bids_processed.fromT1w_GMWM],
                               output=session.subjectPaths.megre.bids_processed.fromT1w_GMWMMask,
                               mathString="{} -thr 0.5 -bin") for session in
                      self.sessions]), env=self.envs.envFSL)

        self.megre_cmb_fromT1w_LatVentMask = PipeJobPartial(name="megre_cmb_fromT1w_LatVentMask", job=SchedulerPartial(
            taskList=[FSLMaths(infiles=[session.subjectPaths.megre.bids_processed.fromT1w_LatVent],
                               output=session.subjectPaths.megre.bids_processed.fromT1w_LatVentMask,
                               mathString="{} -thr 0.5 -bin") for session in
                      self.sessions]), env=self.envs.envFSL)

        self.megre_cmb_fromT1w_CerebellumMask = PipeJobPartial(name="megre_cmb_fromT1w_CerebellumMask", job=SchedulerPartial(
            taskList=[FSLMaths(infiles=[session.subjectPaths.megre.bids_processed.fromT1w_Cerebellum],
                               output=session.subjectPaths.megre.bids_processed.fromT1w_CerebellumMask,
                               mathString="{} -thr 0.5 -bin") for session in
                      self.sessions]), env=self.envs.envFSL)

        self.megre_cmb_fromT1w_GMCorticalMaskDil1mm = PipeJobPartial(name="megre_cmb_fromT1w_GMCorticalMaskDil1mm", job=SchedulerPartial(
            taskList=[FSLMaths(infiles=[session.subjectPaths.megre.bids_processed.fromT1w_GMCortical],
                               output=session.subjectPaths.megre.bids_processed.fromT1w_GMCorticalMaskDil1mm,
                               mathString="{} -thr 0.5 -bin -kernel sphere 1 -dilM") for session in
                      self.sessions]), env=self.envs.envFSL)

        #limit CMB segmentation with masks:
        self.megre_cmb_shivaiCMB_MaskLimitGMWM = PipeJobPartial(name="megre_cmb_shivaiCMB_MaskLimitGMWM", job=SchedulerPartial(
            taskList=[CCOverlapRemoval(infile=session.subjectPaths.megre.bids_processed.shivai_CMB_Mask_labels,
                                       mask=session.subjectPaths.megre.bids_processed.fromT1w_GMWMMask,
                                       outfile=session.subjectPaths.megre.bids_processed.shivai_CMB_Mask_labelsLimited,
                                       inclusive=True) for session in
                      self.sessions]), env=self.envs.envMRPipe)

        self.megre_cmb_shivaiCMB_MaskLimitLV = PipeJobPartial(name="megre_cmb_shivaiCMB_MaskLimitLV", job=SchedulerPartial(
            taskList=[CCOverlapRemoval(infile=session.subjectPaths.megre.bids_processed.shivai_CMB_Mask_labelsLimited,
                                        mask=session.subjectPaths.megre.bids_processed.fromT1w_LatVentMask,
                               outfile=session.subjectPaths.megre.bids_processed.shivai_CMB_Mask_labelsLimitedMasked) for session in
                      self.sessions]), env=self.envs.envMRPipe)

        self.megre_cmb_shivaiCMB_MaskLimitCMB = PipeJobPartial(name="megre_cmb_shivaiCMB_MaskLimitCB", job=SchedulerPartial(
            taskList=[CCOverlapRemoval(infile=session.subjectPaths.megre.bids_processed.shivai_CMB_Mask_labelsLimitedMasked,
                                       mask=session.subjectPaths.megre.bids_processed.fromT1w_CerebellumMask,
                                       outfile=session.subjectPaths.megre.bids_processed.shivai_CMB_Mask_labelsLimitedMaskedMasked) for session in
                      self.sessions]), env=self.envs.envMRPipe)

        self.megre_cmb_shivaiCMB_Mask = PipeJobPartial(name="MEGRE_cmb_shivaiCMB_Mask", job=SchedulerPartial(
            taskList=[FSLMaths(infiles=[session.subjectPaths.megre.bids_processed.shivai_CMB_Mask_labelsLimitedMaskedMasked],
                               output=session.subjectPaths.megre.bids_processed.shivai_CMB_Mask,
                               mathString="{} -bin") for session in
                      self.sessions]), env=self.envs.envFSL)

        self.megre_cmb_shivaiCMB_VisCMB = PipeJobPartial(name="MEGRE_cmb_shivaiCMB_VisCMB", job=SchedulerPartial(
            taskList=[VisMicroBleeds(infile=session.subjectPaths.megre.bids_processed.clearswi_mip_calculated,
                                     mask=session.subjectPaths.megre.bids_processed.shivai_CMB_Mask,
                                     outimage=session.subjectPaths.megre.meta_QC.shivai_CMB_VisMCB
                                     ) for session in self.sessions]), env=self.envs.envMRPipe)

        self.megre_cmb_shivaiCMB_CountCMB = PipeJobPartial(name="MEGRE_cmb_shivaiCMB_CountCMB", job=SchedulerPartial(
            taskList=[CCC(infile=session.subjectPaths.megre.bids_processed.shivai_CMB_Mask,
                          output=session.subjectPaths.megre.bids_statistics.lesionResults_CMB_Count
                          ) for session in self.sessions]), env=self.envs.envMRPipe)

        self.megre_cmb_shivaiCMB_CountCMBLobar = PipeJobPartial(name="MEGRE_cmb_shivaiCMB_CountCMBLobar", job=SchedulerPartial(
            taskList=[CCByMaskCharacterization(inCCFile=session.subjectPaths.megre.bids_processed.shivai_CMB_Mask,
                                                masks=[session.subjectPaths.megre.bids_processed.fromT1w_GMCorticalMaskDil1mm],
                                                outCSV=session.subjectPaths.megre.bids_statistics.lesionResults_CMB_Lobar_Count
                                                ) for session in self.sessions]), env=self.envs.envMRPipe)



    def setup(self) -> bool:
        self.addPipeJobs()
        return True

class MEGRE_ChiSep(ProcessingModule):
    requiredModalities = ["megre", "T1w"]
    moduleDependencies = ["MEGRE_ToT1"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=16, partition=self.inputArgs.partition)


        self.megre_chiSep_RescaleInKSpace4D = PipeJobPartial(name="MEGRE_chiSep_RescaleInKSpace4D", job=SchedulerPartial(
            taskList=[RescaleInKSpace4D(mag4d_path=session.subjectPaths.megre.bids_processed.magnitude4d,
                                        pha4d_path=session.subjectPaths.megre.bids_processed.phase4D,
                                        mag4d_pathOut=session.subjectPaths.megre.bids_processed.magnitude4dScaled0p65,
                                        pha4d_pathOut=session.subjectPaths.megre.bids_processed.phase4DScaled0p65,
                                        tukeyStrength=0.2
                          ) for session in self.sessions]), env=self.envs.envMatlab)

        self.megre_chiSep_ScaledMag1 = PipeJobPartial(name="MEGRE_chiSep_ScaledMag1", job=SchedulerPartial(
            taskList=[ROI(infile=session.subjectPaths.megre.bids_processed.magnitude4dScaled0p65,
                          output=session.subjectPaths.megre.bids_processed.magnitudeE1Scaled0p65,
                          roiDef="0 1"
                          ) for session in self.sessions]), env=self.envs.envFSL)

        self.megre_base_bmToMEGRE = PipeJobPartial(name="MEGRE_base_BMtoMEGRE", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                                          output=session.subjectPaths.megre.bids_processed.brainMask_toMEGRE,
                                          reference=session.subjectPaths.megre.bids_processed.magnitudeE1Scaled0p65,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="NearestNeighbor",
                                          inverse_transform=[True],
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        # Step 2: perform Chi-seperation
        self.megre_base_chiSep = PipeJobPartial(name="MEGRE_base_chiSep", job=SchedulerPartial(
            taskList=[ChiSeperation(mag4d_path=session.subjectPaths.megre.bids_processed.magnitude4dScaled0p65,
                                    pha4d_path=session.subjectPaths.megre.bids_processed.phase4DScaled0p65,
                                    brainmask_path=session.subjectPaths.megre.bids_processed.brainMask_toMEGRE,
                                    outdir=session.subjectPaths.megre.bids_processed.chiSepDir,
                                    TEms=[x * 1000 for x in session.subjectPaths.megre.bids.megre.echoTimes], #script requires miliseconds, json property is seconds
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
            cpusPerTask=16, cpusTotal=self.inputArgs.ncores,
            memPerCPU=3, minimumMemPerNode=24),
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
    moduleDependencies = ["MEGRE_ChiSep", "T1w_base"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=12, partition=self.inputArgs.partition)

        self.megre_toT1wNative_ChiDia = PipeJobPartial(name="MEGRE_native_DiaToT1w", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.chiDiamagnetic_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_toT1wNative_ChiPara = PipeJobPartial(name="MEGRE_native_ParaToT1w", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.chiParamagnetic_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_toT1wNative_QSM = PipeJobPartial(name="MEGRE_native_QSMToT1w", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.QSM,
                                          output=session.subjectPaths.megre.bids_processed.QSM_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

    def setup(self) -> bool:
        self.addPipeJobs()
        return True

class MEGRE_statsNative(ProcessingModule):
    requiredModalities = ["T1w", "megre"]
    moduleDependencies = ["MEGRE_ToT1wNative", "T1w_base", "MEGRE_ChiSep"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=16, partition=self.inputArgs.partition)

        self.megre_native_fromT1w_WM = PipeJobPartial(name="MEGRE_native_fromT1w_WM", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.maskWMCortical_thr0p5_ero1mm,
                                          output=session.subjectPaths.megre.bids_processed.fromT1w_WMCortical_thr0p5_ero1mm,
                                          reference=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_native_fromT1w_GMCortical = PipeJobPartial(name="MEGRE_native_fromT1w_GMCortical", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.maskGMCortical_thr0p5_ero1mm,
                                          output=session.subjectPaths.megre.bids_processed.fromT1w_GMCortical_thr0p5_ero1mm,
                                          reference=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_statsNative_ChiDia_WM = PipeJobPartial(name="MEGRE_StatsNative_ChiDia_WM", job=SchedulerPartial(
            taskList=[FSLStats(infile=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                               output=session.subjectPaths.megre.bids_statistics.chiSepResults_chiNeg_mean_WMCortical_0p5_ero1mm,
                               options=["-k", "-M"],
                               mask=session.subjectPaths.megre.bids_processed.fromT1w_WMCortical_thr0p5_ero1mm) for session in
                      self.sessions],
            cpusPerTask=4), env=self.envs.envFSL)

        self.megre_statsNative_ChiPara_WM = PipeJobPartial(name="MEGRE_StatsNative_ChiPara_WM", job=SchedulerPartial(
            taskList=[FSLStats(infile=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                               output=session.subjectPaths.megre.bids_statistics.chiSepResults_chiPos_mean_WMCortical_0p5_ero1mm,
                               options=["-k", "-M"],
                               mask=session.subjectPaths.megre.bids_processed.fromT1w_WMCortical_thr0p5_ero1mm) for session in
                      self.sessions],
            cpusPerTask=4), env=self.envs.envFSL)

        self.megre_statsNative_QSM_WM = PipeJobPartial(name="MEGRE_StatsNative_QSM_WM", job=SchedulerPartial(
            taskList=[FSLStats(infile=session.subjectPaths.megre.bids_processed.QSM,
                               output=session.subjectPaths.megre.bids_statistics.chiSepResults_QSM_mean_WMCortical_0p5_ero1mm,
                               options=["-k", "-M"],
                               mask=session.subjectPaths.megre.bids_processed.fromT1w_WMCortical_thr0p5_ero1mm) for session in
                      self.sessions],
            cpusPerTask=4), env=self.envs.envFSL)

        self.megre_statsNative_ChiDia_GMCortical = PipeJobPartial(name="MEGRE_StatsNative_ChiDia_GMCortical", job=SchedulerPartial(
            taskList=[FSLStats(infile=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                               output=session.subjectPaths.megre.bids_statistics.chiSepResults_chiNeg_mean_GMCortical_0p5_ero1mm,
                               options=["-k", "-M"],
                               mask=session.subjectPaths.megre.bids_processed.fromT1w_GMCortical_thr0p5_ero1mm) for session in
                      self.sessions],
            cpusPerTask=4), env=self.envs.envFSL)

        self.megre_statsNative_ChiPara_GMCortical = PipeJobPartial(name="MEGRE_StatsNative_ChiPara_GMCortical", job=SchedulerPartial(
            taskList=[FSLStats(infile=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                               output=session.subjectPaths.megre.bids_statistics.chiSepResults_chiPos_mean_GMCortical_0p5_ero1mm,
                               options=["-k", "-M"],
                               mask=session.subjectPaths.megre.bids_processed.fromT1w_GMCortical_thr0p5_ero1mm) for session in
                      self.sessions],
            cpusPerTask=4), env=self.envs.envFSL)

        self.megre_statsNative_QSM_GMCortical = PipeJobPartial(name="MEGRE_StatsNative_QSM_GMCortical", job=SchedulerPartial(
            taskList=[FSLStats(infile=session.subjectPaths.megre.bids_processed.QSM,
                               output=session.subjectPaths.megre.bids_statistics.chiSepResults_QSM_mean_GMCortical_0p5_ero1mm,
                               options=["-k", "-M"],
                               mask=session.subjectPaths.megre.bids_processed.fromT1w_GMCortical_thr0p5_ero1mm) for session in
                      self.sessions],
            cpusPerTask=4), env=self.envs.envFSL)

    def setup(self) -> bool:
        self.addPipeJobs()
        return True



class MEGRE_statsNative_WMH(ProcessingModule):
    requiredModalities = ["T1w", "megre", "flair"]
    moduleDependencies = ["MEGRE_ToT1wNative", "T1w_base", "MEGRE_ChiSep", "FLAIR_base_withT1w"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=4, partition=self.inputArgs.partition)

        #transform WMH and NAWM
        self.megre_native_fromFlair_WMH = PipeJobPartial(name="MEGRE_native_fromFlair_WMH", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.WMHMask,
                                          output=session.subjectPaths.megre.bids_processed.fromFlair_WMH,
                                          reference=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          transforms=[
                                              session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine,
                                              session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine
                                              ],
                                          inverse_transform=[True, False],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_native_fromFlair_NAWMCortical_thr0p5_ero1mm = PipeJobPartial(name="MEGRE_native_fromFlair_NAWMCortical_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.fromT1w_NAWMCortical_thr0p5_ero1mm,
                                          output=session.subjectPaths.megre.bids_processed.fromFlair_NAWMCortical_thr0p5_ero1mm,
                                          reference=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          transforms=[
                                              session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine,
                                              session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine
                                              ],
                                          inverse_transform=[True, False],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        #extract Stats from NAWM mask with Dia / Para / QSM
        self.megre_StatsNative_ChiDia_NAWMCortical_0p5_ero1mm = PipeJobPartial(name="MEGRE_StatsNative_ChiDia_NAWMCortical_0p5_ero1mm", job=SchedulerPartial(
            taskList=[FSLStats(infile=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                               output=session.subjectPaths.megre.bids_statistics.chiSepResults_chiNeg_mean_NAWMCortical_0p5_ero1mm,
                               options=["-k", "-M"],
                               mask=session.subjectPaths.megre.bids_processed.fromFlair_NAWMCortical_thr0p5_ero1mm) for
                      session in
                      self.sessions],
            cpusPerTask=4), env=self.envs.envFSL)

        self.megre_StatsNative_ChiPara_NAWMCortical_0p5_ero1mm = PipeJobPartial(name="MEGRE_StatsNative_ChiPara_NAWMCortical_0p5_ero1mm", job=SchedulerPartial(
            taskList=[FSLStats(infile=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                               output=session.subjectPaths.megre.bids_statistics.chiSepResults_chiPos_mean_NAWMCortical_0p5_ero1mm,
                               options=["-k", "-M"],
                               mask=session.subjectPaths.megre.bids_processed.fromFlair_NAWMCortical_thr0p5_ero1mm) for
                      session in
                      self.sessions],
            cpusPerTask=4), env=self.envs.envFSL)

        self.megre_StatsNative_QSM_NAWMCortical_0p5_ero1mm = PipeJobPartial(name="MEGRE_StatsNative_QSM_NAWMCortical_0p5_ero1mm", job=SchedulerPartial(
            taskList=[FSLStats(infile=session.subjectPaths.megre.bids_processed.QSM,
                               output=session.subjectPaths.megre.bids_statistics.chiSepResults_QSM_mean_NAWMCortical_0p5_ero1mm,
                               options=["-k", "-M"],
                               mask=session.subjectPaths.megre.bids_processed.fromFlair_NAWMCortical_thr0p5_ero1mm) for
                      session in
                      self.sessions],
            cpusPerTask=4), env=self.envs.envFSL)

        # extract Stats from WMH mask with Dia / Para / QSM
        self.megre_StatsNative_ChiDia_WMH = PipeJobPartial(
            name="MEGRE_StatsNative_ChiDia_WMH", job=SchedulerPartial(
                taskList=[FSLStats(infile=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                   output=session.subjectPaths.megre.bids_statistics.chiSepResults_chiNeg_mean_WMH,
                                   options=["-k", "-M"],
                                   mask=session.subjectPaths.megre.bids_processed.fromFlair_WMH)
                          for
                          session in
                          self.sessions],
                cpusPerTask=4), env=self.envs.envFSL)

        self.megre_StatsNative_ChiPara_WMH = PipeJobPartial(
            name="MEGRE_StatsNative_ChiPara_WMH", job=SchedulerPartial(
                taskList=[FSLStats(infile=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                   output=session.subjectPaths.megre.bids_statistics.chiSepResults_chiPos_mean_WMH,
                                   options=["-k", "-M"],
                                   mask=session.subjectPaths.megre.bids_processed.fromFlair_WMH)
                          for
                          session in
                          self.sessions],
                cpusPerTask=4), env=self.envs.envFSL)

        self.megre_StatsNative_QSM_WMH = PipeJobPartial(
            name="MEGRE_StatsNative_QSM_WMH", job=SchedulerPartial(
                taskList=[FSLStats(infile=session.subjectPaths.megre.bids_processed.QSM,
                                   output=session.subjectPaths.megre.bids_statistics.chiSepResults_QSM_mean_WMH,
                                   options=["-k", "-M"],
                                   mask=session.subjectPaths.megre.bids_processed.fromFlair_WMH)
                          for
                          session in
                          self.sessions],
                cpusPerTask=4), env=self.envs.envFSL)
    def setup(self) -> bool:
        self.addPipeJobs()
        return True



class MEGRE_ToCAT12MNI(ProcessingModule):
    requiredModalities = ["megre", "T1w"]
    moduleDependencies = ["MEGRE_ToT1wNative", "T1w_base", "MEGRE_ChiSep"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=16, partition=self.inputArgs.partition)

        self.megre_toCat12MNI_chiDia = PipeJobPartial(name="MEGRE_toCat12MNI_chiDia", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.megre.bids_processed.chiDiamagnetic_toT1w,
                                            warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                          tempdir=self.basepaths.scratch,
                                           outfile=session.subjectPaths.megre.bids_processed.iso1mm.chiDiamagnetic_cat12MNI,
                                           ) for session in
                      self.sessions]), env=self.envs.envSPM12)

        self.megre_toCat12MNI_chiPara = PipeJobPartial(name="MEGRE_toCat12MNI_chiPara", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.megre.bids_processed.chiParamagnetic_toT1w,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                          tempdir=self.basepaths.scratch,
                                           outfile=session.subjectPaths.megre.bids_processed.iso1mm.chiParamagnetic_cat12MNI) for session in
                      self.sessions]), env=self.envs.envSPM12)

        self.megre_toCat12MNI_QSM = PipeJobPartial(name="MEGRE_toCat12MNI_QSM", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.megre.bids_processed.QSM_toT1w,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                          tempdir=self.basepaths.scratch,
                                           outfile=session.subjectPaths.megre.bids_processed.iso1mm.QSM_cat12MNI) for session in
                      self.sessions]), env=self.envs.envSPM12)

    def setup(self) -> bool:
        self.addPipeJobs()
        return True

class MEGRE_ToT1wMNI_1mm(ProcessingModule):
    requiredModalities = ["T1w", "megre"]
    moduleDependencies = ["MEGRE_ToT1wNative", "T1w_1mm", "MEGRE_statsNative"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=4, partition=self.inputArgs.partition)

        self.megre_NativeToT1w_1mm_ChiDia = PipeJobPartial(name="MEGRE_NativeToT1w_1mm_ChiDia", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso1mm.chiDiamagnetic_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso1mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_NativeToT1w_1mm_ChiPara = PipeJobPartial(name="MEGRE_NativeToT1w_1mm_ChiPara", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso1mm.chiParamagnetic_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso1mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_NativeToT1w_1mm_QSM = PipeJobPartial(name="MEGRE_NativeToT1w_1mm_QSM", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.QSM,
                                          output=session.subjectPaths.megre.bids_processed.iso1mm.QSM_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso1mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)


        # To MNI
        self.megre_NativeToMNI_1mm_ChiDia = PipeJobPartial(name="MEGRE_NativeToMNI_1mm_ChiDia", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso1mm.chiDiamagnetic_toMNI,
                                          reference=self.templates.mni152_1mm,
                                          transforms=[session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1Warp,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_NativeToMNI_1mm_ChiPara = PipeJobPartial(name="MEGRE_NativeToMNI_1mm_ChiPara", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso1mm.chiParamagnetic_toMNI,
                                          reference=self.templates.mni152_1mm,
                                          transforms=[session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1Warp,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine
                                                      ],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_NativeToMNI_1mm_QSM = PipeJobPartial(name="MEGRE_NativeToMNI_1mm_QSM", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.QSM,
                                          output=session.subjectPaths.megre.bids_processed.iso1mm.QSM_toMNI,
                                          reference=self.templates.mni152_1mm,
                                          transforms=[session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1Warp,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)


        # atlas to native space:
        self.megre_nativeToMNI_1mm_fromMNI_HammersmithLobar = PipeJobPartial(name="MEGRE_nativeToMNI_1mm_fromMNI_HammersmithLobar", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=self.templates.HammersmithLobar,
                                          output=session.subjectPaths.megre.bids_processed.iso1mm.atlas_HammersmithLobar_megreNative,
                                          reference=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1InverseWarp],
                                          inverse_transform=[True, True, False],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_nativeToMNI_1mm_HammersmithLobar_maskedWM0p5_ero1mm = PipeJobPartial(name="MEGRE_nativeToMNI_1mm_HammersmithLobar_maskedWM0p5_ero1mm", job=SchedulerPartial(
            taskList=[FSLMaths(infiles=[session.subjectPaths.megre.bids_processed.iso1mm.atlas_HammersmithLobar_megreNative,
                                        session.subjectPaths.megre.bids_processed.fromT1w_WMCortical_thr0p5_ero1mm],
                               output=session.subjectPaths.megre.bids_processed.iso1mm.atlas_HammersmithLobar_megreNative_maskedWM0p5_ero1mm,
                               mathString="{} -mul {}") for session in
                      self.sessions]), env=self.envs.envFSL)

        self.megre_nativeToMNI_1mm_fromMNI_JHUDTI_1mm = PipeJobPartial(name="MEGRE_nativeToMNI_1mm_fromMNI_JHUDTI_1mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=self.templates.JHU_1mm,
                                          output=session.subjectPaths.megre.bids_processed.iso1mm.atlas_JHUDTI_1mm_megreNative,
                                          reference=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1InverseWarp],
                                          inverse_transform=[True, True, False],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_nativeToMNI_1mm_JHUDTI_1mm_maskedWM0p5_ero1mm = PipeJobPartial(name="MEGRE_nativeToMNI_1mm_JHUDTI_1mm_maskedWM0p5_ero1mm", job=SchedulerPartial(
            taskList=[FSLMaths(infiles=[session.subjectPaths.megre.bids_processed.iso1mm.atlas_JHUDTI_1mm_megreNative,
                                        session.subjectPaths.megre.bids_processed.fromT1w_WMCortical_thr0p5_ero1mm],
                               output=session.subjectPaths.megre.bids_processed.iso1mm.atlas_JHUDTI_1mm_megreNative_maskedWM0p5_ero1mm,
                               mathString="{} -mul {}") for session in
                      self.sessions]), env=self.envs.envFSL)

        self.megre_nativeToMNI_1mm_fromMNI_Schaefer200_17Net = PipeJobPartial(name="MEGRE_nativeToMNI_1mm_fromMNI_Schaefer200_17Net", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=self.templates.Schaefer2018_200Parcels_17Networks_order_FSLMNI152_1mm,
                                          output=session.subjectPaths.megre.bids_processed.iso1mm.atlas_Schaefer200_17Net_megreNative,
                                          reference=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1InverseWarp],
                                          inverse_transform=[True, True, False],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_nativeToMNI_1mm_Schaefer200_17Net_megreNative_maskedGMCortical0p5_ero1mm = PipeJobPartial(name="MEGRE_nativeToMNI_1mm_Schaefer200_17Net_megreNative_maskedGMCortical0p5_ero1mm", job=SchedulerPartial(
            taskList=[FSLMaths(infiles=[session.subjectPaths.megre.bids_processed.iso1mm.atlas_Schaefer200_17Net_megreNative,
                                        session.subjectPaths.megre.bids_processed.fromT1w_GMCortical_thr0p5_ero1mm],
                               output=session.subjectPaths.megre.bids_processed.iso1mm.atlas_Schaefer200_17Net_megreNative_maskedGMCortical0p5_ero1mm,
                               mathString="{} -mul {}") for session in
                      self.sessions]), env=self.envs.envFSL)

        self.megre_nativeToMNI_1mm_fromMNI_Mindboggle101 = PipeJobPartial(name="MEGRE_nativeToMNI_1mm_fromMNI_Mindboggle101", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=self.templates.OASIS_TRT_20_jointfusion_DKT31_CMA_labels_in_MNI152_v2,
                                          output=session.subjectPaths.megre.bids_processed.iso1mm.atlas_Mindboggle101_megreNative,
                                          reference=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1InverseWarp],
                                          inverse_transform=[True, True, False],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_nativeToMNI_1mm_Mindboggle101_megreNative_maskedGMCortical0p5_ero1mm = PipeJobPartial(
            name="MEGRE_nativeToMNI_1mm_Mindboggle101_megreNative_maskedGMCortical0p5_ero1mm", job=SchedulerPartial(
                taskList=[FSLMaths(infiles=[session.subjectPaths.megre.bids_processed.iso1mm.atlas_Mindboggle101_megreNative,
                                            session.subjectPaths.megre.bids_processed.fromT1w_GMCortical_thr0p5_ero1mm],
                                   output=session.subjectPaths.megre.bids_processed.iso1mm.atlas_Mindboggle101_megreNative_maskedGMCortical0p5_ero1mm,
                                   mathString="{} -mul {}") for session in
                          self.sessions]), env=self.envs.envFSL)

        # Atlas Stats HammersmithLobar
        self.megre_nativeToMNI_1mm_chiDiamagnetic_stats_HammersmithLobar_maskedWM0p5_ero1mm = PipeJobPartial(name="MEGRE_nativeToMNI_1mm_chiDiamagnetic_stats_HammersmithLobar_maskedWM0p5_ero1mm", job=SchedulerPartial(
            taskList=[ExtractAtlasValues(infile=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                         atlas=session.subjectPaths.megre.bids_processed.iso1mm.atlas_HammersmithLobar_megreNative_maskedWM0p5_ero1mm,
                                         outfile=session.subjectPaths.megre.bids_statistics.chiSepResults_chiNeg_mean_HammersmithLobar_maskedWM0p5_ero1mm,
                                         func="mean") for session in self.sessions]), env=self.envs.envR)

        self.megre_nativeToMNI_1mm_chiParamagnetic_stats_HammersmithLobar_maskedWM0p5_ero1mm = PipeJobPartial(name="MEGRE_nativeToMNI_1mm_chiParamagnetic_stats_HammersmithLobar_maskedWM0p5_ero1mm", job=SchedulerPartial(
            taskList=[ExtractAtlasValues(infile=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                         atlas=session.subjectPaths.megre.bids_processed.iso1mm.atlas_HammersmithLobar_megreNative_maskedWM0p5_ero1mm,
                                         outfile=session.subjectPaths.megre.bids_statistics.chiSepResults_chiPos_mean_HammersmithLobar_maskedWM0p5_ero1mm,
                                         func="mean") for session in self.sessions]), env=self.envs.envR)

        self.megre_nativeToMNI_1mm_QSM_stats_HammersmithLobar_maskedWM0p5_ero1mm = PipeJobPartial(name="MEGRE_nativeToMNI_1mm_QSM_stats_HammersmithLobar_maskedWM0p5_ero1mm", job=SchedulerPartial(
            taskList=[ExtractAtlasValues(infile=session.subjectPaths.megre.bids_processed.QSM,
                                         atlas=session.subjectPaths.megre.bids_processed.iso1mm.atlas_HammersmithLobar_megreNative_maskedWM0p5_ero1mm,
                                         outfile=session.subjectPaths.megre.bids_statistics.chiSepResults_QSM_mean_HammersmithLobar_maskedWM0p5_ero1mm,
                                         func="mean") for session in self.sessions]), env=self.envs.envR)

        # Atlas Stats JHU DTI 1mm
        self.megre_nativeToMNI_1mm_chiDiamagnetic_stats_JHUDTI_1mm_maskedWM0p5_ero1mm = PipeJobPartial(name="MEGRE_nativeToMNI_1mm_chiDiamagnetic_stats_JHUDTI_1mm_maskedWM0p5_ero1mm", job=SchedulerPartial(
            taskList=[ExtractAtlasValues(infile=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                         atlas=session.subjectPaths.megre.bids_processed.iso1mm.atlas_JHUDTI_1mm_megreNative_maskedWM0p5_ero1mm,
                                         outfile=session.subjectPaths.megre.bids_statistics.chiSepResults_chiNeg_mean_JHUDTI_1mm_maskedWM0p5_ero1mm,
                                         func="mean") for session in self.sessions]), env=self.envs.envR)

        self.megre_nativeToMNI_1mm_chiParamagnetic_stats_JHUDTI_1mm_maskedWM0p5_ero1mm = PipeJobPartial(name="MEGRE_nativeToMNI_1mm_chiParamagnetic_stats_JHUDTI_1mm_maskedWM0p5_ero1mm", job=SchedulerPartial(
            taskList=[ExtractAtlasValues(infile=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                         atlas=session.subjectPaths.megre.bids_processed.iso1mm.atlas_JHUDTI_1mm_megreNative_maskedWM0p5_ero1mm,
                                         outfile=session.subjectPaths.megre.bids_statistics.chiSepResults_chiPos_mean_JHUDTI_1mm_maskedWM0p5_ero1mm,
                                         func="mean") for session in self.sessions]), env=self.envs.envR)

        self.megre_nativeToMNI_1mm_QSM_stats_JHUDTI_1mm_maskedWM0p5_ero1mm = PipeJobPartial(name="MEGRE_nativeToMNI_1mm_QSM_stats_JHUDTI_1mm_maskedWM0p5_ero1mm", job=SchedulerPartial(
            taskList=[ExtractAtlasValues(infile=session.subjectPaths.megre.bids_processed.QSM,
                                         atlas=session.subjectPaths.megre.bids_processed.iso1mm.atlas_JHUDTI_1mm_megreNative_maskedWM0p5_ero1mm,
                                         outfile=session.subjectPaths.megre.bids_statistics.chiSepResults_QSM_mean_JHUDTI_1mm_maskedWM0p5_ero1mm,
                                         func="mean") for session in self.sessions]), env=self.envs.envR)

        # Atlas Stats Schafer200 17Net
        self.megre_nativeToMNI_1mm_chiDiamagnetic_stats_Schaefer200_17Net_maskedGM0p5_ero1mm = PipeJobPartial(name="MEGRE_nativeToMNI_1mm_chiDiamagnetic_stats_Schaefer200_17Net_maskedGM0p5_ero1mm", job=SchedulerPartial(
            taskList=[ExtractAtlasValues(infile=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                         atlas=session.subjectPaths.megre.bids_processed.iso1mm.atlas_Schaefer200_17Net_megreNative_maskedGMCortical0p5_ero1mm,
                                         outfile=session.subjectPaths.megre.bids_statistics.chiSepResults_chiNeg_mean_Schaefer200_17Net_maskedGM0p5_ero1mm,
                                         func="mean") for session in self.sessions]), env=self.envs.envR)

        self.megre_nativeToMNI_1mm_chiParamagnetic_stats_Schaefer200_17Net_maskedGM0p5_ero1mm = PipeJobPartial(name="MEGRE_nativeToMNI_1mm_chiParamagnetic_stats_Schaefer200_17Net_maskedGM0p5_ero1mm", job=SchedulerPartial(
            taskList=[ExtractAtlasValues(infile=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                         atlas=session.subjectPaths.megre.bids_processed.iso1mm.atlas_Schaefer200_17Net_megreNative_maskedGMCortical0p5_ero1mm,
                                         outfile=session.subjectPaths.megre.bids_statistics.chiSepResults_chiPos_mean_Schaefer200_17Net_maskedGM0p5_ero1mm,
                                         func="mean") for session in self.sessions]), env=self.envs.envR)

        self.megre_nativeToMNI_1mm_QSM_stats_Schaefer200_17Net_maskedGM0p5_ero1mm = PipeJobPartial(name="MEGRE_nativeToMNI_1mm_QSM_stats_Schaefer200_17Net_maskedGM0p5_ero1mm", job=SchedulerPartial(
            taskList=[ExtractAtlasValues(infile=session.subjectPaths.megre.bids_processed.QSM,
                                         atlas=session.subjectPaths.megre.bids_processed.iso1mm.atlas_Schaefer200_17Net_megreNative_maskedGMCortical0p5_ero1mm,
                                         outfile=session.subjectPaths.megre.bids_statistics.chiSepResults_QSM_mean_Schaefer200_17Net_maskedGM0p5_ero1mm,
                                         func="mean") for session in self.sessions]), env=self.envs.envR)

        # Atlas Stats Mindboggle101
        self.megre_nativeToMNI_1mm_chiDiamagnetic_stats_Mindboggle101_maskedGM0p5_ero1mm = PipeJobPartial(
            name="MEGRE_nativeToMNI_1mm_chiDiamagnetic_stats_Mindboggle101_maskedGM0p5_ero1mm", job=SchedulerPartial(
                taskList=[ExtractAtlasValues(infile=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                             atlas=session.subjectPaths.megre.bids_processed.iso1mm.atlas_Mindboggle101_megreNative_maskedGMCortical0p5_ero1mm,
                                             outfile=session.subjectPaths.megre.bids_statistics.chiSepResults_chiNeg_mean_Mindboggle101_maskedGM0p5_ero1mm,
                                             func="mean") for session in self.sessions]), env=self.envs.envR)

        self.megre_nativeToMNI_1mm_chiParamagnetic_stats_Mindboggle101_maskedGM0p5_ero1mm = PipeJobPartial(
            name="MEGRE_nativeToMNI_1mm_chiParamagnetic_stats_Mindboggle101_maskedGM0p5_ero1mm", job=SchedulerPartial(
                taskList=[ExtractAtlasValues(infile=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                             atlas=session.subjectPaths.megre.bids_processed.iso1mm.atlas_Mindboggle101_megreNative_maskedGMCortical0p5_ero1mm,
                                             outfile=session.subjectPaths.megre.bids_statistics.chiSepResults_chiPos_mean_Mindboggle101_maskedGM0p5_ero1mm,
                                             func="mean") for session in self.sessions]), env=self.envs.envR)

        self.megre_nativeToMNI_1mm_QSM_stats_Mindboggle101_maskedGM0p5_ero1mm = PipeJobPartial(
            name="MEGRE_nativeToMNI_1mm_QSM_stats_Mindboggle101_maskedGM0p5_ero1mm", job=SchedulerPartial(
                taskList=[ExtractAtlasValues(infile=session.subjectPaths.megre.bids_processed.QSM,
                                             atlas=session.subjectPaths.megre.bids_processed.iso1mm.atlas_Mindboggle101_megreNative_maskedGMCortical0p5_ero1mm,
                                             outfile=session.subjectPaths.megre.bids_statistics.chiSepResults_QSM_mean_Mindboggle101_maskedGM0p5_ero1mm,
                                             func="mean") for session in self.sessions]), env=self.envs.envR)

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
                                   memPerCPU=3, minimumMemPerNode=4, partition=self.inputArgs.partition)

        self.megre_NativeToT1w_1p5mm_ChiDia = PipeJobPartial(name="MEGRE_NativeToT1w_1p5mm_ChiDia", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso1p5mm.chiDiamagnetic_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso1p5mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_NativeToT1w_1p5mm_ChiPara = PipeJobPartial(name="MEGRE_NativeToT1w_1p5mm_ChiPara", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso1p5mm.chiParamagnetic_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso1p5mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_NativeToT1w_1p5mm_QSM = PipeJobPartial(name="MEGRE_NativeToT1w_1p5mm_QSM", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.QSM,
                                          output=session.subjectPaths.megre.bids_processed.iso1p5mm.QSM_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso1p5mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)



        # To MNI
        self.megre_NativeToMNI_1p5mm_ChiDia = PipeJobPartial(name="MEGRE_NativeToMNI_1p5mm_ChiDia", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso1p5mm.chiDiamagnetic_toMNI,
                                          reference=self.templates.mni152_1p5mm,
                                          transforms=[session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1Warp,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_NativeToMNI_1p5mm_ChiPara = PipeJobPartial(name="MEGRE_NativeToMNI_1p5mm_ChiPara", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso1p5mm.chiParamagnetic_toMNI,
                                          reference=self.templates.mni152_1p5mm,
                                          transforms=[session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1Warp,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_NativeToMNI_1p5mm_QSM = PipeJobPartial(name="MEGRE_NativeToMNI_1p5mm_QSM", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.QSM,
                                          output=session.subjectPaths.megre.bids_processed.iso1p5mm.QSM_toMNI,
                                          reference=self.templates.mni152_1p5mm,
                                          transforms=[session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1Warp,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

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
                                   memPerCPU=3, minimumMemPerNode=4, partition=self.inputArgs.partition)

        self.megre_NativeToT1w_2mm_ChiDia = PipeJobPartial(name="MEGRE_NativeToT1w_2mm_ChiDia", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso2mm.chiDiamagnetic_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso2mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_NativeToT1w_2mm_ChiPara = PipeJobPartial(name="MEGRE_NativeToT1w_2mm_ChiPara", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso2mm.chiParamagnetic_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso2mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_NativeToT1w_2mm_QSM = PipeJobPartial(name="MEGRE_NativeToT1w_2mm_QSM", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.QSM,
                                          output=session.subjectPaths.megre.bids_processed.iso2mm.QSM_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso2mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)



        # To MNI
        self.megre_NativeToMNI_2mm_ChiDia = PipeJobPartial(name="MEGRE_NativeToMNI_2mm_ChiDia", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso2mm.chiDiamagnetic_toMNI,
                                          reference=self.templates.mni152_2mm,
                                          transforms=[session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1Warp,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_NativeToMNI_2mm_ChiPara = PipeJobPartial(name="MEGRE_NativeToMNI_2mm_ChiPara", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso2mm.chiParamagnetic_toMNI,
                                          reference=self.templates.mni152_2mm,
                                          transforms=[session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1Warp,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_NativeToMNI_2mm_QSM = PipeJobPartial(name="MEGRE_NativeToMNI_2mm_QSM", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.QSM,
                                          output=session.subjectPaths.megre.bids_processed.iso2mm.QSM_toMNI,
                                          reference=self.templates.mni152_2mm,
                                          transforms=[session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1Warp,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

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
                                   memPerCPU=3, minimumMemPerNode=4, partition=self.inputArgs.partition)

        self.megre_NativeToT1w_3mm_ChiDia = PipeJobPartial(name="MEGRE_NativeToT1w_3mm_ChiDia", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso3mm.chiDiamagnetic_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso3mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_NativeToT1w_3mm_ChiPara = PipeJobPartial(name="MEGRE_NativeToT1w_3mm_ChiPara", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso3mm.chiParamagnetic_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso3mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_NativeToT1w_3mm_QSM = PipeJobPartial(name="MEGRE_NativeToT1w_3mm_QSM", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.QSM,
                                          output=session.subjectPaths.megre.bids_processed.iso3mm.QSM_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.iso3mm.baseimage,
                                          transforms=[session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)



        # To MNI
        self.megre_NativeToMNI_3mm_ChiDia = PipeJobPartial(name="MEGRE_NativeToMNI_3mm_ChiDia", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiDiamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso3mm.chiDiamagnetic_toMNI,
                                          reference=self.templates.mni152_3mm,
                                          transforms=[session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1Warp,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_NativeToMNI_3mm_ChiPara = PipeJobPartial(name="MEGRE_NativeToMNI_3mm_ChiPara", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.chiParamagnetic,
                                          output=session.subjectPaths.megre.bids_processed.iso3mm.chiParamagnetic_toMNI,
                                          reference=self.templates.mni152_3mm,
                                          transforms=[session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1Warp,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.megre_NativeToMNI_3mm_QSM = PipeJobPartial(name="MEGRE_NativeToMNI_3mm_QSM", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.megre.bids_processed.QSM,
                                          output=session.subjectPaths.megre.bids_processed.iso3mm.QSM_toMNI,
                                          reference=self.templates.mni152_3mm,
                                          transforms=[session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1Warp,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.megre.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

    def setup(self) -> bool:
        self.addPipeJobs()
        return True