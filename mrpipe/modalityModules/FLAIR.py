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
from mrpipe.Toolboxes.FSL.FSLStats import FSLStats
from mrpipe.Toolboxes.standalone.DenoiseAONLM import DenoiseAONLM
from mrpipe.Toolboxes.standalone.RemoveSmallConnectedComp import RemoveSmallConnectedComp
from mrpipe.Toolboxes.standalone.CCSShapeAnalysis import CCShapeAnalysis
from mrpipe.Toolboxes.standalone.ANTsPyNet_WMH_PVS import AntsPyNet_WMH_PVS
from mrpipe.Toolboxes.standalone.CCStats import CCStats
from mrpipe.Toolboxes.standalone.MARS_WMH import MARS_WMH

class FLAIR_base_withT1w(ProcessingModule):
    requiredModalities = ["T1w", "flair"]
    moduleDependencies = ["T1w_base"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=4)

        self.flair_native_copy = PipeJobPartial(name="FLAIR_native_copy", job=SchedulerPartial(
            taskList=[CP(infile=session.subjectPaths.flair.bids.flair,
                         outfile=session.subjectPaths.flair.bids_processed.flair) for session in
                      self.sessions]), env=self.envs.envMRPipe)

        # TODO change if custom masks is allowed again:
        # #copy flair masks is exists
        # self.flair_native_copyWMH = PipeJobPartial(name="flair_native_copyWMH", job=SchedulerPartial(
        #     taskList=[CP(infile=session.subjectPaths.flair.bids.WMHMask,
        #                  outfile=session.subjectPaths.flair.bids_processed.WMHMask) for session in
        #               self.sessions if session.subjectPaths.flair.bids.WMHMask is not None]), env=self.envs.envMRPipe)

        # Step 1: N4 Bias corrections
        self.N4biasCorrect = PipeJobPartial(name="FLAIR_base_N4biasCorrect", job=SchedulerPartial(
            taskList=[N4BiasFieldCorrect(infile=session.subjectPaths.flair.bids.flair,
                                         outfile=session.subjectPaths.flair.bids_processed.N4BiasCorrected) for session in
                      self.sessions]), env=self.envs.envANTS)


        self.flair_NativeToT1w = PipeJobPartial(name="FLAIR_native_NativeToT1", job=SchedulerPartial(
            taskList=[AntsRegistrationSyN(fixed=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                          moving=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
                                          outprefix=session.subjectPaths.flair.bids_processed.toT1w_prefix,
                                          expectedOutFiles=[session.subjectPaths.flair.bids_processed.toT1w_toT1w,
                                                            session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          ncores=2, dim=3, type="a") for session in self.sessions]),
                                                  env=self.envs.envANTS)

        self.flair_native_fromT1w_WM = PipeJobPartial(name="FLAIR_native_fromT1w_WM", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.maskWMCortical_thr0p5_ero1mm,
                                          output=session.subjectPaths.flair.bids_processed.fromT1w_WMCortical_thr0p5_ero1mm,
                                          reference=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)


        # With LST-AI
        # #Step 2: Create Flair mask if it does not exist
        # #TODO IMPORTANT: this is problematic because the output file does not include the probabilityTemp file,
        # # as it gets removed at the cleaning stage and this should not trigger lstai to be reprocessed. However,
        # # this also has the side effect the 'flair_native_copyWMHProbabilitylstai' does not recognizes lstai as
        # # a dependency which might subsequently fail then. Find Solution. Maybe extra dependency output file or
        # # modify lstai python script to copy the file and not as an extra job?
        # self.flair_native_lstai = PipeJobPartial(name="flair_native_lstai", job=SchedulerPartial(
        #     taskList=[LSTAI(t1w=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
        #                     flair=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
        #                     lstaiSIF=self.libpaths.lstai_singularityContainer,
        #                     inputDir=session.subjectPaths.flair.bids_processed.lstai_inputDir,
        #                     tempDir=session.subjectPaths.flair.bids_processed.lstai_tmpDir,
        #                     outputDir=session.subjectPaths.flair.bids_processed.lstai_outputDir,
        #                     outputFiles=[session.subjectPaths.flair.bids_processed.lstai_outputMask,
        #                                  session.subjectPaths.flair.bids_processed.lstai_outputMaskProbability]) for session in
        #               self.sessions if session.subjectPaths.flair.bids.WMHMask is None],
        #     memPerCPU=3, cpusPerTask=14, minimumMemPerNode=48), env=self.envs.envCuda)
        #
        # self.flair_native_copyWMHProbabilitylstai = PipeJobPartial(name="flair_native_copyWMHProbabilitylstai", job=SchedulerPartial(
        #     taskList=[CP(infile=session.subjectPaths.flair.bids_processed.lstai_outputMaskProbabilityTemp,
        #                  outfile=session.subjectPaths.flair.bids_processed.lstai_outputMaskProbabilityOriginal) for session in
        #               self.sessions if session.subjectPaths.flair.bids.WMHMask is None]), env=self.envs.envMRPipe)
        #
        # self.flair_native_limitWMHProbabilitylstai = PipeJobPartial(name="flair_native_limitWMHProbabilitylstai", job=SchedulerPartial(
        #     taskList=[FSLMaths(infiles=[session.subjectPaths.flair.bids_processed.lstai_outputMaskProbabilityTemp,
        #                                 session.subjectPaths.flair.bids_processed.fromT1w_WMCortical_thr0p5_ero1mm],
        #                        output=session.subjectPaths.flair.bids_processed.lstai_outputMaskProbability,
        #                        mathString="{} -mul {}") for session in
        #               self.sessions if session.subjectPaths.flair.bids.WMHMask is None]), env=self.envs.envFSL)
        #
        # self.flair_native_limitWMHlstai = PipeJobPartial(name="flair_native_limitWMHlstai", job=SchedulerPartial(
        #     taskList=[FSLMaths(infiles=[session.subjectPaths.flair.bids_processed.lstai_outputMask,
        #                                 session.subjectPaths.flair.bids_processed.fromT1w_WMCortical_thr0p5_ero1mm],
        #                        output=session.subjectPaths.flair.bids_processed.WMHMask,
        #                        mathString="{} -mul {}") for session in
        #               self.sessions if session.subjectPaths.flair.bids.WMHMask is None]), env=self.envs.envFSL)


        # With AntsPyNet
        self.flair_native_denoise = PipeJobPartial(name="flair_native_denoise", job=SchedulerPartial(
                taskList=[DenoiseAONLM(infile=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
                                outfile=session.subjectPaths.flair.bids_processed.flair_denoised) for session in
                          self.sessions], # if session.subjectPaths.flair.bids.WMHMask is None
                memPerCPU=3, cpusPerTask=4, minimumMemPerNode=12), env=self.envs.envMatlab)

        self.flair_native_fromT1w_T1 = PipeJobPartial(name="FLAIR_native_fromT1w_T1", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                          output=session.subjectPaths.flair.bids_processed.t1,
                                          reference=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        # self.flair_native_t1_denoise = PipeJobPartial(name="flair_native_t1_denoise", job=SchedulerPartial(
        #     taskList=[DenoiseAONLM(infile=session.subjectPaths.flair.bids_processed.t1,
        #                            outfile=session.subjectPaths.flair.bids_processed.t1_denoised) for session in
        #               self.sessions], # if session.subjectPaths.flair.bids.WMHMask is None
        #     memPerCPU=3, cpusPerTask=4, minimumMemPerNode=12), env=self.envs.envMatlab)

        # self.flair_native_AntsPyNet = PipeJobPartial(name="flair_native_AntsPyNet", job=SchedulerPartial(
        #         taskList=[AntsPyNet_WMH_PVS(t1=session.subjectPaths.flair.bids_processed.t1_denoised,
        #                                     flairReg=session.subjectPaths.flair.bids_processed.flair_denoised,
        #                                     algorithms=['shiva_pvs'],
        #                                     outputTemplate=session.subjectPaths.flair.bids_processed.antspynet_TemplateName,
        #                                     outputFiles=[#session.subjectPaths.flair.bids_processed.antspynet_hypermapp3r,
        #                                                  session.subjectPaths.flair.bids_processed.antspynet_shiva_pvs],
        #                                     antspynetSIF=self.libpaths.antspynet_singularityContainer) for session in
        #                   self.sessions],  memPerCPU=3, cpusPerTask=14, minimumMemPerNode=48), env=self.envs.envCuda)

        self.flair_native_MARSWMH = PipeJobPartial(name="flair_native_MARSWMH", job=SchedulerPartial(
            taskList=[MARS_WMH(t1=session.subjectPaths.flair.bids_processed.t1_denoised,
                               flairReg=session.subjectPaths.flair.bids_processed.flair_denoised,
                               wmhMaskOut=session.subjectPaths.flair.bids_processed.WMHMask_MARS_raw,
                               MarsWMHSIF=self.libpaths.MarsWMHSIF) for session in
                      self.sessions], memPerCPU=3, cpusPerTask=12, minimumMemPerNode=36, ngpus=self.inputArgs.ngpus), env=self.envs.envCuda)

        # self.flair_native_limitWMHProbability_AntsPyNet = PipeJobPartial(name="flair_native_limitWMHProbability_AntsPyNet", job=SchedulerPartial(
        #     taskList=[FSLMaths(infiles=[session.subjectPaths.flair.bids_processed.antspynet_hypermapp3r,
        #                                 session.subjectPaths.flair.bids_processed.fromT1w_WMCortical_thr0p5_ero1mm],
        #                        output=session.subjectPaths.flair.bids_processed.antspynet_hypermapp3r_limitWM,
        #                        mathString="{} -mul {}") for session in
        #               self.sessions]), env=self.envs.envFSL) #  if session.subjectPaths.flair.bids.WMHMask is None

        # self.flair_native_limitWMH_AntsPyNet = PipeJobPartial(name="flair_native_limitWMH_AntsPyNet", job=SchedulerPartial(
        #     taskList=[FSLMaths(infiles=[session.subjectPaths.flair.bids_processed.antspynet_hypermapp3r_limitWM],
        #                        output=session.subjectPaths.flair.bids_processed.WMHMask,
        #                        mathString="{} -thr 0.3 -bin") for session in
        #               self.sessions]), env=self.envs.envFSL) # if session.subjectPaths.flair.bids.WMHMask is None

        # self.flair_native_limitPVSProbability_AntsPyNet = PipeJobPartial(name="flair_native_limitPVSProbability_AntsPyNet", job=SchedulerPartial(
        #     taskList=[FSLMaths(infiles=[session.subjectPaths.flair.bids_processed.antspynet_shiva_pvs,
        #                                 session.subjectPaths.flair.bids_processed.fromT1w_WMCortical_thr0p5_ero1mm],
        #                        output=session.subjectPaths.flair.bids_processed.antspynet_shiva_pvs_limitWM,
        #                        mathString="{} -mul {}") for session in
        #               self.sessions]), env=self.envs.envFSL)
        #
        # self.flair_native_limitPVS_AntsPyNet = PipeJobPartial(name="flair_native_limitPVS_AntsPyNet", job=SchedulerPartial(
        #     taskList=[FSLMaths(infiles=[session.subjectPaths.flair.bids_processed.antspynet_shiva_pvs_limitWM],
        #                        output=session.subjectPaths.flair.bids_processed.PVSMask,
        #                        mathString="{} -thr 0.3 -bin") for session in
        #               self.sessions]), env=self.envs.envFSL)

        self.flair_native_WMH_RemoveSmallCC_MARS = PipeJobPartial(name="flair_native_WMH_RemoveSmallCC_MARS", job=SchedulerPartial(
            taskList=[RemoveSmallConnectedComp(infile=session.subjectPaths.flair.bids_processed.WMHMask_MARS_raw,
                                               outfile=session.subjectPaths.flair.bids_processed.WMHMask_MARS_FilteredCC)
                      for session in self.sessions]), env=self.envs.envMRPipe)

        self.flair_native_limitWMH_MARS = PipeJobPartial(name="flair_native_limitWMH_MARS", job=SchedulerPartial(
            taskList=[FSLMaths(infiles=[session.subjectPaths.flair.bids_processed.WMHMask_MARS_FilteredCC,
                                        session.subjectPaths.flair.bids_processed.fromT1w_WMCortical_thr0p5_ero1mm],
                               output=session.subjectPaths.flair.bids_processed.WMHMask,
                               mathString="{} -mul {}") for session in
                      self.sessions]), env=self.envs.envFSL)

        self.flair_native_qc_vis_toT1w = PipeJobPartial(name="FLAIR_native_slices_toT1w", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.flair.bids_processed.toT1w_toT1w,
                            mask=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                            image=session.subjectPaths.flair.meta_QC.ToT1w_native_slices, contrastAdjustment=False,
                            outline=True, transparency=True, zoom=1) for session in
                      self.sessions]), env=self.envs.envQCVis)


        self.flair_native_WMHToT1w = PipeJobPartial(name="FLAIR_native_WMHToT1w", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.WMHMask,
                                          output=session.subjectPaths.flair.bids_processed.WMHMask_toT1w,
                                          reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        # self.flair_native_PVSToT1w = PipeJobPartial(name="FLAIR_native_PVSToT1w", job=SchedulerPartial(
        #     taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.PVSMask,
        #                                   output=session.subjectPaths.flair.bids_processed.PVSMask_toT1w,
        #                                   reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
        #                                   transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
        #                                   interpolation="NearestNeighbor",
        #                                   verbose=self.inputArgs.verbose <= 30) for session in
        #               self.sessions],
        #     cpusPerTask=2), env=self.envs.envANTS)

        # Flair mask QC
        self.flair_native_qc_vis_wmhMask = PipeJobPartial(name="FLAIR_native_slices_wmhMask", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.flair.bids_processed.flair_denoised,
                            mask=session.subjectPaths.flair.bids_processed.WMHMask,
                            image=session.subjectPaths.flair.meta_QC.wmhMask, contrastAdjustment=False,
                            outline=False, transparency=True, zoom=1, sliceNumber=12) for session in
                      self.sessions]), env=self.envs.envQCVis)
        # # PVS mask QC
        # self.flair_native_qc_vis_pvsMask = PipeJobPartial(name="FLAIR_native_slices_pvsMask", job=SchedulerPartial(
        #     taskList=[QCVis(infile=session.subjectPaths.flair.bids_processed.t1_denoised,
        #                     mask=session.subjectPaths.flair.bids_processed.PVSMask,
        #                     image=session.subjectPaths.flair.meta_QC.pvsMask, contrastAdjustment=False,
        #                     outline=False, transparency=True, zoom=1, sliceNumber=12) for session in
        #               self.sessions]), env=self.envs.envQCVis)

        self.flair_StatsNative_WMHVol = PipeJobPartial(name="FLAIR_StatsNative_WMHVol", job=SchedulerPartial(
            taskList=[FSLStats(infile=session.subjectPaths.flair.bids_processed.WMHMask,
                               output=session.subjectPaths.flair.bids_statistics.WMHVolNative,
                               options=["-V"]) for session in self.sessions],
            cpusPerTask=3), env=self.envs.envFSL)

        self.flair_StatsNative_WMHCount = PipeJobPartial(name="FLAIR_StatsNative_WMHCount", job=SchedulerPartial(
            taskList=[CCStats(infile=session.subjectPaths.flair.bids_processed.WMHMask,
                          output=session.subjectPaths.flair.bids_statistics.WMHCCCount,
                            statistic="countCC"
                          ) for session in self.sessions], cpusPerTask=4), env=self.envs.envMRPipe)

        self.flair_StatsNative_WMHClusterSizeMean = PipeJobPartial(name="FLAIR_StatsNative_WMHClusterSizeMean", job=SchedulerPartial(
            taskList=[CCStats(infile=session.subjectPaths.flair.bids_processed.WMHMask,
                              output=session.subjectPaths.flair.bids_statistics.WMHClusterSizeMean,
                              statistic="meanVolume"
                              ) for session in self.sessions], cpusPerTask=4), env=self.envs.envMRPipe)

        self.flair_StatsNative_WMHClusterSizeSD = PipeJobPartial(name="FLAIR_StatsNative_WMHClusterSizeSD", job=SchedulerPartial(
            taskList=[CCStats(infile=session.subjectPaths.flair.bids_processed.WMHMask,
                              output=session.subjectPaths.flair.bids_statistics.WMHClusterSizeSD,
                              statistic="stdVolume"
                              ) for session in self.sessions], cpusPerTask=4), env=self.envs.envMRPipe)

        self.flair_StatsNative_WMHClusterSizeMin = PipeJobPartial(name="FLAIR_StatsNative_WMHClusterSizeMin", job=SchedulerPartial(
            taskList=[CCStats(infile=session.subjectPaths.flair.bids_processed.WMHMask,
                              output=session.subjectPaths.flair.bids_statistics.WMHClusterSizeMin,
                              statistic="minVolume"
                              ) for session in self.sessions], cpusPerTask=4), env=self.envs.envMRPipe)

        self.flair_StatsNative_WMHClusterSizeMax = PipeJobPartial(name="FLAIR_StatsNative_WMHClusterSizeMax", job=SchedulerPartial(
            taskList=[CCStats(infile=session.subjectPaths.flair.bids_processed.WMHMask,
                              output=session.subjectPaths.flair.bids_statistics.WMHClusterSizeMax,
                              statistic="maxVolume"
                              ) for session in self.sessions], cpusPerTask=4), env=self.envs.envMRPipe)

        self.flair_native_NAWM = PipeJobPartial(name="FLAIR_native_NAWM", job=SchedulerPartial(
            taskList=[FSLMaths(infiles=[session.subjectPaths.flair.bids_processed.fromT1w_WMCortical_thr0p5_ero1mm,
                                        session.subjectPaths.flair.bids_processed.WMHMask],
                                          output=session.subjectPaths.flair.bids_processed.fromT1w_NAWMCortical_thr0p5_ero1mm,
                                          mathString="{} -sub {} -bin") for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        # move LV mask from T1w to flair space
        self.flair_native_fromT1wLV = PipeJobPartial(name="FLAIR_native_fromT1wLV", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.T1w.bids_processed.synthsegLV_thr0p5,
                                          output=session.subjectPaths.flair.bids_processed.fromT1w_LV_thr0p5,
                                          reference=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          inverse_transform=[True],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions], cpusPerTask=2), env=self.envs.envANTS)

        # perform CCShapeAnalysis
        self.flair_native_CCShapeAnalysis = PipeJobPartial(name="FLAIR_native_CCShapeAnalysis", job=SchedulerPartial(
            taskList=[CCShapeAnalysis(infile=session.subjectPaths.flair.bids_processed.WMHMask,
                                      ventricleMask=session.subjectPaths.flair.bids_processed.fromT1w_LV_thr0p5,
                                      outputCSV=session.subjectPaths.flair.bids_statistics.CCShapeAnalysis,
                                      outputStem=session.subjectPaths.flair.bids_processed.CCShapeAnalysisStem,
                                      statistic= "all") for session in
                      self.sessions], cpusPerTask=2), env=self.envs.envANTS)


    def setup(self) -> bool:
        self.addPipeJobs()
        return True

class FLAIR_ToT1wMNI_1mm(ProcessingModule):
    requiredModalities = ["T1w", "flair"]
    moduleDependencies = ["FLAIR_base_withT1w", "T1w_1mm"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=4)

        self.flair_NativeToT1w_1mm = PipeJobPartial(name="FLAIR_NativeToT1w_1mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
                                          output=session.subjectPaths.flair.bids_processed.iso1mm.baseimage,
                                          reference=session.subjectPaths.T1w.bids_processed.iso1mm.baseimage,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.flair_Native_WMHToT1w_1mm = PipeJobPartial(name="FLAIR_Native_WMHToT1w_1mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.WMHMask,
                                          output=session.subjectPaths.flair.bids_processed.iso1mm.WMHMask_toT1,
                                          reference=session.subjectPaths.T1w.bids_processed.iso1mm.baseimage,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)


        #To MNI
        self.flair_NativeToMNI_1mm = PipeJobPartial(name="FLAIR_NativeToMNI_1mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
                                          output=session.subjectPaths.flair.bids_processed.iso1mm.toMNI,
                                          reference=self.templates.mni152_1mm,
                                          transforms=[session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1Warp,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.flair_Native_WMHToMNI_1mm = PipeJobPartial(name="FLAIR_Native_WMHToMNI_1mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.WMHMask,
                                          output=session.subjectPaths.flair.bids_processed.iso1mm.WMHMask_toMNI,
                                          reference=self.templates.mni152_1mm,
                                          transforms=[session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1Warp,
                                                      session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
                                                      session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)


    def setup(self) -> bool:
        self.addPipeJobs()
        return True


class FLAIR_ToT1wMNI_1p5mm(ProcessingModule):
    requiredModalities = ["T1w", "flair"]
    moduleDependencies = ["FLAIR_base_withT1w", "T1w_1p5mm"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=4)

        self.flair_NativeToT1w_1p5mm = PipeJobPartial(name="FLAIR_NativeToT1w_1p5mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
                                          output=session.subjectPaths.flair.bids_processed.iso1p5mm.baseimage,
                                          reference=session.subjectPaths.T1w.bids_processed.iso1p5mm.baseimage,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.flair_Native_WMHToT1w_1p5mm = PipeJobPartial(name="FLAIR_Native_WMHToT1w_1p5mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.WMHMask,
                                          output=session.subjectPaths.flair.bids_processed.iso1p5mm.WMHMask_toT1,
                                          reference=session.subjectPaths.T1w.bids_processed.iso1p5mm.baseimage,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        # To MNI
        self.flair_NativeToMNI_1p5mm = PipeJobPartial(name="FLAIR_NativeToMNI_1p5mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
                                          output=session.subjectPaths.flair.bids_processed.iso1p5mm.toMNI,
                                          reference=self.templates.mni152_1p5mm,
                                          transforms=[session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_1Warp,
                                                      session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_0GenericAffine,
                                                      session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.flair_Native_WMHToMNI_1p5mm = PipeJobPartial(name="FLAIR_Native_WMHToMNI_1p5mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.WMHMask,
                                          output=session.subjectPaths.flair.bids_processed.iso1p5mm.WMHMask_toMNI,
                                          reference=self.templates.mni152_1p5mm,
                                          transforms=[session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_1Warp,
                                                      session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_0GenericAffine,
                                                      session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)


    def setup(self) -> bool:
        self.addPipeJobs()
        return True

class FLAIR_ToT1wMNI_2mm(ProcessingModule):
    requiredModalities = ["T1w", "flair"]
    moduleDependencies = ["FLAIR_base_withT1w", "T1w_2mm"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=4)

        self.flair_NativeToT1w_2mm = PipeJobPartial(name="FLAIR_NativeToT1w_2mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
                                          output=session.subjectPaths.flair.bids_processed.iso2mm.baseimage,
                                          reference=session.subjectPaths.T1w.bids_processed.iso2mm.baseimage,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.flair_Native_WMHToT1w_2mm = PipeJobPartial(name="FLAIR_Native_WMHToT1w_2mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.WMHMask,
                                          output=session.subjectPaths.flair.bids_processed.iso2mm.WMHMask_toT1,
                                          reference=session.subjectPaths.T1w.bids_processed.iso2mm.baseimage,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        # To MNI
        self.flair_NativeToMNI_2mm = PipeJobPartial(name="FLAIR_NativeToMNI_2mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
                                          output=session.subjectPaths.flair.bids_processed.iso2mm.toMNI,
                                          reference=self.templates.mni152_2mm,
                                          transforms=[session.subjectPaths.T1w.bids_processed.iso2mm.MNI_1Warp,
                                                      session.subjectPaths.T1w.bids_processed.iso2mm.MNI_0GenericAffine,
                                                      session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.flair_Native_WMHToMNI_2mm = PipeJobPartial(name="FLAIR_Native_WMHToMNI_2mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.WMHMask,
                                          output=session.subjectPaths.flair.bids_processed.iso2mm.WMHMask_toMNI,
                                          reference=self.templates.mni152_2mm,
                                          transforms=[session.subjectPaths.T1w.bids_processed.iso2mm.MNI_1Warp,
                                                      session.subjectPaths.T1w.bids_processed.iso2mm.MNI_0GenericAffine,
                                                      session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

    def setup(self) -> bool:
        self.addPipeJobs()
        return True


class FLAIR_ToT1wMNI_3mm(ProcessingModule):
    requiredModalities = ["T1w", "flair"]
    moduleDependencies = ["FLAIR_base_withT1w", "T1w_3mm"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=4)

        self.flair_NativeToT1w_3mm = PipeJobPartial(name="FLAIR_NativeToT1w_3mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
                                          output=session.subjectPaths.flair.bids_processed.iso3mm.baseimage,
                                          reference=session.subjectPaths.T1w.bids_processed.iso3mm.baseimage,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.flair_Native_WMHToT1w_3mm = PipeJobPartial(name="FLAIR_Native_WMHToT1w_3mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.WMHMask,
                                          output=session.subjectPaths.flair.bids_processed.iso3mm.WMHMask_toT1,
                                          reference=session.subjectPaths.T1w.bids_processed.iso3mm.baseimage,
                                          transforms=[session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        # To MNI
        self.flair_NativeToMNI_3mm = PipeJobPartial(name="FLAIR_NativeToMNI_3mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.N4BiasCorrected,
                                          output=session.subjectPaths.flair.bids_processed.iso3mm.toMNI,
                                          reference=self.templates.mni152_3mm,
                                          transforms=[session.subjectPaths.T1w.bids_processed.iso3mm.MNI_1Warp,
                                                      session.subjectPaths.T1w.bids_processed.iso3mm.MNI_0GenericAffine,
                                                      session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="BSpline",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

        self.flair_Native_WMHToMNI_3mm = PipeJobPartial(name="FLAIR_Native_WMHToMNI_3mm", job=SchedulerPartial(
            taskList=[AntsApplyTransforms(input=session.subjectPaths.flair.bids_processed.WMHMask,
                                          output=session.subjectPaths.flair.bids_processed.iso3mm.WMHMask_toMNI,
                                          reference=self.templates.mni152_3mm,
                                          transforms=[session.subjectPaths.T1w.bids_processed.iso3mm.MNI_1Warp,
                                                      session.subjectPaths.T1w.bids_processed.iso3mm.MNI_0GenericAffine,
                                                      session.subjectPaths.flair.bids_processed.toT1w_0GenericAffine],
                                          interpolation="NearestNeighbor",
                                          verbose=self.inputArgs.verbose <= 30) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envANTS)

    def setup(self) -> bool:
        self.addPipeJobs()
        return True