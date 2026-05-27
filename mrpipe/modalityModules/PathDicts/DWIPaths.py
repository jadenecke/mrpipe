import os.path
from typing import List

from mrpipe.meta import LoggerModule
import numpy as np

from mrpipe.meta.ImageWithSideCar import ImageWithSideCar
from mrpipe.modalityModules.PathDicts.BasePaths import PathBase
from mrpipe.meta.PathClass import Path
from mrpipe.meta.PathClass import StatsFilePath
from mrpipe.meta.PathCollection import PathCollection
from mrpipe.meta.ImageSeries import DWI

logger = LoggerModule.Logger()

class PathDictDWI(PathCollection):
    class Bids(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename, *args, **kwargs):
            super().__init__(name="dwi_bids", *args, **kwargs)
            self.basedir = Path(os.path.join(basepaths.bidsPath, filler), isDirectory=True)
            self.basename = Path(os.path.join(basepaths.bidsPath, filler, nameFormatter.format(subj=sub, ses=ses, basename=basename)))
            self.dwi = DWI(self.basedir, onlyWithReversePhaseEncoding=self.inputArgs.onlyWithReversePhaseEncoding,
                           bval_tol=self.inputArgs.bval_tol, non_gaussian_cutoff=self.inputArgs.non_gaussian_cutoff, faultyDWISessions=basepaths.faultyDWISessions,
                           onlyMultiShell=self.inputArgs.onlyMultiShell)


    class Bids_processed(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="dwi_bidsProcessed")
            basenameWithoutPath = nameFormatter.format(subj=sub, ses=ses, basename=basename)
            self.baseString = basenameWithoutPath
            self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler), isDirectory=True)
            self.basename = self.basedir.join(basenameWithoutPath)
            self.basemif = self.basename + ".mif"
            self.acqparams = self.basename + "_acqparams.txt"
            self.index = self.basename + "_index.txt"
            self.denoised = self.basename + "_dns.mif"
            self.degibbs = self.basename + "_dns_dgbs.mif"
            self.firstb0 = self.basename + "_firstb0.nii.gz"
            self.degibbs_nifti = ImageWithSideCar(self.basename + "_dns_dgbs.nii.gz", self.basename + "_dns_dgbs.json", cleanup=True)
            self.degibbs_bval = self.basename + "_dns_dgbs.bval"
            self.degibbs_bvec = self.basename + "_dns_dgbs.bvec"
            self.meanb0 = self.basename + "_meanb0.nii.gz"
            self.meanb0_stripped = self.basename + "_meanb0_stripped.nii.gz"
            self.meanb0_mask = (self.basename + "_meanb0_stripped_bet.nii.gz").setStatic()
            self.N4biascorrected = self.basename + "_eddy_N4biascorrected.nii.gz"
            self.fullyPreprocessedmif = self.basename + "_fullyPreprocessed.mif"
            self.trace1000 = self.basename + "_trace1000.mif"
            self.subsetForDTI = self.basename + "_subsetForDTI.nii.gz"
            self.subsetForDIT_bval = self.basename + "_subsetForDTI.bval"
            self.subsetForDIT_bvec = self.basename + "_subsetForDTI.bvec"

            self.toT1w_prefix = self.basename + "_toT1w"
            self.toT1w_toT1w = (self.toT1w_prefix + "Warped.nii.gz").setStatic().setCleanup()
            self.toT1w_0GenericAffine = (self.toT1w_prefix + "0GenericAffine.mat").setStatic()
            self.toT1w_InverseWarped = (self.toT1w_prefix + "InverseWarped.nii.gz").setStatic()
            self.cat12_fromT1_whiteMatterProbability = (self.basename + "cat12_fromT1_whiteMatterProbability.nii.gz")
            self.synthsegWMCorticalProbability_fromT1w = (self.basename + "synthsegWMCortical_fromT1w.nii.gz")
            self.synthsegWMCortical_mask_fromT1w = (self.basename + "synthsegWMCortical_mask0p5_fromT1w.nii.gz")
            self.fromFlair_WMHMask = self.basename + "_fromFlair_WMHMask.nii.gz"
            self.synthsegNAWMCortical_mask = self.basename + "_synthsegNAWMCortical_mask.nii.gz"

            #topup
            self.synB0_script = self.basename + "_synB0Wrapper.sh"
            self.b0ForTopup = self.basename + "_b0ForTopup.nii.gz"
            self.b0MergeForTopup = self.basename + "_b0MergeForTopup.nii.gz"
            self.topup_outdir = self.basedir.join("topup")
            self.topup_out_basename = self.topup_outdir.join("topup_")
            self.topup_b0_hifi = Path(self.topup_out_basename + "b0_hifi.nii.gz")
            self.topup_fieldcoef = Path(self.topup_out_basename + "_fieldcoef.nii.gz", static=True)
            self.topup_movepar = Path(self.topup_out_basename + "_movpar.txt", static=True)
            self.topup_b0_hifi_mean = self.topup_out_basename + "b0_hifi_mean.nii.gz"
            self.topup_b0_hifi_mean_stripped = self.topup_out_basename + "b0_hifi_mean_stripped.nii.gz"
            self.topup_b0_hifi_mean_mask = (self.topup_out_basename + "b0_hifi_mean_stripped_bet.nii.gz").setStatic()

            #eddy
            self.eddy_outdir = self.basedir.join("eddy")
            self.eddy_out_basename = self.eddy_outdir.join("eddy")
            self.eddy_eddy_cnr_maps = (self.eddy_out_basename + ".eddy_cnr_maps.nii.gz").setStatic()
            self.eddy_eddy_command_txt = (self.eddy_out_basename + ".eddy_command_txt").setStatic()
            self.eddy_eddy_movement_over_time = (self.eddy_out_basename + ".eddy_movement_over_time").setStatic()
            self.eddy_eddy_movement_rms = (self.eddy_out_basename + ".eddy_movement_rms").setStatic()
            self.eddy_eddy_outlier_free_data = (self.eddy_out_basename + ".eddy_outlier_free_data.nii.gz").setStatic()
            self.eddy_eddy_outlier_map = (self.eddy_out_basename + ".eddy_outlier_map").setStatic()
            self.eddy_eddy_outlier_n_sqr_stdev_map = (self.eddy_out_basename + ".eddy_outlier_n_sqr_stdev_map").setStatic()
            self.eddy_eddy_outlier_n_stdev_map = (self.eddy_out_basename + ".eddy_outlier_n_stdev_map").setStatic()
            self.eddy_eddy_outlier_report = (self.eddy_out_basename + ".eddy_outlier_report").setStatic()
            self.eddy_eddy_parameters = (self.eddy_out_basename + ".eddy_parameters").setStatic()
            self.eddy_eddy_post_eddy_shell_alignment_parameters = (self.eddy_out_basename + ".eddy_post_eddy_shell_alignment_parameters").setStatic()
            self.eddy_eddy_post_eddy_shell_PE_translation_parameters = (self.eddy_out_basename + ".eddy_post_eddy_shell_PE_translation_parameters").setStatic()
            self.eddy_eddy_range_cnr_maps = (self.eddy_out_basename + ".eddy_range_cnr_maps.nii.gz").setStatic()
            self.eddy_eddy_residuals = (self.eddy_out_basename + ".eddy_residuals.nii.gz").setStatic()
            self.eddy_eddy_restricted_movement_rms = (self.eddy_out_basename + ".eddy_restricted_movement_rms").setStatic()
            self.eddy_eddy_rotated_bvecs = (self.eddy_out_basename + ".eddy_rotated_bvecs").setStatic()
            self.eddy_eddy_shell_indicies = (self.eddy_out_basename + ".eddy_shell_indicies.json").setStatic()
            self.eddy_eddy_values_of_all_input_parameters = (self.eddy_out_basename + ".eddy_values_of_all_input_parameters").setStatic()
            self.eddy_json = (self.eddy_out_basename + ".eddy.json").setStatic()
            self.eddy_imageCorrected = (self.eddy_out_basename + ".nii.gz").setStatic()

            self.eddy_outFileList = [self.eddy_eddy_cnr_maps,
                                     self.eddy_eddy_command_txt,
                                     self.eddy_eddy_movement_over_time,
                                     self.eddy_eddy_movement_rms,
                                     self.eddy_eddy_outlier_free_data,
                                     self.eddy_eddy_outlier_map,
                                     self.eddy_eddy_outlier_n_sqr_stdev_map,
                                     self.eddy_eddy_outlier_n_stdev_map,
                                     self.eddy_eddy_outlier_report,
                                     self.eddy_eddy_parameters,
                                     self.eddy_eddy_post_eddy_shell_alignment_parameters,
                                     self.eddy_eddy_post_eddy_shell_PE_translation_parameters,
                                     self.eddy_eddy_range_cnr_maps,
                                     self.eddy_eddy_residuals,
                                     self.eddy_eddy_restricted_movement_rms,
                                     self.eddy_eddy_rotated_bvecs,
                                     self.eddy_eddy_shell_indicies,
                                     self.eddy_eddy_values_of_all_input_parameters,
                                     self.eddy_json,
                                     self.eddy_imageCorrected]

            #DTIFIT
            self.dtifit_basename = self.basename + "_dtifit"
            self.dtifit_V1 = self.dtifit_basename + "_V1.nii.gz"
            self.dtifit_V2 = self.dtifit_basename + "_V2.nii.gz"
            self.dtifit_V3 = self.dtifit_basename + "_V3.nii.gz"
            self.dtifit_L1 = self.dtifit_basename + "_L1.nii.gz"
            self.dtifit_L2 = self.dtifit_basename + "_L2.nii.gz"
            self.dtifit_L3 = self.dtifit_basename + "_L3.nii.gz"
            self.dtifit_MD = self.dtifit_basename + "_MD.nii.gz"
            self.dtifit_FA = self.dtifit_basename + "_FA.nii.gz"
            self.dtifit_MO = self.dtifit_basename + "_MO.nii.gz"
            self.dtifit_S0 = self.dtifit_basename + "_S0.nii.gz"
            self.dtifit_outFileList = [
                self.dtifit_V1,
                self.dtifit_V2,
                self.dtifit_V3,
                self.dtifit_L1,
                self.dtifit_L2,
                self.dtifit_L3,
                self.dtifit_MD,
                self.dtifit_FA,
                self.dtifit_MO,
                self.dtifit_S0
            ]
            self.dtifit_RD = self.dtifit_basename + "_RD.nii.gz" #needs to be calculated


            #advanced msmt model:
            self.responseVoxels = self.basename + "_msmt_responseVoxels.nii.gz"
            self.responseSFWM = self.basename + "_msmt_responseSFWM.txt"
            self.responseGM = self.basename + "_msmt_responseGM.txt"
            self.responseCSF = self.basename + "_msmt_responseCSF.txt"
            self.responseWM_FOD = self.basename + "_msmt_responseWM_FOD.mif"
            self.responseGM_FOD = self.basename + "_msmt_responseGM_FOD.mif"
            self.responseCSF_FOD = self.basename + "_msmt_responseCSF_FOD.mif"
            self.responseWM_FOD_norm = self.basename + "_msmt_responseWM_FOD_norm.mif"
            self.responseGM_FOD_norm = self.basename + "_msmt_responseGM_FOD_norm.mif"
            self.responseCSF_FOD_norm = self.basename + "_msmt_responseCSF_FOD_norm.mif"
            self.msmt_5tt = self.basename + "_msmt_5tt.mif"
            self.msmt_wmfod_peaks = self.basename + "_msmt_responseWM_FOD_norm_peaks.nii.gz"
            self.msmt_wmfod_peaks2std = self.basename + "_msmt_responseWM_FOD_norm_peaks2std.nii.gz"
            self.topup_b0_hifi_mean_mask2std = self.basename + "_topup_b0_hifi_mean_stripped_bet2std.nii.gz"
            self.tractseg_dir = self.basedir.join("tractseg")

            self.atlas_Schaefer2018_200Parcels_7Networks_order_FSLMNI152 = self.basename + "_fromT1w_Schaefer2018_200Parcels_7Networks_order_FSLMNI152.nii.gz"
            self.atlas_Schaefer2018_100Parcels_7Networks_order_FSLMNI152 = self.basename + "_fromT1w_Schaefer2018_100Parcels_7Networks_order_FSLMNI152.nii.gz"
            self.atlas_synthsegPosterior = self.basename + "_fromT1w_synthsegPosterior.nii.gz"
            self.atlas_Schaefer2018_200Parcels_17Networks_order_FSLMNI152 = self.basename + "_fromT1w_Schaefer2018_200Parcels_17Networks_order_FSLMNI152.nii.gz"
            self.atlas_JHU_1mm = self.basename + "_fromT1w_JHU_1mm.nii.gz"
            self.atlas_HammersmithLobar = self.basename + "_fromT1w_HammersmithLobar.nii.gz"
            self.atlas_JHU_1mm_WMMasked0p5 = self.basename + "_fromT1w_JHU_1mm_WMMasked.nii.gz"
            self.atlas_HammersmithLobar_WMMasked0p5 = self.basename + "_fromT1w_HammersmithLobar_wmMasked.nii.gz"


            self.iso1p5mm = self.Iso1p5mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses,
                                          nameFormatter=nameFormatter,
                                          basename=basename)
            self.iso2mm = self.Iso2mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)
            self.iso3mm = self.Iso3mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)

        class Iso1p5mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                super().__init__(name="dwi_bidsProcessed_iso1p5mm")
                basename = basename + "_iso1p5mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler, "resample_iso1p5mm"), isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))

        class Iso2mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                super().__init__(name="dwi_bidsProcessed_iso2mm")
                basename = basename + "_iso2mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler, "resample_iso2mm"), isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))

        class Iso3mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                super().__init__(name="dwi_bidsProcessed_iso3mm")
                basename = basename + "_iso3mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler, "resample_iso3mm"), isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))

    class Meta_QC(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="dwi_metaQC")
            self.basedir = Path(os.path.join(basepaths.qcPath, filler), isDirectory=True, create=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename), isDirectory=False)
            self.ToT1w_native_slices = self.basename + "_ToT1w_native.png"
            self.shellVisMp4 = self.basename + "_shellVis.mp4"
            self.firstb0 = self.basename + "_firstb0.png"
            self.topup_bmask = self.basename + "_topup_hdbet_mask.png"
            self.meanb0_bmask = self.basename + "_meanb0_hdbet_mask.png"
            self.eddy_qc_Dir = self.basedir.join("eddy", isDirectory=True, shouldExist=False).setNeverCreate()
            self.eddy_qc_pdf = self.eddy_qc_Dir.join("qc.pdf")
            self.eddy_qc_json = self.eddy_qc_Dir.join("qc.json")
            self.ToT1w_native_slices = self.basename + "_ToT1w_native.png"


    class Bids_statistics(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="dwi_bidsStatistic")
            self.basedir = Path(os.path.join(basepaths.bidsStatisticsPath, filler), isDirectory=True, create=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
            self.topupCorrectionMethod = StatsFilePath(path=self.basename + "ProcessingSettings.json", attributeName="topupCorrectionMethod", subject=sub, session=ses)
            self.SliceTimeCorrection = StatsFilePath(path=self.basename + "ProcessingSettings.json", attributeName="SliceTimeCorrection", subject=sub, session=ses)
            self.nDirectionsB1000 = StatsFilePath(path=self.basename + "ProcessingSettings.json", attributeName="nDirectionsB1000", subject=sub, session=ses)
            self.shellDescription = StatsFilePath(path=self.basename + "ProcessingSettings.json", attributeName="shellDescription", subject=sub, session=ses)
            self.MRIVendor = StatsFilePath(path=self.basename + "ProcessingSettings.json", attributeName="MRIVendor", subject=sub, session=ses)
            self.MRIModel = StatsFilePath(path=self.basename + "ProcessingSettings.json", attributeName="MRIModel", subject=sub, session=ses)

            self.connectome_basename = self.basename + "_SC_"

            self.dtifit_MD_mean_atlas_HammersmithLobar_WMMasked0p5 = self.basename + "dtiResults_MD_mean_HammersmithLobar_maskedWM0p5.csv"
            self.dtifit_FA_mean_atlas_HammersmithLobar_WMMasked0p5 = self.basename + "dtiResults_FA_mean_HammersmithLobar_maskedWM0p5.csv"
            self.dtifit_RD_mean_atlas_HammersmithLobar_WMMasked0p5 = self.basename + "dtiResults_RD_mean_HammersmithLobar_maskedWM0p5.csv"
            self.dtifit_AD_mean_atlas_HammersmithLobar_WMMasked0p5 = self.basename + "dtiResults_AD_mean_HammersmithLobar_maskedWM0p5.csv"

            self.dtifit_MD_mean_atlas_JHU_1mm_WMMasked0p5 = self.basename + "dtiResults_MD_mean_JHU_1mm_WMMasked.csv"
            self.dtifit_FA_mean_atlas_JHU_1mm_WMMasked0p5 = self.basename + "dtiResults_FA_mean_JHU_1mm_WMMasked.csv"
            self.dtifit_RD_mean_atlas_JHU_1mm_WMMasked0p5 = self.basename + "dtiResults_RD_mean_JHU_1mm_WMMasked.csv"
            self.dtifit_AD_mean_atlas_JHU_1mm_WMMasked0p5 = self.basename + "dtiResults_AD_mean_JHU_1mm_WMMasked.csv"

            self.dtifit_MD_mean_WMCortical0p5 = StatsFilePath(path=self.basename + "DTIStats.json", attributeName="DTI_MD_WMCortical_masked0p5_mean", subject=sub, session=ses)
            self.dtifit_FA_mean_WMCortical0p5 = StatsFilePath(path=self.basename + "DTIStats.json", attributeName="DTI_FA_WMCortical_masked0p5_mean", subject=sub, session=ses)
            self.dtifit_RD_mean_WMCortical0p5 = StatsFilePath(path=self.basename + "DTIStats.json", attributeName="DTI_RD_WMCortical_masked0p5_mean", subject=sub, session=ses)
            self.dtifit_AD_mean_WMCortical0p5 = StatsFilePath(path=self.basename + "DTIStats.json", attributeName="DTI_AD_WMCortical_masked0p5_mean", subject=sub, session=ses)

            self.dtifit_MD_mean_NAWMCortical0p5 = StatsFilePath(path=self.basename + "DTIStats.json", attributeName="DTI_MD_NAWMCortical_masked0p5_mean", subject=sub, session=ses)
            self.dtifit_FA_mean_NAWMCortical0p5 = StatsFilePath(path=self.basename + "DTIStats.json", attributeName="DTI_FA_NAWMCortical_masked0p5_mean", subject=sub, session=ses)
            self.dtifit_RD_mean_NAWMCortical0p5 = StatsFilePath(path=self.basename + "DTIStats.json", attributeName="DTI_RD_NAWMCortical_masked0p5_mean", subject=sub, session=ses)
            self.dtifit_AD_mean_NAWMCortical0p5 = StatsFilePath(path=self.basename + "DTIStats.json", attributeName="DTI_AD_NAWMCortical_masked0p5_mean", subject=sub, session=ses)

            self.dtifit_MD_mean_WMH = StatsFilePath(path=self.basename + "DTIStats.json", attributeName="DTI_MD_WMH_mean", subject=sub, session=ses)
            self.dtifit_FA_mean_WMH = StatsFilePath(path=self.basename + "DTIStats.json", attributeName="DTI_FA_WMH_mean", subject=sub, session=ses)
            self.dtifit_RD_mean_WMH = StatsFilePath(path=self.basename + "DTIStats.json", attributeName="DTI_RD_WMH_mean", subject=sub, session=ses)
            self.dtifit_AD_mean_WMH = StatsFilePath(path=self.basename + "DTIStats.json", attributeName="DTI_AD_WMH_mean", subject=sub, session=ses)



    def __init__(self, sub, ses, basepaths, basedir="DWI", nameFormatter="{subj}_{ses}_{basename}",
                 modalityBeforeSession=False, basename="DWI", *args, **kwargs):
        super().__init__(name="DWI", *args, **kwargs)
        if modalityBeforeSession:
            fillerBids = os.path.join(sub, basedir, ses)
            filler = os.path.join(sub, basename, ses)
        else:
            fillerBids = os.path.join(sub, ses, basedir)
            filler = os.path.join(sub, ses, basename)

        self.subjectName = sub
        self.sessionName = ses
        self.bids = self.Bids(fillerBids, basepaths, sub, ses, nameFormatter, basename, inputArgs=self.inputArgs)
        self.bids_processed = self.Bids_processed(filler, basepaths, sub, ses, nameFormatter, basename)
        self.bids_statistics = self.Bids_statistics(filler, basepaths, sub, ses, nameFormatter, basename)
        self.meta_QC = self.Meta_QC(filler, basepaths, sub, ses, nameFormatter, basename)


    def verify(self):
        if not self.bids.dwi.validate():
            logger.warning(
                f"Subject without valid DWI specifications found, excluding subject {self.subjectName} ({self.sessionName})")
            return None
        return self


