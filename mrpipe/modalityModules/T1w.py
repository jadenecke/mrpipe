from mrpipe.Toolboxes.standalone.SelectAtlasROIs import SelectAtlasROIs
from mrpipe.Toolboxes.standalone.CreateConvexHull import CreateConvexHull
from mrpipe.Toolboxes.FSL.FSLStats import FSLStats
from mrpipe.Toolboxes.standalone.CountConnectedComponents import CCC
from mrpipe.Toolboxes.standalone.DenoiseAONLM import DenoiseAONLM
from mrpipe.Toolboxes.standalone.PINGU_PVS import PINGU_PVS
from mrpipe.modalityModules.ProcessingModule import ProcessingModule
from functools import partial
from mrpipe.schedueler.PipeJob import PipeJob
from mrpipe.schedueler import Slurm
from mrpipe.Toolboxes.ANTSTools.N4BiasFieldCorrect import N4BiasFieldCorrect
from mrpipe.Toolboxes.standalone.HDBet import HDBET
from mrpipe.Toolboxes.standalone.SynthSeg import SynthSeg
from mrpipe.Toolboxes.standalone.QCVis import QCVis
from mrpipe.Toolboxes.FSL.Binarize import Binarize
from mrpipe.Toolboxes.FSL.Split4D import Split4D
from mrpipe.Toolboxes.FSL.Add import Add
from mrpipe.Toolboxes.FSL.Erode import Erode
from mrpipe.Toolboxes.standalone.QCVisSynthSeg import QCVisSynthSeg
from mrpipe.Toolboxes.standalone.RecenterToCOM import RecenterToCOM
from mrpipe.Toolboxes.ANTSTools.AntsRegistrationSyN import AntsRegistrationSyN
from mrpipe.Toolboxes.FSL.FlirtResampleToTemplate import FlirtResampleToTemplate
from mrpipe.Toolboxes.FSL.FlirtResampleIso import FlirtResampleIso
from mrpipe.Toolboxes.ANTSTools.AntsApplyTransform import AntsApplyTransforms
from mrpipe.Toolboxes.spm12.cat12 import CAT12
from mrpipe.Toolboxes.spm12.cat12_surf2roi import CAT12_surf2roi
from mrpipe.Toolboxes.spm12.cat12_xml2csv import CAT12_xml2csv
from mrpipe.Toolboxes.spm12.cat12_TIV import CAT12_TIV
from mrpipe.Toolboxes.FSL.FSLMaths import FSLMaths
from mrpipe.Toolboxes.standalone.CAT12_WarpToTemplate import CAT12_WarpToTemplate
from mrpipe.Toolboxes.standalone.CAT12_WarpToTemplate import ValidCat12Interps

class T1w_base(ProcessingModule):
    requiredModalities = ["T1w"]
    moduleDependencies = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=4, partition=self.inputArgs.partition)

        # Step 0: recenter Image to center of mass
        self.recenter = PipeJobPartial(name="T1w_base_recenterToCOM", job=SchedulerPartial(
            taskList=[RecenterToCOM(infile=session.subjectPaths.T1w.bids.T1w.imagePath,
                                    outfile=session.subjectPaths.T1w.bids_processed.recentered
                                    ) for session in
                      self.sessions]),
                                       env=self.envs.envMRPipe)

        # Step 0.1: Run CAT12
        self.cat12 = PipeJobPartial(name="T1w_base_cat12", job=SchedulerPartial(
            taskList=[CAT12(t1w=session.subjectPaths.T1w.bids_processed.cat12.cat12BaseImage, #this is stupidly sensitive because cat12 does not allow for an output directory, but will put the output in the same directory as the input directory.
                            scriptPath=session.subjectPaths.T1w.bids_processed.cat12.cat12Script,
                            outputFiles=[
                                session.subjectPaths.T1w.bids_processed.cat12.cat12_T1_grayMatterProbability,
                                session.subjectPaths.T1w.bids_processed.cat12.cat12_T1_whiteMatterProbability,
                                session.subjectPaths.T1w.bids_processed.cat12.cat12_T1_csfProbability,
                                session.subjectPaths.T1w.bids_processed.cat12.cat12_MNI_grayMatterProbability,
                                session.subjectPaths.T1w.bids_processed.cat12.cat12_MNI_whiteMatterProbability,
                                session.subjectPaths.T1w.bids_processed.cat12.cat12_MNI_csfProbability,
                                session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_InverseWarp,
                                session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                session.subjectPaths.T1w.bids_processed.cat12.cat12_stat_volume,
                                session.subjectPaths.T1w.bids_processed.cat12.cat12_stat_TIV,
                                session.subjectPaths.T1w.bids_processed.cat12.cat12_surf_thickness_lh,
                                session.subjectPaths.T1w.bids_processed.cat12.cat12_surf_thickness_rh
                                         ]) for session in
                      self.sessions], memPerCPU=3, cpusPerTask=8, minimumMemPerNode=24),
                                       env=self.envs.envSPM12)

        # Step 1: N4 Bias corrections
        self.N4biasCorrect = PipeJobPartial(name="T1w_base_N4biasCorrect", job=SchedulerPartial(
            taskList=[N4BiasFieldCorrect(infile=session.subjectPaths.T1w.bids_processed.recentered,
                                         outfile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected) for session in
                      self.sessions],
            cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
            memPerCPU=3, minimumMemPerNode=4), env=self.envs.envANTS)

        # Step 2: Brain extraction using hd-bet
        self.hdbet = PipeJobPartial(name="T1w_base_hdbet", job=SchedulerPartial(
            taskList=[HDBET(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                            brain=session.subjectPaths.T1w.bids_processed.hdbet_brain,
                            mask=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                            useGPU=self.inputArgs.ngpus > 0) for session in
                      self.sessions],
            ngpus=self.inputArgs.ngpus, memPerCPU=3, minimumMemPerNode=12), env=self.envs.envHDBET)


        #other stuff
        self.T1w_base_cat12_GMWMMask = PipeJobPartial(name="T1w_base_cat12_GMWMMask", job=SchedulerPartial(
            taskList=[FSLMaths(infiles=[session.subjectPaths.T1w.bids_processed.cat12.cat12_T1_grayMatterProbability,
                                        session.subjectPaths.T1w.bids_processed.cat12.cat12_T1_whiteMatterProbability],
                               output=session.subjectPaths.T1w.bids_processed.cat12.cat12GMWMMask,
                               mathString="{} -add {} -thr 0.5 -bin") for session in
                      self.sessions]), env=self.envs.envFSL)

        #extract ca12 statistics
        self.cat12_surf_stats = PipeJobPartial(name="T1w_base_surf_stats", job=SchedulerPartial(
            taskList=[CAT12_surf2roi(lh_thickness=session.subjectPaths.T1w.bids_processed.cat12.cat12_surf_thickness_lh,
                                     scriptPath=session.subjectPaths.T1w.bids_processed.cat12.cat12Script_surfStats,
                                     outputFiles=session.subjectPaths.T1w.bids_processed.cat12.cat12_stat_surface
                                     ) for session in
                      self.sessions], memPerCPU=3, cpusPerTask=2, minimumMemPerNode=16),
                                               env=self.envs.envSPM12)

        self.cat12_xml2csv_surf = PipeJobPartial(name="T1w_base_xml2csv_surf", job=SchedulerPartial(
            taskList=[CAT12_xml2csv(xml_path=session.subjectPaths.T1w.bids_processed.cat12.cat12_stat_surface,
                                    scriptPath=session.subjectPaths.T1w.bids_processed.cat12.cat12Script_xml2csv_surf,
                                    out_dir=session.subjectPaths.T1w.bids_statistics.cat12_statsdir,
                                    name_prepend=session.subjectPaths.T1w.bids_statistics.cat12_stats_string,
                                    outputFiles=[
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_aparc_a2009s_thickness,
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_aparc_DK40_thickness,
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_aparc_HCP_MMP1_thickness,
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_Schaefer2018_100Parcels_17Networks_order_thickness,
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_Schaefer2018_200Parcels_17Networks_order_thickness,
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_Schaefer2018_400Parcels_17Networks_order_thickness,
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_Schaefer2018_600Parcels_17Networks_order_thickness
                                    ]) for session in
                      self.sessions], memPerCPU=3, cpusPerTask=2, minimumMemPerNode=16),
                                               env=self.envs.envSPM12)

        self.cat12_xml2csv_volume = PipeJobPartial(name="T1w_base_xml2csv_volume", job=SchedulerPartial(
            taskList=[CAT12_xml2csv(xml_path=session.subjectPaths.T1w.bids_processed.cat12.cat12_stat_volume,
                                    scriptPath=session.subjectPaths.T1w.bids_processed.cat12.cat12Script_xml2csv_vol,
                                    out_dir=session.subjectPaths.T1w.bids_statistics.cat12_statsdir,
                                    name_prepend=session.subjectPaths.T1w.bids_statistics.cat12_stats_string,
                                    outputFiles=[
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_cobra_Vgm,
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_cobra_Vwm,
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_hammers_Vcsf,
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_hammers_Vgm,
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_hammers_Vwm,
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_ibsr_Vcsf,
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_ibsr_Vgm,
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_ibsr_Vwm,
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_lpba40_Vgm,
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_lpba40_Vwm,
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_neuromorphometrics_Vcsf,
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_neuromorphometrics_Vgm,
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_neuromorphometrics_Vwm,
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_suit_Vgm,
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_suit_Vwm,
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_thalamic_nuclei_Vgm,
                                        session.subjectPaths.T1w.bids_statistics.cat12_stats_thalamus_Vgm
                                    ]) for session in
                      self.sessions], memPerCPU=3, cpusPerTask=2, minimumMemPerNode=16),
                                                 env=self.envs.envSPM12)

        self.cat12_TIV = PipeJobPartial(name="T1w_base_cat12_TIV", job=SchedulerPartial(
            taskList=[CAT12_TIV(xml_tiv=session.subjectPaths.T1w.bids_processed.cat12.cat12_stat_TIV,
                                scriptPath=session.subjectPaths.T1w.bids_processed.cat12.cat12Script_statTIV,
                                output=session.subjectPaths.T1w.bids_statistics.cat12_TIV
                                ) for session in
                      self.sessions], memPerCPU=3, cpusPerTask=2, minimumMemPerNode=16),
                                        env=self.envs.envSPM12)



        # self.T1w_base_cat12_GMWMMask = PipeJobPartial(name="T1w_base_cat12_GMWMMask", job=SchedulerPartial(
        #     taskList=[FSLMaths(infiles=[session.subjectPaths.T1w.bids_processed.cat12.cat12_T1_grayMatterProbability,
        #                                 session.subjectPaths.T1w.bids_processed.cat12.cat12_T1_whiteMatterProbability],
        #                        output=session.subjectPaths.T1w.bids_processed.cat12.cat12GMWMMask,
        #                        mathString="{} -add {} -thr 0.5 -bin") for session in
        #               self.sessions]), env=self.envs.envFSL)



        ########## QC ###########
        self.qc_vis_hdbet = PipeJobPartial(name="T1w_base_QC_slices_hdbet", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                            mask=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                            image=session.subjectPaths.T1w.meta_QC.hdbet_slices, contrastAdjustment=True) for session in
                      self.sessions]), env=self.envs.envQCVis)

    def setup(self) -> bool:
        self.addPipeJobs()
        return True


class T1w_SynthSeg(ProcessingModule):
    requiredModalities = ["T1w"]
    moduleDependencies = ["T1w_base"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=4, partition=self.inputArgs.partition)

        # Synthseg Segmentation
        self.synthseg = PipeJobPartial(name="T1w_SynthSeg_SynthSeg", job=SchedulerPartial(
            taskList=[SynthSeg(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                               posterior=session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosterior,
                               posteriorProb=session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorProbabilities,
                               volumes=session.subjectPaths.T1w.bids_statistics.synthsegVolumes,
                               resample=session.subjectPaths.T1w.bids_processed.synthseg.synthsegResample,
                               qc=session.subjectPaths.T1w.meta_QC.synthsegQC,
                               corticalParc=True,
                               useGPU=self.inputArgs.ngpus > 0, ncores=2) for session in
                      self.sessions],
            ngpus=self.inputArgs.ngpus, memPerCPU=3, cpusPerTask=8, minimumMemPerNode=120), env=self.envs.envSynthSeg)
        # has external depencies set in self.setup()

        self.synthsegSplit = PipeJobPartial(name="T1w_SynthSeg_SynthSegSplit", job=SchedulerPartial(
            taskList=[Split4D(infile=session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorProbabilities,
                              stem=session.subjectPaths.T1w.bids_processed.synthseg.synthsegSplitStem,
                              outputNames=[
                                  session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.getAllPaths()])
                      for
                      session in
                      self.sessions],
            memPerCPU=3, cpusPerTask=2, minimumMemPerNode=8), env=self.envs.envFSL)

        # Full masks
        self.GMmerge = PipeJobPartial(name="T1w_SynthSeg_GMmerge", job=SchedulerPartial(
            taskList=[Add(infiles=[
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_cerebral_cortex,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_cerebellum_cortex,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_thalamus,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_caudate,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_putamen,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_pallidum,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_hippocampus,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_amygdala,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_accumbens_area,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_ventral_DC,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_cerebral_cortex,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_cerebellum_cortex,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_thalamus,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_caudate,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_putamen,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_pallidum,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_hippocampus,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_amygdala,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_accumbens_area,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_ventral_DC
            ],
                output=session.subjectPaths.T1w.bids_processed.synthseg.synthsegGM) for session in
                self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.WMmerge = PipeJobPartial(name="T1w_SynthSeg_WMmerge", job=SchedulerPartial(
            taskList=[Add(infiles=[
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_cerebral_white_matter,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_cerebral_white_matter,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_cerebellum_white_matter,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_cerebellum_white_matter,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.brain_stem
            ],
                output=session.subjectPaths.T1w.bids_processed.synthseg.synthsegWM) for session in
                self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.LBGmerge = PipeJobPartial(name="T1w_SynthSeg_LBGmerge", job=SchedulerPartial(
            taskList=[Add(infiles=[
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_thalamus,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_caudate,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_putamen,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_pallidum,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_ventral_DC,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_accumbens_area
            ],
                output=session.subjectPaths.T1w.bids_processed.synthseg.synthsegLBG) for session in
                self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.RBGmerge = PipeJobPartial(name="T1w_SynthSeg_RBGmerge", job=SchedulerPartial(
            taskList=[Add(infiles=[
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_thalamus,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_caudate,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_putamen,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_pallidum,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_ventral_DC,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_accumbens_area
            ],
                output=session.subjectPaths.T1w.bids_processed.synthseg.synthsegRBG) for session in
                self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.CSFmerge = PipeJobPartial(name="T1w_SynthSeg_CSFmerge", job=SchedulerPartial(
            taskList=[Add(infiles=[
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.CSF,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_lateral_ventricle,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_lateral_ventricle,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_inferior_lateral_ventricle,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_inferior_lateral_ventricle,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.d3rd_ventricle,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.d4th_ventricle
            ],
                output=session.subjectPaths.T1w.bids_processed.synthseg.synthsegCSF) for session in
                self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.LVmerge = PipeJobPartial(name="T1w_SynthSeg_LVmerge", job=SchedulerPartial(
            taskList=[Add(infiles=[
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_lateral_ventricle,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_lateral_ventricle,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_inferior_lateral_ventricle,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_inferior_lateral_ventricle,
            ],
                output=session.subjectPaths.T1w.bids_processed.synthseg.synthsegLV) for session in
                self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        # cortical Masks
        self.GMCorticalmerge = PipeJobPartial(name="T1w_SynthSeg_GMCorticalmerge", job=SchedulerPartial(
            taskList=[Add(infiles=[
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_cerebral_cortex,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_cerebral_cortex
            ],
                output=session.subjectPaths.T1w.bids_processed.synthseg.synthsegGMCortical) for session in
                self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.WMCorticalmerge = PipeJobPartial(name="T1w_SynthSeg_WMCorticalmerge", job=SchedulerPartial(
            taskList=[Add(infiles=[
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_cerebral_white_matter,
                session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_cerebral_white_matter
            ],
                output=session.subjectPaths.T1w.bids_processed.synthseg.synthsegWMCortical) for session in
                self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_SynthSeg_GMWM = PipeJobPartial(name="T1w_SynthSeg_GMWM", job=SchedulerPartial(
            taskList=[Add(infiles=[session.subjectPaths.T1w.bids_processed.synthseg.synthsegWM,
                                        session.subjectPaths.T1w.bids_processed.synthseg.synthsegGM],
                               output=session.subjectPaths.T1w.bids_processed.synthseg.synthsegGMWM) for session in
                      self.sessions]), env=self.envs.envFSL)

        self.T1w_SynthSeg_Cerebellum = PipeJobPartial(name="T1w_SynthSeg_Cerebellum", job=SchedulerPartial(
            taskList=[Add(infiles=[session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_cerebellum_white_matter,
                                   session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_cerebellum_white_matter,
                                   session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.right_cerebellum_cortex,
                                   session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosteriorPathNames.left_cerebellum_cortex
                                   ],
                          output=session.subjectPaths.T1w.bids_processed.synthseg.synthsegCerebellum) for session in
                      self.sessions]), env=self.envs.envFSL)


        # Transfrom back to T1 native space
        self.SynthSegToNative_GM = PipeJobPartial(name="T1w_SynthSeg_ToNative_GM", job=SchedulerPartial(
            taskList=[FlirtResampleToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthseg.synthsegGM,
                                              reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                              output=session.subjectPaths.T1w.bids_processed.synthsegGM) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.SynthSegToNative_WM = PipeJobPartial(name="T1w_SynthSeg_ToNative_WM", job=SchedulerPartial(
            taskList=[FlirtResampleToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthseg.synthsegWM,
                                              reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                              output=session.subjectPaths.T1w.bids_processed.synthsegWM) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.SynthSegToNative_CSF = PipeJobPartial(name="T1w_SynthSeg_ToNative_CSF", job=SchedulerPartial(
            taskList=[FlirtResampleToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthseg.synthsegCSF,
                                              reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                              output=session.subjectPaths.T1w.bids_processed.synthsegCSF) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.SynthSegToNative_GMCortical = PipeJobPartial(name="T1w_SynthSeg_ToNative_GMCortical", job=SchedulerPartial(
            taskList=[
                FlirtResampleToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthseg.synthsegGMCortical,
                                        reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                        output=session.subjectPaths.T1w.bids_processed.synthsegGMCortical) for session
                in
                self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.SynthSegToNative_WMCortical = PipeJobPartial(name="T1w_SynthSeg_ToNative_WMCortical", job=SchedulerPartial(
            taskList=[
                FlirtResampleToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthseg.synthsegWMCortical,
                                        reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                        output=session.subjectPaths.T1w.bids_processed.synthsegWMCortical) for session
                in
                self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.SynthSegToNative_LBG = PipeJobPartial(name="T1w_SynthSeg_ToNative_LBG", job=SchedulerPartial(
            taskList=[FlirtResampleToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthseg.synthsegLBG,
                                              reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                              output=session.subjectPaths.T1w.bids_processed.synthsegLBG) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.SynthSegToNative_RBG = PipeJobPartial(name="T1w_SynthSeg_ToNative_RBG", job=SchedulerPartial(
            taskList=[FlirtResampleToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthseg.synthsegRBG,
                                              reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                              output=session.subjectPaths.T1w.bids_processed.synthsegRBG) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.SynthSegToNative_LV = PipeJobPartial(name="T1w_SynthSeg_ToNative_LV", job=SchedulerPartial(
            taskList=[FlirtResampleToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthseg.synthsegLV,
                                              reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                              output=session.subjectPaths.T1w.bids_processed.synthsegLV) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        # Calculate masks from probabilities maps
        self.GMthr0p3 = PipeJobPartial(name="T1w_SynthSeg_GM_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.maskGM_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.GMthr0p3ero1mm = PipeJobPartial(name="T1w_SynthSeg_GM_thr0p3_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.maskGM_thr0p3,
                            output=session.subjectPaths.T1w.bids_processed.maskGM_thr0p3_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.GMthr0p5 = PipeJobPartial(name="T1w_SynthSeg_GM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.maskGM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.GMthr0p5ero1mm = PipeJobPartial(name="T1w_SynthSeg_GM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.maskGM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.maskGM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.WMthr0p5 = PipeJobPartial(name="T1w_SynthSeg_WM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegWM,
                               output=session.subjectPaths.T1w.bids_processed.maskWM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.WMthr0p5ero1mm = PipeJobPartial(name="T1w_SynthSeg_WM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.maskWM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.maskWM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.CSFthr0p9 = PipeJobPartial(name="T1w_SynthSeg_CSF_thr0p9", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegCSF,
                               output=session.subjectPaths.T1w.bids_processed.maskCSF_thr0p9,
                               threshold=0.9) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.CSFthr0p9ero1mm = PipeJobPartial(name="T1w_SynthSeg_CSF_thr0p9_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.maskCSF_thr0p9,
                            output=session.subjectPaths.T1w.bids_processed.maskCSF_thr0p9_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.LV_thr0p5 = PipeJobPartial(name="T1w_SynthSeg_LV_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegLV,
                               output=session.subjectPaths.T1w.bids_processed.synthsegLV_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.GMCorticalthr0p3 = PipeJobPartial(name="T1w_SynthSeg_GMCortical_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegGMCortical,
                               output=session.subjectPaths.T1w.bids_processed.maskGMCortical_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.GMCorticalthr0p3ero1mm = PipeJobPartial(name="T1w_SynthSeg_GMCortical_thr0p3_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.maskGMCortical_thr0p3,
                            output=session.subjectPaths.T1w.bids_processed.maskGMCortical_thr0p3_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.GMCorticalthr0p5 = PipeJobPartial(name="T1w_SynthSeg_GMCortical_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegGMCortical,
                               output=session.subjectPaths.T1w.bids_processed.maskGMCortical_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.GMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_SynthSeg_GMCortical_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.maskGMCortical_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.maskGMCortical_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.WMCorticalthr0p5 = PipeJobPartial(name="T1w_SynthSeg_WMCortical_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegWMCortical,
                               output=session.subjectPaths.T1w.bids_processed.maskWMCortical_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.WMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_SynthSeg_WMCortical_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.maskWMCortical_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.maskWMCortical_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.LBGthr0p5 = PipeJobPartial(name="T1w_SynthSeg_LBG_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegLBG,
                               output=session.subjectPaths.T1w.bids_processed.maskLBG_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.RBGthr0p5 = PipeJobPartial(name="T1w_SynthSeg_RBG_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.synthsegRBG,
                               output=session.subjectPaths.T1w.bids_processed.maskRBG_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.LBGthr0p5_CVS = PipeJobPartial(name="T1w_SynthSeg_LBG_thr0p5_CVS", job=SchedulerPartial(
            taskList=[CreateConvexHull(infile=session.subjectPaths.T1w.bids_processed.maskLBG_thr0p5,
                               outfile=session.subjectPaths.T1w.bids_processed.maskLBG_thr0p5_CVS) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.RBGthr0p5_CVS = PipeJobPartial(name="T1w_SynthSeg_RBG_thr0p5_CVS", job=SchedulerPartial(
            taskList=[CreateConvexHull(infile=session.subjectPaths.T1w.bids_processed.maskRBG_thr0p5,
                               outfile=session.subjectPaths.T1w.bids_processed.maskRBG_thr0p5_CVS) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.LTemporal = PipeJobPartial(name="T1w_SynthSeg_LTemporal", job=SchedulerPartial(
            taskList=[SelectAtlasROIs(infile=session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosterior,
                                       outfile=session.subjectPaths.T1w.bids_processed.maskLTemporal,
                                       ROIs=[1001, 1006, 1007, 1009, 1015, 1016, 1030, 1033, 1034],
                                      binarize=True) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.RTemporal = PipeJobPartial(name="T1w_SynthSeg_RTemporal", job=SchedulerPartial(
            taskList=[SelectAtlasROIs(infile=session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosterior,
                                      outfile=session.subjectPaths.T1w.bids_processed.maskRTemporal,
                                      ROIs=[2001, 2006, 2007, 2009, 2015, 2016, 2030, 2033, 2034],
                                      binarize=True) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.LTemporal_CVS = PipeJobPartial(name="T1w_SynthSeg_LTemporal_CVS", job=SchedulerPartial(
            taskList=[CreateConvexHull(infile=session.subjectPaths.T1w.bids_processed.maskLTemporal,
                                       outfile=session.subjectPaths.T1w.bids_processed.maskLTemporal_CVS) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.RTemporal_CVS = PipeJobPartial(name="T1w_SynthSeg_RTemporal_CVS", job=SchedulerPartial(
            taskList=[CreateConvexHull(infile=session.subjectPaths.T1w.bids_processed.maskRTemporal,
                                       outfile=session.subjectPaths.T1w.bids_processed.maskRTemporal_CVS) for session in
                      self.sessions],
            cpusPerTask=1), env=self.envs.envFSL)

        self.T1w_MB101_toT1w = PipeJobPartial(name="T1w_MB101_toT1w", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=self.templates.OASIS_TRT_20_jointfusion_DKT31_CMA_labels_in_MNI152_v2,
                                           outfile=session.subjectPaths.T1w.bids_processed.OASIS_TRT_20_jointfusion_DKT31_CMA_labels_in_MNI152_v2,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_InverseWarp,
                                           interp=ValidCat12Interps.nearestNeighbor,
                                           voxelsize=1) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        self.T1w_Schafer200_17Net_toT1w = PipeJobPartial(name="T1w_Schafer200_17Net_toT1w", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=self.templates.Schaefer2018_200Parcels_17Networks_order_FSLMNI152_1mm,
                                           outfile=session.subjectPaths.T1w.bids_processed.Schaefer2018_200Parcels_17Networks_order_FSLMNI152_1mm,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_InverseWarp,
                                           interp=ValidCat12Interps.nearestNeighbor,
                                           voxelsize=1) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        self.T1w_MB101_toT1w_GMMask = PipeJobPartial(name="T1w_MB101_toT1w_GMMask", job=SchedulerPartial(
            taskList=[FSLMaths(infiles=[session.subjectPaths.T1w.bids_processed.OASIS_TRT_20_jointfusion_DKT31_CMA_labels_in_MNI152_v2,
                                        session.subjectPaths.T1w.bids_processed.maskGM_thr0p5],
                               output=session.subjectPaths.T1w.bids_processed.OASIS_TRT_20_jointfusion_DKT31_CMA_labels_in_MNI152_v2_gmMasked,
                               mathString="{} -mul {}") for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_Schafer200_17Net_toT1w_GMMask = PipeJobPartial(name="T1w_Schafer200_17Net_toT1w_GMMask", job=SchedulerPartial(
            taskList=[FSLMaths(infiles=[session.subjectPaths.T1w.bids_processed.Schaefer2018_200Parcels_17Networks_order_FSLMNI152_1mm,
                                        session.subjectPaths.T1w.bids_processed.maskGM_thr0p5],
                               output=session.subjectPaths.T1w.bids_processed.Schaefer2018_200Parcels_17Networks_order_FSLMNI152_1mm_gmMasked,
                               mathString="{} -mul {}") for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        ########## QC ############
        self.qc_vis_GMthr0p3 = PipeJobPartial(name="T1w_SynthSeg_QC_slices_GMthr0p3", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                            mask=session.subjectPaths.T1w.bids_processed.maskGM_thr0p3,
                            image=session.subjectPaths.T1w.meta_QC.GMthr0p3_slices,
                            session=session.name,
                            subject=session.subjectName) for session in
                      self.sessions]), env=self.envs.envQCVis)

        self.qc_vis_GMthr0p5 = PipeJobPartial(name="T1w_SynthSeg_QC_slices_GMthr0p5", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                            mask=session.subjectPaths.T1w.bids_processed.maskGM_thr0p5,
                            image=session.subjectPaths.T1w.meta_QC.GMthr0p5_slices,
                            session=session.name,
                            subject=session.subjectName) for session in
                      self.sessions]), env=self.envs.envQCVis)

        self.qc_vis_WMthr0p5 = PipeJobPartial(name="T1w_SynthSeg_QC_slices_WM", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                            mask=session.subjectPaths.T1w.bids_processed.maskWM_thr0p5,
                            image=session.subjectPaths.T1w.meta_QC.WMthr0p5_slices,
                            session=session.name,
                            subject=session.subjectName) for session in
                      self.sessions]), env=self.envs.envQCVis)

        self.qc_vis_CSFthr0p9 = PipeJobPartial(name="T1w_SynthSeg_QC_slices_CSF", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                            mask=session.subjectPaths.T1w.bids_processed.maskCSF_thr0p9,
                            image=session.subjectPaths.T1w.meta_QC.CSFthr0p9_slices,
                            session=session.name,
                            subject=session.subjectName) for session in
                      self.sessions]), env=self.envs.envQCVis)

        self.qc_vis_synthseg = PipeJobPartial(name="T1w_SynthSeg_QC_slices_synthseg", job=SchedulerPartial(
            taskList=[QCVisSynthSeg(infile=session.subjectPaths.T1w.bids_processed.synthseg.synthsegResample,
                                    mask=session.subjectPaths.T1w.bids_processed.synthseg.synthsegPosterior,
                                    image=session.subjectPaths.T1w.meta_QC.synthseg_slices,
                                    session=session.name,
                                    subject=session.subjectName,
                                    tempDir=self.inputArgs.scratch) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envQCVis)

    def setup(self) -> bool:
        self.addPipeJobs()
        return True



class T1w_PVS(ProcessingModule):
    requiredModalities = ["T1w"]
    moduleDependencies = ["T1w_base"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=4, partition=self.inputArgs.partition)

        self.T1w_native_t1_denoise = PipeJobPartial(name="T1w_native_t1_denoise", job=SchedulerPartial(
            taskList=[DenoiseAONLM(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                   outfile=session.subjectPaths.T1w.bids_processed.Denoised) for session in
                      self.sessions], # if session.subjectPaths.T1w.bids.WMHMask is None
            memPerCPU=3, cpusPerTask=4, minimumMemPerNode=12), env=self.envs.envMatlab)

        self.T1w_native_PINGU_PVS = PipeJobPartial(name="T1w_native_PINGU_PVS", job=SchedulerPartial(
            taskList=[PINGU_PVS(input_image=session.subjectPaths.T1w.bids_processed.Denoised,
                                temp_dir=self.basepaths.scratch,
                               output_image=session.subjectPaths.T1w.bids_processed.PinguPVSOut,
                               pingu_sif=self.libpaths.PINGUPVSSif) for session in
                      self.sessions], memPerCPU=3, cpusPerTask=12, minimumMemPerNode=36, ngpus=self.inputArgs.ngpus), env=self.envs.envCuda)

        self.T1w_native_limitPVS = PipeJobPartial(name="T1w_native_limitPVS", job=SchedulerPartial(
            taskList=[FSLMaths(infiles=[session.subjectPaths.T1w.bids_processed.PinguPVSOut,
                                        session.subjectPaths.T1w.bids_processed.maskWMCortical_thr0p5],
                               output=session.subjectPaths.T1w.bids_processed.PVSMask,
                               mathString="{} -mul {}") for session in
                      self.sessions]), env=self.envs.envFSL) # if session.subjectPaths.T1w.bids.WMHMask is None

        # PVS mask QC
        self.T1w_native_qc_vis_PVSMask = PipeJobPartial(name="T1w_native_slices_PVSMask", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.Denoised,
                            mask=session.subjectPaths.T1w.bids_processed.PVSMask,
                            image=session.subjectPaths.T1w.meta_QC.pvsMask, contrastAdjustment=False,
                            outline=False, transparency=True, zoom=1, sliceNumber=6) for session in
                      self.sessions]), env=self.envs.envQCVis)

        self.T1w_StatsNative_PVSVol = PipeJobPartial(name="T1w_StatsNative_PVSVol", job=SchedulerPartial(
            taskList=[FSLStats(infile=session.subjectPaths.T1w.bids_processed.PVSMask,
                               output=session.subjectPaths.T1w.bids_statistics.PVSVolNative,
                               options=["-V"]) for session in self.sessions],
            cpusPerTask=3), env=self.envs.envFSL)

        self.T1w_StatsNative_PVSCount = PipeJobPartial(name="T1w_StatsNative_PVSCount", job=SchedulerPartial(
            taskList=[CCC(infile=session.subjectPaths.T1w.bids_processed.PVSMask,
                          output=session.subjectPaths.T1w.bids_statistics.PVSCount
                          ) for session in self.sessions]), env=self.envs.envMRPipe)

    def setup(self) -> bool:
        # Set external dependencies

        self.addPipeJobs()
        return True


class T1w_1mm(ProcessingModule):
    requiredModalities = ["T1w"]
    moduleDependencies = ["T1w_base", "T1w_SynthSeg"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each jobT1w_base_recenterToCOM step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=4, partition=self.inputArgs.partition)

        self.T1w_1mm_Native = PipeJobPartial(name="T1w_1mm_baseimage", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                       reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                       output=session.subjectPaths.T1w.bids_processed.iso1mm.baseimage,
                                       isoRes=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_Brain = PipeJobPartial(name="T1w_1mm_brain", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.hdbet_brain,
                                       reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                       output=session.subjectPaths.T1w.bids_processed.iso1mm.brain,
                                       isoRes=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_BrainMask = PipeJobPartial(name="T1w_1mm_brainMask", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                                       reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                       output=session.subjectPaths.T1w.bids_processed.iso1mm.brainmask,
                                       isoRes=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        # Register to MNI # done now with cat12 MNI transform
        # self.T1w_1mm_NativeToMNI = PipeJobPartial(name="T1w_1mm_NativeToMNI", job=SchedulerPartial(
        #     taskList=[AntsRegistrationSyN(fixed=self.templates.mni152_1mm,
        #                                   moving=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
        #                                   outprefix=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_prefix,
        #                                   expectedOutFiles=[session.subjectPaths.T1w.bids_processed.iso1mm.MNI_toMNI,
        #                                                     session.subjectPaths.T1w.bids_processed.iso1mm.MNI_0GenericAffine,
        #                                                     session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1Warp,
        #                                                     session.subjectPaths.T1w.bids_processed.iso1mm.MNI_1InverseWarp],
        #                                   ncores=2, dim=3, type="s") for session in
        #               self.sessions],  # something
        #     cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
        #     memPerCPU=3, minimumMemPerNode=4),
        #                                           env=self.envs.envANTS)

        self.T1w_1mm_NativeToMNI = PipeJobPartial(name="T1w_1mm_NativeToMNI", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_toMNI,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=1) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        self.T1w_1mm_qc_vis_MNI = PipeJobPartial(name="T1w_1mm_QC_slices_MNI", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_toMNI,
                            mask=self.templates.cat12_mni152_brain_mask_1mm,
                            image=session.subjectPaths.T1w.meta_QC.MNI_1mm_slices, contrastAdjustment=False,
                            outline=True, transparency=True) for session in
                      self.sessions]), env=self.envs.envQCVis)

        # SynthSeg Masks Native Space
        self.T1w_1mm_synthsegGM = PipeJobPartial(name="T1w_1mm_synthsegGM", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                                       reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                       output=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegGM,
                                       isoRes=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)


        self.T1w_1mm_synthsegWM = PipeJobPartial(name="T1w_1mm_synthsegWM", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegWM,
                                       reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                       output=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegWM,
                                       isoRes=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_synthsegCSF = PipeJobPartial(name="T1w_1mm_synthsegCSF", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegCSF,
                                       reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                       output=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegCSF,
                                       isoRes=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_synthsegGMCortical = PipeJobPartial(name="T1w_1mm_synthsegGMCortical", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegGMCortical,
                                       reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                       output=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegGMCortical,
                                       isoRes=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_synthsegWMCortical = PipeJobPartial(name="T1w_1mm_synthsegWMCortical", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegWMCortical,
                                       reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                       output=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegWMCortical,
                                       isoRes=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        # Calculate masks from probabilities maps
        self.T1w_1mm_GMthr0p3 = PipeJobPartial(name="T1w_1mm_SynthSeg_GM_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso1mm.maskGM_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_GMthr0p3ero1mm = PipeJobPartial(name="T1w_1mm_SynthSeg_GM_thr0p3_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso1mm.maskGM_thr0p3,
                            output=session.subjectPaths.T1w.bids_processed.iso1mm.maskGM_thr0p3_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_GMthr0p5 = PipeJobPartial(name="T1w_1mm_SynthSeg_GM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso1mm.maskGM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_GMthr0p5ero1mm = PipeJobPartial(name="T1w_1mm_SynthSeg_GM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso1mm.maskGM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.iso1mm.maskGM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_WMthr0p5 = PipeJobPartial(name="T1w_1mm_SynthSeg_WM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegWM,
                               output=session.subjectPaths.T1w.bids_processed.iso1mm.maskWM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_WMthr0p5ero1mm = PipeJobPartial(name="T1w_1mm_SynthSeg_WM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso1mm.maskWM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.iso1mm.maskWM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_CSFthr0p9 = PipeJobPartial(name="T1w_1mm_SynthSeg_CSF_thr0p9", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegCSF,
                               output=session.subjectPaths.T1w.bids_processed.iso1mm.maskCSF_thr0p9,
                               threshold=0.9) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_CSFthr0p9ero1mm = PipeJobPartial(name="T1w_1mm_SynthSeg_CSF_thr0p9_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso1mm.maskCSF_thr0p9,
                            output=session.subjectPaths.T1w.bids_processed.iso1mm.maskCSF_thr0p9_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_GMCorticalthr0p3 = PipeJobPartial(name="T1w_1mm_SynthSeg_GMCortical_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegGMCortical,
                               output=session.subjectPaths.T1w.bids_processed.iso1mm.maskGMCortical_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_GMCorticalthr0p3ero1mm = PipeJobPartial(name="T1w_1mm_SynthSeg_GMCortical_thr0p3_ero1mm",
                                                             job=SchedulerPartial(
                                                                 taskList=[Erode(
                                                                     infile=session.subjectPaths.T1w.bids_processed.iso1mm.maskGMCortical_thr0p3,
                                                                     output=session.subjectPaths.T1w.bids_processed.iso1mm.maskGMCortical_thr0p3_ero1mm,
                                                                     size=1) for session in
                                                                           self.sessions],
                                                                 cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_GMCorticalthr0p5 = PipeJobPartial(name="T1w_1mm_SynthSeg_GMCortical_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegGMCortical,
                               output=session.subjectPaths.T1w.bids_processed.iso1mm.maskGMCortical_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_GMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_1mm_SynthSeg_GMCortical_thr0p5_ero1mm",
                                                             job=SchedulerPartial(
                                                                 taskList=[Erode(
                                                                     infile=session.subjectPaths.T1w.bids_processed.iso1mm.maskGMCortical_thr0p5,
                                                                     output=session.subjectPaths.T1w.bids_processed.iso1mm.maskGMCortical_thr0p5_ero1mm,
                                                                     size=1) for session in
                                                                           self.sessions],
                                                                 cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_WMCorticalthr0p5 = PipeJobPartial(name="T1w_1mm_SynthSeg_WMCortical_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1mm.synthsegWMCortical,
                               output=session.subjectPaths.T1w.bids_processed.iso1mm.maskWMCortical_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_WMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_1mm_SynthSeg_WMCortical_thr0p5_ero1mm",
                                                             job=SchedulerPartial(
                                                                 taskList=[Erode(
                                                                     infile=session.subjectPaths.T1w.bids_processed.iso1mm.maskWMCortical_thr0p5,
                                                                     output=session.subjectPaths.T1w.bids_processed.iso1mm.maskWMCortical_thr0p5_ero1mm,
                                                                     size=1) for session in
                                                                           self.sessions],
                                                                 cpusPerTask=2), env=self.envs.envFSL)

        # self.megre_toCat12MNI_chiDia = PipeJobPartial(name="MEGRE_toCat12MNI_chiDia", job=SchedulerPartial(
        #     taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.megre.bids_processed.chiDiamagnetic_toT1w,
        #                                    warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
        #                                    outfile=session.subjectPaths.megre.bids_processed.iso1mm.chiDiamagnetic_cat12MNI,
        #                                    ) for session in
        #               self.sessions]), env=self.envs.envSPM12)

        # SynthSeg Masks MNI Space
        self.T1w_1mm_MNI_synthsegGM = PipeJobPartial(name="T1w_1mm_MNI_synthsegGM", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_synthsegGM,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=1) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)



        self.T1w_1mm_MNI_synthsegWM = PipeJobPartial(name="T1w_1mm_MNI_synthsegWM", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthsegWM,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_synthsegWM,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=1) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        self.T1w_1mm_MNI_synthsegCSF = PipeJobPartial(name="T1w_1mm_MNI_synthsegCSF", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthsegCSF,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_synthsegCSF,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=1) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        self.T1w_1mm_MNI_synthsegGMCortical = PipeJobPartial(name="T1w_1mm_MNI_synthsegGMCortical", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthsegGMCortical,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_synthsegGMCortical,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=1) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        self.T1w_1mm_MNI_synthsegWMCortical = PipeJobPartial(name="T1w_1mm_MNI_synthsegWMCortical", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthsegWMCortical,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_synthsegWMCortical,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=1) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        # Calculate masks from probabilities maps
        self.T1w_1mm_MNI_GMthr0p3 = PipeJobPartial(name="T1w_1mm_MNI_SynthSeg_GM_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_maskGM_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_MNI_GMthr0p3ero1mm = PipeJobPartial(name="T1w_1mm_MNI_SynthSeg_GM_thr0p3_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_maskGM_thr0p3,
                            output=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_maskGM_thr0p3_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_MNI_GMthr0p5 = PipeJobPartial(name="T1w_1mm_MNI_SynthSeg_GM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_maskGM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_MNI_GMthr0p5ero1mm = PipeJobPartial(name="T1w_1mm_MNI_SynthSeg_GM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_maskGM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_maskGM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_MNI_WMthr0p5 = PipeJobPartial(name="T1w_1mm_MNI_SynthSeg_WM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_synthsegWM,
                               output=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_maskWM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_MNI_WMthr0p5ero1mm = PipeJobPartial(name="T1w_1mm_MNI_SynthSeg_WM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_maskWM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_maskWM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_MNI_CSFthr0p9 = PipeJobPartial(name="T1w_1mm_MNI_SynthSeg_CSF_thr0p9", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_synthsegCSF,
                               output=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_maskCSF_thr0p9,
                               threshold=0.9) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_MNI_CSFthr0p9ero1mm = PipeJobPartial(name="T1w_1mm_MNI_SynthSeg_CSF_thr0p9_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_maskCSF_thr0p9,
                            output=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_maskCSF_thr0p9_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_MNI_GMCorticalthr0p3 = PipeJobPartial(name="T1w_1mm_MNI_SynthSeg_GMCortical_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_synthsegGMCortical,
                               output=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_maskGMCortical_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_MNI_GMCorticalthr0p3ero1mm = PipeJobPartial(name="T1w_1mm_MNI_SynthSeg_GMCortical_thr0p3_ero1mm",
                                                             job=SchedulerPartial(
                                                                 taskList=[Erode(
                                                                     infile=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_maskGMCortical_thr0p3,
                                                                     output=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_maskGMCortical_thr0p3_ero1mm,
                                                                     size=1) for session in
                                                                     self.sessions],
                                                                 cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_MNI_GMCorticalthr0p5 = PipeJobPartial(name="T1w_1mm_MNI_SynthSeg_GMCortical_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_synthsegGMCortical,
                               output=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_maskGMCortical_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_MNI_GMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_1mm_MNI_SynthSeg_GMCortical_thr0p5_ero1mm",
                                                             job=SchedulerPartial(
                                                                 taskList=[Erode(
                                                                     infile=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_maskGMCortical_thr0p5,
                                                                     output=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_maskGMCortical_thr0p5_ero1mm,
                                                                     size=1) for session in
                                                                     self.sessions],
                                                                 cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_MNI_WMCorticalthr0p5 = PipeJobPartial(name="T1w_1mm_MNI_SynthSeg_WMCortical_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_synthsegWMCortical,
                               output=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_maskWMCortical_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1mm_MNI_WMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_1mm_MNI_SynthSeg_WMCortical_thr0p5_ero1mm",
                                                             job=SchedulerPartial(
                                                                 taskList=[Erode(
                                                                     infile=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_maskWMCortical_thr0p5,
                                                                     output=session.subjectPaths.T1w.bids_processed.iso1mm.MNI_maskWMCortical_thr0p5_ero1mm,
                                                                     size=1) for session in
                                                                     self.sessions],
                                                                 cpusPerTask=2), env=self.envs.envFSL)

    def setup(self) -> bool:
        # Set external dependencies
        # MNI

        self.addPipeJobs()
        return True


class T1w_1p5mm(ProcessingModule):
    requiredModalities = ["T1w"]
    moduleDependencies = ["T1w_base", "T1w_SynthSeg"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=4, partition=self.inputArgs.partition)

        self.T1w_1p5mm_Native = PipeJobPartial(name="T1w_1p5mm_baseimage", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                       reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                       output=session.subjectPaths.T1w.bids_processed.iso1p5mm.baseimage,
                                       isoRes=1.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_Brain = PipeJobPartial(name="T1w_1p5mm_brain", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.hdbet_brain,
                                       reference=session.subjectPaths.T1w.bids_processed.hdbet_brain,
                                       output=session.subjectPaths.T1w.bids_processed.iso1p5mm.brain,
                                       isoRes=1.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_BrainMask = PipeJobPartial(name="T1w_1p5mm_brainMask", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                                       reference=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                                       output=session.subjectPaths.T1w.bids_processed.iso1p5mm.brainmask,
                                       isoRes=1.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        # Register to MNI
        # self.T1w_1p5mm_NativeToMNI = PipeJobPartial(name="T1w_1p5mm_NativeToMNI", job=SchedulerPartial(
        #     taskList=[AntsRegistrationSyN(fixed=self.templates.mni152_1p5mm,
        #                                   moving=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
        #                                   outprefix=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_prefix,
        #                                   expectedOutFiles=[session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_toMNI,
        #                                                     session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_0GenericAffine,
        #                                                     session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_1Warp,
        #                                                     session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_1InverseWarp],
        #                                   ncores=2, dim=3, type="s") for session in
        #               self.sessions],  # something
        #     cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
        #     memPerCPU=3, minimumMemPerNode=4),
        #                                             env=self.envs.envANTS)

        self.T1w_1p5mm_NativeToMNI = PipeJobPartial(name="T1w_1p5mm_NativeToMNI", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_toMNI,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=1.5) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)


        self.T1w_1p5mm_qc_vis_MNI = PipeJobPartial(name="T1w_1p5mm_QC_slices_MNI", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_toMNI,
                            mask=self.templates.mni152_brain_mask_1p5mm,
                            image=session.subjectPaths.T1w.meta_QC.MNI_1p5mm_slices, contrastAdjustment=False,
                            outline=True, transparency=True, zoom=1.5) for session in
                      self.sessions]), env=self.envs.envQCVis)

        # SynthSeg Masks
        self.T1w_1p5mm_synthsegGM = PipeJobPartial(name="T1w_1p5mm_synthsegGM", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                                       reference=self.templates.mni152_1p5mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegGM,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_synthsegWM = PipeJobPartial(name="T1w_1p5mm_synthsegWM", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegWM,
                                       reference=self.templates.mni152_1p5mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegWM,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_synthsegCSF = PipeJobPartial(name="T1w_1p5mm_synthsegCSF", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegCSF,
                                       reference=self.templates.mni152_1p5mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegCSF,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_synthsegGMCortical = PipeJobPartial(name="T1w_1p5mm_synthsegGMCortical", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegGMCortical,
                                       reference=self.templates.mni152_1p5mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegGMCortical,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_synthsegWMCortical = PipeJobPartial(name="T1w_1p5mm_synthsegWMCortical", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegWMCortical,
                                       reference=self.templates.mni152_1p5mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegWMCortical,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        # Calculate masks from probabilities maps
        self.T1w_1p5mm_GMthr0p3 = PipeJobPartial(name="T1w_1p5mm_SynthSeg_GM_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGM_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_GMthr0p3ero1mm = PipeJobPartial(name="T1w_1p5mm_SynthSeg_GM_thr0p3_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGM_thr0p3,
                            output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGM_thr0p3_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_GMthr0p5 = PipeJobPartial(name="T1w_1p5mm_SynthSeg_GM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_GMthr0p5ero1mm = PipeJobPartial(name="T1w_1p5mm_SynthSeg_GM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_WMthr0p5 = PipeJobPartial(name="T1w_1p5mm_SynthSeg_WM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegWM,
                               output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskWM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_WMthr0p5ero1mm = PipeJobPartial(name="T1w_1p5mm_SynthSeg_WM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskWM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskWM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_CSFthr0p9 = PipeJobPartial(name="T1w_1p5mm_SynthSeg_CSF_thr0p9", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegCSF,
                               output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskCSF_thr0p9,
                               threshold=0.9) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_CSFthr0p9ero1mm = PipeJobPartial(name="T1w_1p5mm_SynthSeg_CSF_thr0p9_ero1mm",
                                                        job=SchedulerPartial(
                                                            taskList=[Erode(
                                                                infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskCSF_thr0p9,
                                                                output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskCSF_thr0p9_ero1mm,
                                                                size=1) for session in
                                                                      self.sessions],
                                                            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_GMCorticalthr0p3 = PipeJobPartial(name="T1w_1p5mm_SynthSeg_GMCortical_thr0p3",
                                                         job=SchedulerPartial(
                                                             taskList=[Binarize(
                                                                 infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegGMCortical,
                                                                 output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGMCortical_thr0p3,
                                                                 threshold=0.3) for session in
                                                                       self.sessions],
                                                             cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_GMCorticalthr0p3ero1mm = PipeJobPartial(name="T1w_1p5mm_SynthSeg_GMCortical_thr0p3_ero1mm",
                                                               job=SchedulerPartial(
                                                                   taskList=[Erode(
                                                                       infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGMCortical_thr0p3,
                                                                       output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGMCortical_thr0p3_ero1mm,
                                                                       size=1) for session in
                                                                             self.sessions],
                                                                   cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_GMCorticalthr0p5 = PipeJobPartial(name="T1w_1p5mm_SynthSeg_GMCortical_thr0p5",
                                                         job=SchedulerPartial(
                                                             taskList=[Binarize(
                                                                 infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegGMCortical,
                                                                 output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGMCortical_thr0p5,
                                                                 threshold=0.5) for session in
                                                                       self.sessions],
                                                             cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_GMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_1p5mm_SynthSeg_GMCortical_thr0p5_ero1mm",
                                                               job=SchedulerPartial(
                                                                   taskList=[Erode(
                                                                       infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGMCortical_thr0p5,
                                                                       output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskGMCortical_thr0p5_ero1mm,
                                                                       size=1) for session in
                                                                             self.sessions],
                                                                   cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_WMCorticalthr0p5 = PipeJobPartial(name="T1w_1p5mm_SynthSeg_WMCortical_thr0p5",
                                                         job=SchedulerPartial(
                                                             taskList=[Binarize(
                                                                 infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.synthsegWMCortical,
                                                                 output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskWMCortical_thr0p5,
                                                                 threshold=0.5) for session in
                                                                       self.sessions],
                                                             cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_WMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_1p5mm_SynthSeg_WMCortical_thr0p5_ero1mm",
                                                               job=SchedulerPartial(
                                                                   taskList=[Erode(
                                                                       infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskWMCortical_thr0p5,
                                                                       output=session.subjectPaths.T1w.bids_processed.iso1p5mm.maskWMCortical_thr0p5_ero1mm,
                                                                       size=1) for session in
                                                                             self.sessions],
                                                                   cpusPerTask=2), env=self.envs.envFSL)

        # SynthSeg Masks MNI Space
        self.T1w_1p5mm_MNI_synthsegGM = PipeJobPartial(name="T1w_1p5mm_MNI_synthsegGM", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_synthsegGM,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=1.5) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        self.T1w_1p5mm_MNI_synthsegWM = PipeJobPartial(name="T1w_1p5mm_MNI_synthsegWM", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthsegWM,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_synthsegWM,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=1.5) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        self.T1w_1p5mm_MNI_synthsegCSF = PipeJobPartial(name="T1w_1p5mm_MNI_synthsegCSF", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthsegCSF,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_synthsegCSF,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=1.5) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        self.T1w_1p5mm_MNI_synthsegGMCortical = PipeJobPartial(name="T1w_1p5mm_MNI_synthsegGMCortical", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthsegGMCortical,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_synthsegGMCortical,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=1.5) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        self.T1w_1p5mm_MNI_synthsegWMCortical = PipeJobPartial(name="T1w_1p5mm_MNI_synthsegWMCortical", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthsegWMCortical,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_synthsegWMCortical,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=1.5) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        # Calculate masks from probabilities maps
        self.T1w_1p5mm_MNI_GMthr0p3 = PipeJobPartial(name="T1w_1p5mm_MNI_SynthSeg_GM_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_maskGM_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_MNI_GMthr0p3ero1mm = PipeJobPartial(name="T1w_1p5mm_MNI_SynthSeg_GM_thr0p3_ero1mm",
                                                         job=SchedulerPartial(
                                                             taskList=[Erode(
                                                                 infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_maskGM_thr0p3,
                                                                 output=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_maskGM_thr0p3_ero1mm,
                                                                 size=1) for session in
                                                                       self.sessions],
                                                             cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_MNI_GMthr0p5 = PipeJobPartial(name="T1w_1p5mm_MNI_SynthSeg_GM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_maskGM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_MNI_GMthr0p5ero1mm = PipeJobPartial(name="T1w_1p5mm_MNI_SynthSeg_GM_thr0p5_ero1mm",
                                                         job=SchedulerPartial(
                                                             taskList=[Erode(
                                                                 infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_maskGM_thr0p5,
                                                                 output=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_maskGM_thr0p5_ero1mm,
                                                                 size=1) for session in
                                                                       self.sessions],
                                                             cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_MNI_WMthr0p5 = PipeJobPartial(name="T1w_1p5mm_MNI_SynthSeg_WM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_synthsegWM,
                               output=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_maskWM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_MNI_WMthr0p5ero1mm = PipeJobPartial(name="T1w_1p5mm_MNI_SynthSeg_WM_thr0p5_ero1mm",
                                                         job=SchedulerPartial(
                                                             taskList=[Erode(
                                                                 infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_maskWM_thr0p5,
                                                                 output=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_maskWM_thr0p5_ero1mm,
                                                                 size=1) for session in
                                                                       self.sessions],
                                                             cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_MNI_CSFthr0p9 = PipeJobPartial(name="T1w_1p5mm_MNI_SynthSeg_CSF_thr0p9", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_synthsegCSF,
                               output=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_maskCSF_thr0p9,
                               threshold=0.9) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_MNI_CSFthr0p9ero1mm = PipeJobPartial(name="T1w_1p5mm_MNI_SynthSeg_CSF_thr0p9_ero1mm",
                                                          job=SchedulerPartial(
                                                              taskList=[Erode(
                                                                  infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_maskCSF_thr0p9,
                                                                  output=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_maskCSF_thr0p9_ero1mm,
                                                                  size=1) for session in
                                                                        self.sessions],
                                                              cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_MNI_GMCorticalthr0p3 = PipeJobPartial(name="T1w_1p5mm_MNI_SynthSeg_GMCortical_thr0p3",
                                                           job=SchedulerPartial(
                                                               taskList=[Binarize(
                                                                   infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_synthsegGMCortical,
                                                                   output=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_maskGMCortical_thr0p3,
                                                                   threshold=0.3) for session in
                                                                         self.sessions],
                                                               cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_MNI_GMCorticalthr0p3ero1mm = PipeJobPartial(name="T1w_1p5mm_MNI_SynthSeg_GMCortical_thr0p3_ero1mm",
                                                                 job=SchedulerPartial(
                                                                     taskList=[Erode(
                                                                         infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_maskGMCortical_thr0p3,
                                                                         output=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_maskGMCortical_thr0p3_ero1mm,
                                                                         size=1) for session in
                                                                         self.sessions],
                                                                     cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_MNI_GMCorticalthr0p5 = PipeJobPartial(name="T1w_1p5mm_MNI_SynthSeg_GMCortical_thr0p5",
                                                           job=SchedulerPartial(
                                                               taskList=[Binarize(
                                                                   infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_synthsegGMCortical,
                                                                   output=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_maskGMCortical_thr0p5,
                                                                   threshold=0.5) for session in
                                                                         self.sessions],
                                                               cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_MNI_GMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_1p5mm_MNI_SynthSeg_GMCortical_thr0p5_ero1mm",
                                                                 job=SchedulerPartial(
                                                                     taskList=[Erode(
                                                                         infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_maskGMCortical_thr0p5,
                                                                         output=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_maskGMCortical_thr0p5_ero1mm,
                                                                         size=1) for session in
                                                                         self.sessions],
                                                                     cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_MNI_WMCorticalthr0p5 = PipeJobPartial(name="T1w_1p5mm_MNI_SynthSeg_WMCortical_thr0p5",
                                                           job=SchedulerPartial(
                                                               taskList=[Binarize(
                                                                   infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_synthsegWMCortical,
                                                                   output=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_maskWMCortical_thr0p5,
                                                                   threshold=0.5) for session in
                                                                         self.sessions],
                                                               cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_1p5mm_MNI_WMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_1p5mm_MNI_SynthSeg_WMCortical_thr0p5_ero1mm",
                                                                 job=SchedulerPartial(
                                                                     taskList=[Erode(
                                                                         infile=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_maskWMCortical_thr0p5,
                                                                         output=session.subjectPaths.T1w.bids_processed.iso1p5mm.MNI_maskWMCortical_thr0p5_ero1mm,
                                                                         size=1) for session in
                                                                         self.sessions],
                                                                     cpusPerTask=2), env=self.envs.envFSL)

    def setup(self) -> bool:
        # Set external dependencies

        # MNI

        self.addPipeJobs()
        return True


class T1w_2mm(ProcessingModule):
    requiredModalities = ["T1w"]
    moduleDependencies = ["T1w_base", "T1w_SynthSeg"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=4, partition=self.inputArgs.partition)

        self.T1w_2mm_Native = PipeJobPartial(name="T1w_2mm_baseimage", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                       reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                       output=session.subjectPaths.T1w.bids_processed.iso2mm.baseimage,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_Brain = PipeJobPartial(name="T1w_2mm_brain", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.hdbet_brain,
                                       reference=session.subjectPaths.T1w.bids_processed.hdbet_brain,
                                       output=session.subjectPaths.T1w.bids_processed.iso2mm.brain,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_BrainMask = PipeJobPartial(name="T1w_2mm_brainMask", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                                       reference=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                                       output=session.subjectPaths.T1w.bids_processed.iso2mm.brainmask,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        # # Register to MNI # Done now with cat12 MNI transfrom
        # self.T1w_2mm_NativeToMNI = PipeJobPartial(name="T1w_2mm_NativeToMNI", job=SchedulerPartial(
        #     taskList=[AntsRegistrationSyN(fixed=self.templates.mni152_2mm,
        #                                   moving=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
        #                                   outprefix=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_prefix,
        #                                   expectedOutFiles=[session.subjectPaths.T1w.bids_processed.iso2mm.MNI_toMNI,
        #                                                     session.subjectPaths.T1w.bids_processed.iso2mm.MNI_0GenericAffine,
        #                                                     session.subjectPaths.T1w.bids_processed.iso2mm.MNI_1Warp,
        #                                                     session.subjectPaths.T1w.bids_processed.iso2mm.MNI_1InverseWarp],
        #                                   ncores=2, dim=3, type="s") for session in
        #               self.sessions],  # something
        #     cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
        #     memPerCPU=3, minimumMemPerNode=4),
        #                                           env=self.envs.envANTS)

        self.T1w_2mm_NativeToMNI = PipeJobPartial(name="T1w_2mm_NativeToMNI", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_toMNI,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=2) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        self.T1w_2mm_qc_vis_MNI = PipeJobPartial(name="T1w_2mm_QC_slices_MNI", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_toMNI,
                            mask=self.templates.mni152_brain_mask_2mm,
                            image=session.subjectPaths.T1w.meta_QC.MNI_2mm_slices, contrastAdjustment=False,
                            outline=True, transparency=True, zoom=2) for session in
                      self.sessions]), env=self.envs.envQCVis)

        # SynthSeg Masks        
        self.T1w_2mm_synthsegGM = PipeJobPartial(name="T1w_2mm_synthsegGM", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                                       reference=self.templates.mni152_2mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegGM,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_synthsegWM = PipeJobPartial(name="T1w_2mm_synthsegWM", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegWM,
                                       reference=self.templates.mni152_2mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegWM,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_synthsegCSF = PipeJobPartial(name="T1w_2mm_synthsegCSF", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegCSF,
                                       reference=self.templates.mni152_2mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegCSF,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_synthsegGMCortical = PipeJobPartial(name="T1w_2mm_synthsegGMCortical", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegGMCortical,
                                       reference=self.templates.mni152_2mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegGMCortical,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_synthsegWMCortical = PipeJobPartial(name="T1w_2mm_synthsegWMCortical", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegWMCortical,
                                       reference=self.templates.mni152_2mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegWMCortical,
                                       isoRes=2) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        # Calculate masks from probabilities maps
        self.T1w_2mm_GMthr0p3 = PipeJobPartial(name="T1w_2mm_SynthSeg_GM_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso2mm.maskGM_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_GMthr0p3ero1mm = PipeJobPartial(name="T1w_2mm_SynthSeg_GM_thr0p3_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso2mm.maskGM_thr0p3,
                            output=session.subjectPaths.T1w.bids_processed.iso2mm.maskGM_thr0p3_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_GMthr0p5 = PipeJobPartial(name="T1w_2mm_SynthSeg_GM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso2mm.maskGM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_GMthr0p5ero1mm = PipeJobPartial(name="T1w_2mm_SynthSeg_GM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso2mm.maskGM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.iso2mm.maskGM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_WMthr0p5 = PipeJobPartial(name="T1w_2mm_SynthSeg_WM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegWM,
                               output=session.subjectPaths.T1w.bids_processed.iso2mm.maskWM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_WMthr0p5ero1mm = PipeJobPartial(name="T1w_2mm_SynthSeg_WM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso2mm.maskWM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.iso2mm.maskWM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_CSFthr0p9 = PipeJobPartial(name="T1w_2mm_SynthSeg_CSF_thr0p9", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegCSF,
                               output=session.subjectPaths.T1w.bids_processed.iso2mm.maskCSF_thr0p9,
                               threshold=0.9) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_CSFthr0p9ero1mm = PipeJobPartial(name="T1w_2mm_SynthSeg_CSF_thr0p9_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso2mm.maskCSF_thr0p9,
                            output=session.subjectPaths.T1w.bids_processed.iso2mm.maskCSF_thr0p9_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_GMCorticalthr0p3 = PipeJobPartial(name="T1w_2mm_SynthSeg_GMCortical_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegGMCortical,
                               output=session.subjectPaths.T1w.bids_processed.iso2mm.maskGMCortical_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_GMCorticalthr0p3ero1mm = PipeJobPartial(name="T1w_2mm_SynthSeg_GMCortical_thr0p3_ero1mm",
                                                             job=SchedulerPartial(
                                                                 taskList=[Erode(
                                                                     infile=session.subjectPaths.T1w.bids_processed.iso2mm.maskGMCortical_thr0p3,
                                                                     output=session.subjectPaths.T1w.bids_processed.iso2mm.maskGMCortical_thr0p3_ero1mm,
                                                                     size=1) for session in
                                                                           self.sessions],
                                                                 cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_GMCorticalthr0p5 = PipeJobPartial(name="T1w_2mm_SynthSeg_GMCortical_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegGMCortical,
                               output=session.subjectPaths.T1w.bids_processed.iso2mm.maskGMCortical_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_GMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_2mm_SynthSeg_GMCortical_thr0p5_ero1mm",
                                                             job=SchedulerPartial(
                                                                 taskList=[Erode(
                                                                     infile=session.subjectPaths.T1w.bids_processed.iso2mm.maskGMCortical_thr0p5,
                                                                     output=session.subjectPaths.T1w.bids_processed.iso2mm.maskGMCortical_thr0p5_ero1mm,
                                                                     size=1) for session in
                                                                           self.sessions],
                                                                 cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_WMCorticalthr0p5 = PipeJobPartial(name="T1w_2mm_SynthSeg_WMCortical_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso2mm.synthsegWMCortical,
                               output=session.subjectPaths.T1w.bids_processed.iso2mm.maskWMCortical_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_WMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_2mm_SynthSeg_WMCortical_thr0p5_ero1mm",
                                                             job=SchedulerPartial(
                                                                 taskList=[Erode(
                                                                     infile=session.subjectPaths.T1w.bids_processed.iso2mm.maskWMCortical_thr0p5,
                                                                     output=session.subjectPaths.T1w.bids_processed.iso2mm.maskWMCortical_thr0p5_ero1mm,
                                                                     size=1) for session in
                                                                           self.sessions],
                                                                 cpusPerTask=2), env=self.envs.envFSL)

        # SynthSeg Masks MNI Space
        self.T1w_2mm_MNI_synthsegGM = PipeJobPartial(name="T1w_2mm_MNI_synthsegGM", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_synthsegGM,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=2) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        self.T1w_2mm_MNI_synthsegWM = PipeJobPartial(name="T1w_2mm_MNI_synthsegWM", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthsegWM,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_synthsegWM,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=2) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        self.T1w_2mm_MNI_synthsegCSF = PipeJobPartial(name="T1w_2mm_MNI_synthsegCSF", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthsegCSF,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_synthsegCSF,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=2) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        self.T1w_2mm_MNI_synthsegGMCortical = PipeJobPartial(name="T1w_2mm_MNI_synthsegGMCortical", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthsegGMCortical,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_synthsegGMCortical,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=2) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        self.T1w_2mm_MNI_synthsegWMCortical = PipeJobPartial(name="T1w_2mm_MNI_synthsegWMCortical", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthsegWMCortical,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_synthsegWMCortical,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=2) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        # Calculate masks from probabilities maps
        self.T1w_2mm_MNI_GMthr0p3 = PipeJobPartial(name="T1w_2mm_MNI_SynthSeg_GM_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_maskGM_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_MNI_GMthr0p3ero1mm = PipeJobPartial(name="T1w_2mm_MNI_SynthSeg_GM_thr0p3_ero1mm",
                                                         job=SchedulerPartial(
                                                             taskList=[Erode(
                                                                 infile=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_maskGM_thr0p3,
                                                                 output=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_maskGM_thr0p3_ero1mm,
                                                                 size=1) for session in
                                                                       self.sessions],
                                                             cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_MNI_GMthr0p5 = PipeJobPartial(name="T1w_2mm_MNI_SynthSeg_GM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_maskGM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_MNI_GMthr0p5ero1mm = PipeJobPartial(name="T1w_2mm_MNI_SynthSeg_GM_thr0p5_ero1mm",
                                                         job=SchedulerPartial(
                                                             taskList=[Erode(
                                                                 infile=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_maskGM_thr0p5,
                                                                 output=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_maskGM_thr0p5_ero1mm,
                                                                 size=1) for session in
                                                                       self.sessions],
                                                             cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_MNI_WMthr0p5 = PipeJobPartial(name="T1w_2mm_MNI_SynthSeg_WM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_synthsegWM,
                               output=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_maskWM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_MNI_WMthr0p5ero1mm = PipeJobPartial(name="T1w_2mm_MNI_SynthSeg_WM_thr0p5_ero1mm",
                                                         job=SchedulerPartial(
                                                             taskList=[Erode(
                                                                 infile=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_maskWM_thr0p5,
                                                                 output=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_maskWM_thr0p5_ero1mm,
                                                                 size=1) for session in
                                                                       self.sessions],
                                                             cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_MNI_CSFthr0p9 = PipeJobPartial(name="T1w_2mm_MNI_SynthSeg_CSF_thr0p9", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_synthsegCSF,
                               output=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_maskCSF_thr0p9,
                               threshold=0.9) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_MNI_CSFthr0p9ero1mm = PipeJobPartial(name="T1w_2mm_MNI_SynthSeg_CSF_thr0p9_ero1mm",
                                                          job=SchedulerPartial(
                                                              taskList=[Erode(
                                                                  infile=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_maskCSF_thr0p9,
                                                                  output=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_maskCSF_thr0p9_ero1mm,
                                                                  size=1) for session in
                                                                        self.sessions],
                                                              cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_MNI_GMCorticalthr0p3 = PipeJobPartial(name="T1w_2mm_MNI_SynthSeg_GMCortical_thr0p3",
                                                           job=SchedulerPartial(
                                                               taskList=[Binarize(
                                                                   infile=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_synthsegGMCortical,
                                                                   output=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_maskGMCortical_thr0p3,
                                                                   threshold=0.3) for session in
                                                                         self.sessions],
                                                               cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_MNI_GMCorticalthr0p3ero1mm = PipeJobPartial(name="T1w_2mm_MNI_SynthSeg_GMCortical_thr0p3_ero1mm",
                                                                 job=SchedulerPartial(
                                                                     taskList=[Erode(
                                                                         infile=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_maskGMCortical_thr0p3,
                                                                         output=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_maskGMCortical_thr0p3_ero1mm,
                                                                         size=1) for session in
                                                                         self.sessions],
                                                                     cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_MNI_GMCorticalthr0p5 = PipeJobPartial(name="T1w_2mm_MNI_SynthSeg_GMCortical_thr0p5",
                                                           job=SchedulerPartial(
                                                               taskList=[Binarize(
                                                                   infile=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_synthsegGMCortical,
                                                                   output=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_maskGMCortical_thr0p5,
                                                                   threshold=0.5) for session in
                                                                         self.sessions],
                                                               cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_MNI_GMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_2mm_MNI_SynthSeg_GMCortical_thr0p5_ero1mm",
                                                                 job=SchedulerPartial(
                                                                     taskList=[Erode(
                                                                         infile=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_maskGMCortical_thr0p5,
                                                                         output=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_maskGMCortical_thr0p5_ero1mm,
                                                                         size=1) for session in
                                                                         self.sessions],
                                                                     cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_MNI_WMCorticalthr0p5 = PipeJobPartial(name="T1w_2mm_MNI_SynthSeg_WMCortical_thr0p5",
                                                           job=SchedulerPartial(
                                                               taskList=[Binarize(
                                                                   infile=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_synthsegWMCortical,
                                                                   output=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_maskWMCortical_thr0p5,
                                                                   threshold=0.5) for session in
                                                                         self.sessions],
                                                               cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_2mm_MNI_WMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_2mm_MNI_SynthSeg_WMCortical_thr0p5_ero1mm",
                                                                 job=SchedulerPartial(
                                                                     taskList=[Erode(
                                                                         infile=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_maskWMCortical_thr0p5,
                                                                         output=session.subjectPaths.T1w.bids_processed.iso2mm.MNI_maskWMCortical_thr0p5_ero1mm,
                                                                         size=1) for session in
                                                                         self.sessions],
                                                                     cpusPerTask=2), env=self.envs.envFSL)
    def setup(self) -> bool:
        # Set external dependencies

        # MNI

        self.addPipeJobs()
        return True


class T1w_3mm(ProcessingModule):
    requiredModalities = ["T1w"]
    moduleDependencies = ["T1w_base", "T1w_SynthSeg"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create Partials to avoid repeating arguments in each job step:
        PipeJobPartial = partial(PipeJob, basepaths=self.basepaths, moduleName=self.moduleName)
        SchedulerPartial = partial(Slurm.Scheduler, cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
                                   memPerCPU=3, minimumMemPerNode=4, partition=self.inputArgs.partition)

        self.T1w_3mm_Native = PipeJobPartial(name="T1w_3mm_baseimage", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                       reference=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                       output=session.subjectPaths.T1w.bids_processed.iso3mm.baseimage,
                                       isoRes=3) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_Brain = PipeJobPartial(name="T1w_3mm_brain", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.hdbet_brain,
                                       reference=session.subjectPaths.T1w.bids_processed.hdbet_brain,
                                       output=session.subjectPaths.T1w.bids_processed.iso3mm.brain,
                                       isoRes=3) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_BrainMask = PipeJobPartial(name="T1w_3mm_brainMask", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                                       reference=session.subjectPaths.T1w.bids_processed.hdbet_mask,
                                       output=session.subjectPaths.T1w.bids_processed.iso3mm.brainmask,
                                       isoRes=3) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        # Register to MNI # Using Cat12 MNI estimate from now on.
        # self.T1w_3mm_NativeToMNI = PipeJobPartial(name="T1w_3mm_NativeToMNI", job=SchedulerPartial(
        #     taskList=[AntsRegistrationSyN(fixed=self.templates.mni152_3mm,
        #                                   moving=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
        #                                   outprefix=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_prefix,
        #                                   expectedOutFiles=[session.subjectPaths.T1w.bids_processed.iso3mm.MNI_toMNI,
        #                                                     session.subjectPaths.T1w.bids_processed.iso3mm.MNI_0GenericAffine,
        #                                                     session.subjectPaths.T1w.bids_processed.iso3mm.MNI_1Warp,
        #                                                     session.subjectPaths.T1w.bids_processed.iso3mm.MNI_1InverseWarp],
        #                                   ncores=2, dim=3, type="s") for session in
        #               self.sessions], # something
        #     cpusPerTask=2, cpusTotal=self.inputArgs.ncores,
        #     memPerCPU=3, minimumMemPerNode=4),
        #                                           env=self.envs.envANTS)

        self.T1w_3mm_NativeToMNI = PipeJobPartial(name="T1w_3mm_NativeToMNI", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.N4BiasCorrected,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_toMNI,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=3) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        self.T1w_3mm_qc_vis_MNI = PipeJobPartial(name="T1w_3mm_QC_slices_MNI", job=SchedulerPartial(
            taskList=[QCVis(infile=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_toMNI,
                            mask=self.templates.mni152_brain_mask_3mm,
                            image=session.subjectPaths.T1w.meta_QC.MNI_3mm_slices, contrastAdjustment=False,
                            outline=True, transparency=True, zoom=3) for session in
                      self.sessions]), env=self.envs.envQCVis)

        # SynthSeg Masks
        self.T1w_3mm_synthsegGM = PipeJobPartial(name="T1w_3mm_synthsegGM", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                                       reference=self.templates.mni152_3mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegGM,
                                       isoRes=3) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_synthsegWM = PipeJobPartial(name="T1w_3mm_synthsegWM", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegWM,
                                       reference=self.templates.mni152_3mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegWM,
                                       isoRes=3) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_synthsegCSF = PipeJobPartial(name="T1w_3mm_synthsegCSF", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegCSF,
                                       reference=self.templates.mni152_3mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegCSF,
                                       isoRes=3) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_synthsegGMCortical = PipeJobPartial(name="T1w_3mm_synthsegGMCortical", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegGMCortical,
                                       reference=self.templates.mni152_3mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegGMCortical,
                                       isoRes=3) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_synthsegWMCortical = PipeJobPartial(name="T1w_3mm_synthsegWMCortical", job=SchedulerPartial(
            taskList=[FlirtResampleIso(infile=session.subjectPaths.T1w.bids_processed.synthsegWMCortical,
                                       reference=self.templates.mni152_3mm,
                                       output=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegWMCortical,
                                       isoRes=3) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        # Calculate masks from probabilities maps
        self.T1w_3mm_GMthr0p3 = PipeJobPartial(name="T1w_3mm_SynthSeg_GM_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso3mm.maskGM_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_GMthr0p3ero1mm = PipeJobPartial(name="T1w_3mm_SynthSeg_GM_thr0p3_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso3mm.maskGM_thr0p3,
                            output=session.subjectPaths.T1w.bids_processed.iso3mm.maskGM_thr0p3_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_GMthr0p5 = PipeJobPartial(name="T1w_3mm_SynthSeg_GM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso3mm.maskGM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_GMthr0p5ero1mm = PipeJobPartial(name="T1w_3mm_SynthSeg_GM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso3mm.maskGM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.iso3mm.maskGM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_WMthr0p5 = PipeJobPartial(name="T1w_3mm_SynthSeg_WM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegWM,
                               output=session.subjectPaths.T1w.bids_processed.iso3mm.maskWM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_WMthr0p5ero1mm = PipeJobPartial(name="T1w_3mm_SynthSeg_WM_thr0p5_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso3mm.maskWM_thr0p5,
                            output=session.subjectPaths.T1w.bids_processed.iso3mm.maskWM_thr0p5_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_CSFthr0p9 = PipeJobPartial(name="T1w_3mm_SynthSeg_CSF_thr0p9", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegCSF,
                               output=session.subjectPaths.T1w.bids_processed.iso3mm.maskCSF_thr0p9,
                               threshold=0.9) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_CSFthr0p9ero1mm = PipeJobPartial(name="T1w_3mm_SynthSeg_CSF_thr0p9_ero1mm", job=SchedulerPartial(
            taskList=[Erode(infile=session.subjectPaths.T1w.bids_processed.iso3mm.maskCSF_thr0p9,
                            output=session.subjectPaths.T1w.bids_processed.iso3mm.maskCSF_thr0p9_ero1mm,
                            size=1) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_GMCorticalthr0p3 = PipeJobPartial(name="T1w_3mm_SynthSeg_GMCortical_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegGMCortical,
                               output=session.subjectPaths.T1w.bids_processed.iso3mm.maskGMCortical_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_GMCorticalthr0p3ero1mm = PipeJobPartial(name="T1w_3mm_SynthSeg_GMCortical_thr0p3_ero1mm",
                                                             job=SchedulerPartial(
                                                                 taskList=[Erode(
                                                                     infile=session.subjectPaths.T1w.bids_processed.iso3mm.maskGMCortical_thr0p3,
                                                                     output=session.subjectPaths.T1w.bids_processed.iso3mm.maskGMCortical_thr0p3_ero1mm,
                                                                     size=1) for session in
                                                                           self.sessions],
                                                                 cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_GMCorticalthr0p5 = PipeJobPartial(name="T1w_3mm_SynthSeg_GMCortical_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegGMCortical,
                               output=session.subjectPaths.T1w.bids_processed.iso3mm.maskGMCortical_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_GMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_3mm_SynthSeg_GMCortical_thr0p5_ero1mm",
                                                             job=SchedulerPartial(
                                                                 taskList=[Erode(
                                                                     infile=session.subjectPaths.T1w.bids_processed.iso3mm.maskGMCortical_thr0p5,
                                                                     output=session.subjectPaths.T1w.bids_processed.iso3mm.maskGMCortical_thr0p5_ero1mm,
                                                                     size=1) for session in
                                                                           self.sessions],
                                                                 cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_WMCorticalthr0p5 = PipeJobPartial(name="T1w_3mm_SynthSeg_WMCortical_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso3mm.synthsegWMCortical,
                               output=session.subjectPaths.T1w.bids_processed.iso3mm.maskWMCortical_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_WMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_3mm_SynthSeg_WMCortical_thr0p5_ero1mm",
                                                             job=SchedulerPartial(
                                                                 taskList=[Erode(
                                                                     infile=session.subjectPaths.T1w.bids_processed.iso3mm.maskWMCortical_thr0p5,
                                                                     output=session.subjectPaths.T1w.bids_processed.iso3mm.maskWMCortical_thr0p5_ero1mm,
                                                                     size=1) for session in
                                                                           self.sessions],
                                                                 cpusPerTask=2), env=self.envs.envFSL)

        # SynthSeg Masks MNI Space
        self.T1w_3mm_MNI_synthsegGM = PipeJobPartial(name="T1w_3mm_MNI_synthsegGM", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthsegGM,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_synthsegGM,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=3) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        self.T1w_3mm_MNI_synthsegWM = PipeJobPartial(name="T1w_3mm_MNI_synthsegWM", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthsegWM,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_synthsegWM,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=3) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        self.T1w_3mm_MNI_synthsegCSF = PipeJobPartial(name="T1w_3mm_MNI_synthsegCSF", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthsegCSF,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_synthsegCSF,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=3) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        self.T1w_3mm_MNI_synthsegGMCortical = PipeJobPartial(name="T1w_3mm_MNI_synthsegGMCortical", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthsegGMCortical,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_synthsegGMCortical,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=3) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        self.T1w_3mm_MNI_synthsegWMCortical = PipeJobPartial(name="T1w_3mm_MNI_synthsegWMCortical", job=SchedulerPartial(
            taskList=[CAT12_WarpToTemplate(infile=session.subjectPaths.T1w.bids_processed.synthsegWMCortical,
                                           outfile=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_synthsegWMCortical,
                                           warpfile=session.subjectPaths.T1w.bids_processed.cat12.cat12_T1ToMNI_Warp,
                                           interp=ValidCat12Interps.bspline_3rd,
                                           voxelsize=3) for session in
                      self.sessions],
            cpusPerTask=3), env=self.envs.envSPM12)

        # Calculate masks from probabilities maps
        self.T1w_3mm_MNI_GMthr0p3 = PipeJobPartial(name="T1w_3mm_MNI_SynthSeg_GM_thr0p3", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_maskGM_thr0p3,
                               threshold=0.3) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_MNI_GMthr0p3ero1mm = PipeJobPartial(name="T1w_3mm_MNI_SynthSeg_GM_thr0p3_ero1mm",
                                                         job=SchedulerPartial(
                                                             taskList=[Erode(
                                                                 infile=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_maskGM_thr0p3,
                                                                 output=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_maskGM_thr0p3_ero1mm,
                                                                 size=1) for session in
                                                                       self.sessions],
                                                             cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_MNI_GMthr0p5 = PipeJobPartial(name="T1w_3mm_MNI_SynthSeg_GM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_synthsegGM,
                               output=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_maskGM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_MNI_GMthr0p5ero1mm = PipeJobPartial(name="T1w_3mm_MNI_SynthSeg_GM_thr0p5_ero1mm",
                                                         job=SchedulerPartial(
                                                             taskList=[Erode(
                                                                 infile=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_maskGM_thr0p5,
                                                                 output=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_maskGM_thr0p5_ero1mm,
                                                                 size=1) for session in
                                                                       self.sessions],
                                                             cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_MNI_WMthr0p5 = PipeJobPartial(name="T1w_3mm_MNI_SynthSeg_WM_thr0p5", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_synthsegWM,
                               output=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_maskWM_thr0p5,
                               threshold=0.5) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_MNI_WMthr0p5ero1mm = PipeJobPartial(name="T1w_3mm_MNI_SynthSeg_WM_thr0p5_ero1mm",
                                                         job=SchedulerPartial(
                                                             taskList=[Erode(
                                                                 infile=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_maskWM_thr0p5,
                                                                 output=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_maskWM_thr0p5_ero1mm,
                                                                 size=1) for session in
                                                                       self.sessions],
                                                             cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_MNI_CSFthr0p9 = PipeJobPartial(name="T1w_3mm_MNI_SynthSeg_CSF_thr0p9", job=SchedulerPartial(
            taskList=[Binarize(infile=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_synthsegCSF,
                               output=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_maskCSF_thr0p9,
                               threshold=0.9) for session in
                      self.sessions],
            cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_MNI_CSFthr0p9ero1mm = PipeJobPartial(name="T1w_3mm_MNI_SynthSeg_CSF_thr0p9_ero1mm",
                                                          job=SchedulerPartial(
                                                              taskList=[Erode(
                                                                  infile=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_maskCSF_thr0p9,
                                                                  output=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_maskCSF_thr0p9_ero1mm,
                                                                  size=1) for session in
                                                                        self.sessions],
                                                              cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_MNI_GMCorticalthr0p3 = PipeJobPartial(name="T1w_3mm_MNI_SynthSeg_GMCortical_thr0p3",
                                                           job=SchedulerPartial(
                                                               taskList=[Binarize(
                                                                   infile=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_synthsegGMCortical,
                                                                   output=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_maskGMCortical_thr0p3,
                                                                   threshold=0.3) for session in
                                                                         self.sessions],
                                                               cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_MNI_GMCorticalthr0p3ero1mm = PipeJobPartial(name="T1w_3mm_MNI_SynthSeg_GMCortical_thr0p3_ero1mm",
                                                                 job=SchedulerPartial(
                                                                     taskList=[Erode(
                                                                         infile=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_maskGMCortical_thr0p3,
                                                                         output=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_maskGMCortical_thr0p3_ero1mm,
                                                                         size=1) for session in
                                                                         self.sessions],
                                                                     cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_MNI_GMCorticalthr0p5 = PipeJobPartial(name="T1w_3mm_MNI_SynthSeg_GMCortical_thr0p5",
                                                           job=SchedulerPartial(
                                                               taskList=[Binarize(
                                                                   infile=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_synthsegGMCortical,
                                                                   output=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_maskGMCortical_thr0p5,
                                                                   threshold=0.5) for session in
                                                                         self.sessions],
                                                               cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_MNI_GMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_3mm_MNI_SynthSeg_GMCortical_thr0p5_ero1mm",
                                                                 job=SchedulerPartial(
                                                                     taskList=[Erode(
                                                                         infile=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_maskGMCortical_thr0p5,
                                                                         output=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_maskGMCortical_thr0p5_ero1mm,
                                                                         size=1) for session in
                                                                         self.sessions],
                                                                     cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_MNI_WMCorticalthr0p5 = PipeJobPartial(name="T1w_3mm_MNI_SynthSeg_WMCortical_thr0p5",
                                                           job=SchedulerPartial(
                                                               taskList=[Binarize(
                                                                   infile=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_synthsegWMCortical,
                                                                   output=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_maskWMCortical_thr0p5,
                                                                   threshold=0.5) for session in
                                                                         self.sessions],
                                                               cpusPerTask=2), env=self.envs.envFSL)

        self.T1w_3mm_MNI_WMCorticalthr0p5ero1mm = PipeJobPartial(name="T1w_3mm_MNI_SynthSeg_WMCortical_thr0p5_ero1mm",
                                                                 job=SchedulerPartial(
                                                                     taskList=[Erode(
                                                                         infile=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_maskWMCortical_thr0p5,
                                                                         output=session.subjectPaths.T1w.bids_processed.iso3mm.MNI_maskWMCortical_thr0p5_ero1mm,
                                                                         size=1) for session in
                                                                         self.sessions],
                                                                     cpusPerTask=2), env=self.envs.envFSL)

    def setup(self) -> bool:
        # Set external dependencies

        # MNI

        self.addPipeJobs()
        return True
