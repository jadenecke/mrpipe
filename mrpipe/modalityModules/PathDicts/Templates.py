import os
from mrpipe.meta.PathClass import Path
from mrpipe.meta.PathCollection import PathCollection
import mrpipe

class Templates(PathCollection):
    def __init__(self):
        self.standard = Path(
            os.path.join(os.path.abspath(os.path.dirname(mrpipe.__file__)), os.pardir, "data", "standard"),
            isDirectory=True, shouldExist=True)
        self.standard = Path(
            os.path.join(os.path.abspath(os.path.dirname(mrpipe.__file__)), os.pardir, "data", "atlases"),
            isDirectory=True, shouldExist=True)
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
        self.mni152_3mm = self.standard.join("MNI152_T1_2mm.nii.gz", shouldExist=True)
        self.mni152_brain_3mm = self.standard.join("MNI152_T1_2mm_brain.nii.gz", shouldExist=True)
        self.mni152_brain_mask_3mm = self.standard.join("MNI152_T1_2mm_brain_mask.nii.gz", shouldExist=True)
