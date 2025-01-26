import os
from mrpipe.meta.PathClass import Path
from mrpipe.meta.PathCollection import PathCollection
from mrpipe.Helper import Helper
import mrpipe

class Templates(PathCollection):
    def __init__(self):
        self.standard = Path(os.path.join(Helper.get_libpath(), os.pardir, "data", "standard"),
            isDirectory=True, shouldExist=True)
        self.atlases = Path(os.path.join(Helper.get_libpath(), os.pardir, "data", "atlases"),
            isDirectory=True, shouldExist=True)
        self.masks = Path(os.path.join(Helper.get_libpath(), os.pardir, "data", "masks"),
                            isDirectory=True, shouldExist=True)

        # TODO: easy win: Introduce three subclases, i.e. standards / atlasses / masks

        # MNI
        self.mni152_1mm = self.standard.join("MNI152_T1_1mm.nii.gz", shouldExist=True)
        self.mni152_brain_1mm = self.standard.join("MNI152_T1_1mm_brain.nii.gz", shouldExist=True)
        self.mni152_brain_mask_1mm = self.standard.join("MNI152_T1_1mm_brain_mask.nii.gz", shouldExist=True)
        self.mni152_2mm = self.standard.join("MNI152_T1_2mm.nii.gz", shouldExist=True)
        self.mni152_brain_2mm = self.standard.join("MNI152_T1_2mm_brain.nii.gz", shouldExist=True)
        self.mni152_brain_mask_2mm = self.standard.join("MNI152_T1_2mm_brain_mask.nii.gz", shouldExist=True)
        self.mni152_0p5mm = self.standard.join("MNI152_T1_0.5mm.nii.gz", shouldExist=True)
        self.mni152_1p5mm = self.standard.join("MNI152_T1_1p5mm.nii.gz", shouldExist=True)
        self.mni152_brain_1p5mm = self.standard.join("MNI152_T1_1p5mm_brain.nii.gz", shouldExist=True)
        self.mni152_brain_mask_1p5mm = self.standard.join("MNI152_T1_1p5mm_brain_mask.nii.gz", shouldExist=True)
        self.mni152_3mm = self.standard.join("MNI152_T1_3mm.nii.gz", shouldExist=True)
        self.mni152_brain_3mm = self.standard.join("MNI152_T1_3mm_brain.nii.gz", shouldExist=True)
        self.mni152_brain_mask_3mm = self.standard.join("MNI152_T1_3mm_brain_mask.nii.gz", shouldExist=True)

        # Schaefer Atlas 2018
        self.schaefer2018Dir = self.atlases.join("schaefer2018", isDirectory=True, shouldExist=True)
        self.Schaefer2018_200Parcels_7Networks_order_FSLMNI152_1mm = self.schaefer2018Dir.join("Schaefer2018_200Parcels_7Networks_order_FSLMNI152_1mm.nii.gz", shouldExist=True)
        self.Schaefer2018_200Parcels_7Networks_order_FSLMNI152_1p5mm_CAT12 = self.schaefer2018Dir.join("Schaefer2018_200Parcels_7Networks_order_FSLMNI152_1p5mm_CAT12.nii.gz", shouldExist=True)
        self.Schaefer2018_200Parcels_7Networks_order_FSLMNI152_2mm = self.schaefer2018Dir.join("Schaefer2018_200Parcels_7Networks_order_FSLMNI152_2mm.nii.gz", shouldExist=True)
        self.Schaefer2018_200Parcels_7Networks_order = self.schaefer2018Dir.join("Schaefer2018_200Parcels_7Networks_order.lut", shouldExist=True)
        self.Schaefer2018_200Parcels_17Networks_order_FSLMNI152_1mm = self.schaefer2018Dir.join("Schaefer2018_200Parcels_17Networks_order_FSLMNI152_1mm.nii.gz", shouldExist=True)
        self.Schaefer2018_200Parcels_17Networks_order_FSLMNI152_1p5mm = self.schaefer2018Dir.join("Schaefer2018_200Parcels_17Networks_order_FSLMNI152_1p5mm.nii.gz", shouldExist=True)
        self.Schaefer2018_200Parcels_17Networks_order_FSLMNI152_2mm = self.schaefer2018Dir.join("Schaefer2018_200Parcels_17Networks_order_FSLMNI152_2mm.nii.gz", shouldExist=True)
        self.Schaefer2018_200Parcels_17Networks_order = self.schaefer2018Dir.join("Schaefer2018_200Parcels_17Networks_order.lut", shouldExist=True)
        self.Schaefer2018_400Parcels_7Networks_order_FSLMNI152_1mm = self.schaefer2018Dir.join("Schaefer2018_400Parcels_7Networks_order_FSLMNI152_1mm.nii.gz", shouldExist=True)
        self.Schaefer2018_400Parcels_7Networks_order_FSLMNI152_1p5mm_CAT12 = self.schaefer2018Dir.join("Schaefer2018_400Parcels_7Networks_order_FSLMNI152_1p5mm_CAT12.nii.gz", shouldExist=True)
        self.Schaefer2018_400Parcels_7Networks_order_FSLMNI152_2mm = self.schaefer2018Dir.join("Schaefer2018_400Parcels_7Networks_order_FSLMNI152_2mm.nii.gz", shouldExist=True)
        self.Schaefer2018_400Parcels_7Networks_order = self.schaefer2018Dir.join("Schaefer2018_400Parcels_7Networks_order.lut", shouldExist=True)
        self.Schaefer2018_400Parcels_17Networks_order_FSLMNI152_1mm = self.schaefer2018Dir.join("Schaefer2018_400Parcels_17Networks_order_FSLMNI152_1mm.nii.gz", shouldExist=True)
        self.Schaefer2018_400Parcels_17Networks_order_FSLMNI152_1p5mm = self.schaefer2018Dir.join("Schaefer2018_400Parcels_17Networks_order_FSLMNI152_1p5mm.nii.gz", shouldExist=True)
        self.Schaefer2018_400Parcels_17Networks_order_FSLMNI152_2mm = self.schaefer2018Dir.join("Schaefer2018_400Parcels_17Networks_order_FSLMNI152_2mm.nii.gz", shouldExist=True)
        self.Schaefer2018_400Parcels_17Networks_order = self.schaefer2018Dir.join("Schaefer2018_400Parcels_17Networks_order.lut", shouldExist=True)

        # Mindboggle101 Atlas V2
        self.mindboggleDir = self.atlases.join("mindboggle101", isDirectory=True, shouldExist=True)
        self.Braak_stage_Mindboggle_ROIs_DK40 = self.mindboggleDir.join("Braak_stage_Mindboggle_ROIs_DK40.csv", shouldExist=True)
        self.labels_all = self.mindboggleDir.join("labels_all.csv", shouldExist=True)
        self.labels_combined = self.mindboggleDir.join("labels_combined.csv", shouldExist=True)
        self.OASIS_TRT_20_jointfusion_DKT31_CMA_labels_in_MNI152_1p5mm_v2 = self.mindboggleDir.join("OASIS-TRT-20_jointfusion_DKT31_CMA_labels_in_MNI152_1p5mm_v2.nii.gz", shouldExist=True)
        self.OASIS_TRT_20_jointfusion_DKT31_CMA_labels_in_MNI152_2mm_v2 = self.mindboggleDir.join("OASIS-TRT-20_jointfusion_DKT31_CMA_labels_in_MNI152_2mm_v2.nii.gz", shouldExist=True)
        self.OASIS_TRT_20_jointfusion_DKT31_CMA_labels_in_MNI152_v2 = self.mindboggleDir.join("OASIS-TRT-20_jointfusion_DKT31_CMA_labels_in_MNI152_v2.nii.gz", shouldExist=True)

        # JHU Atlases
        self.JHUDir = self.atlases.join("JHU_DTI", isDirectory=True, shouldExist=True)
        self.JHULabels = self.JHUDir.join("JHU-ICBM-labels-atlas.txt", shouldExist=True)
        self.JHU_1mm = self.JHUDir.join("JHU-ICBM-labels-1mm.nii.gz", shouldExist=True)
        self.JHU_2mm = self.JHUDir.join("JHU-ICBM-labels-2mm.nii.gz", shouldExist=True)


        # Hammersmith (lobar)
        # JHU Atlases
        self.HammersmithDir = self.atlases.join("LobarHammersmith", isDirectory=True, shouldExist=True)
        self.HammersmithLabels = self.HammersmithDir.join("hammers_mithLabels.csv", shouldExist=True)
        self.Hammersmith = self.HammersmithDir.join("Hammers_mith_atlas_n30r83_SPM5.nii.gz", shouldExist=True)
        self.HammersmithLobarLabels = self.HammersmithDir.join("hammers_mithLobarLabels.csv", shouldExist=True)
        self.HammersmithLobar = self.HammersmithDir.join("Hammers_mith_atlas_Lobar_SPM5.nii.gz", shouldExist=True)

        # PET Masks
        self.cerebellum_whole_eroded = self.masks.join("Cerebellum-MNIflirt_bin_eroded_whole.nii.gz", shouldExist=True)
        self.cerebellum_inferiorGM_eroded = self.masks.join("inferior_cerebellar_ROI_masked_eroded.nii.gz", shouldExist=True)
        self.Pons_whole_eroded = self.masks.join("Pons_MNI152_2mm_eroded.nii.gz", shouldExist=True)

        # CenTauR Scale masks
        self.centaurDir = self.atlases.join("CenTauRZ", isDirectory=True, shouldExist=True)
        self.centaur_CenTauR = self.centaurDir.join("CenTauR.nii.gz", shouldExist=True)
        self.centaur_Frontal_CenTauR = self.centaurDir.join("Frontal_CenTauR.nii.gz", shouldExist=True)
        self.centaur_Mesial_CenTauR = self.centaurDir.join("Mesial_CenTauR.nii.gz", shouldExist=True)
        self.centaur_Meta_CenTauR = self.centaurDir.join("Meta_CenTauR.nii.gz", shouldExist=True)
        self.centaur_TP_CenTauR = self.centaurDir.join("TP_CenTauR.nii.gz", shouldExist=True)


