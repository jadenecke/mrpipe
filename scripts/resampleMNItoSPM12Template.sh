#!/bin/bash

# Input files
inDir="../data/standard"
outDir="../data/standard/cat12_resampled"
cat12TemplateFile="../mrpipe/Toolboxes/submodules/cat12/templates_MNI152NLin2009cAsym/Template_0_GS.nii"


if [ ! -f "$cat12TemplateFile" ]; then
    echo "ERROR: Template file not found at $cat12TemplateFile"
    exit 1
fi

if ! command -v flirt &> /dev/null; then
    echo "ERROR: FSL flirt command not found in PATH. Please load FSL."
    exit 1
fi

# Create output directory
mkdir -p "$outDir" || { echo "ERROR: Could not create output directory $outDir"; exit 1; }

echo "Resampling ${#MNIFiles[@]} MNI files to match template FOV..."
echo "Template: $cat12TemplateFile"
echo "Output directory: $outDir"
echo 

# --- Main loop ---
# Use flirt to resample to template dimensions (FOV), preserving voxel size
flirt -in ${inDir}/MNI152_T1_0.5mm.nii.gz -ref "$cat12TemplateFile" -out ${outDir}/MNI152_T1_0.5mm_resampled.nii.gz -usesqform -applyisoxfm 0.5 -noresample
flirt -in ${inDir}/MNI152_T1_1mm_brain_mask.nii.gz -ref "$cat12TemplateFile" -out ${outDir}/MNI152_T1_1mm_brain_mask_resampled.nii.gz -usesqform -applyisoxfm 1 -noresample
flirt -in ${inDir}/MNI152_T1_1mm_brain.nii.gz -ref "$cat12TemplateFile" -out ${outDir}/MNI152_T1_1mm_brain_resampled.nii.gz -usesqform -applyisoxfm 1 -noresample
flirt -in ${inDir}/MNI152_T1_1mm.nii.gz -ref "$cat12TemplateFile" -out ${outDir}/MNI152_T1_1mm_resampled.nii.gz -usesqform -applyisoxfm 1 -noresample
flirt -in ${inDir}/MNI152_T1_1p5mm_brain_mask.nii.gz -ref "$cat12TemplateFile" -out ${outDir}/MNI152_T1_1p5mm_brain_mask_resampled.nii.gz -usesqform -applyisoxfm 1.5 -noresample
flirt -in ${inDir}/MNI152_T1_1p5mm_brain.nii.gz -ref "$cat12TemplateFile" -out ${outDir}/MNI152_T1_1p5mm_brain_resampled.nii.gz -usesqform -applyisoxfm 1.5 -noresample
flirt -in ${inDir}/MNI152_T1_1p5mm.nii.gz -ref "$cat12TemplateFile" -out ${outDir}/MNI152_T1_1p5mm_resampled.nii.gz -usesqform -applyisoxfm 1.5 -noresample
flirt -in ${inDir}/MNI152_T1_2mm_brain_mask.nii.gz -ref "$cat12TemplateFile" -out ${outDir}/MNI152_T1_2mm_brain_mask_resampled.nii.gz -usesqform -applyisoxfm 2 -noresample
flirt -in ${inDir}/MNI152_T1_2mm_brain.nii.gz -ref "$cat12TemplateFile" -out ${outDir}/MNI152_T1_2mm_brain_resampled.nii.gz -usesqform -applyisoxfm 2 -noresample
flirt -in ${inDir}/MNI152_T1_2mm.nii.gz -ref "$cat12TemplateFile" -out ${outDir}/MNI152_T1_2mm_resampled.nii.gz -usesqform -applyisoxfm 2 -noresample
flirt -in ${inDir}/MNI152_T1_3mm_brain_mask.nii.gz -ref "$cat12TemplateFile" -out ${outDir}/MNI152_T1_3mm_brain_mask_resampled.nii.gz -usesqform -applyisoxfm 3 -noresample
flirt -in ${inDir}/MNI152_T1_3mm_brain.nii.gz -ref "$cat12TemplateFile" -out ${outDir}/MNI152_T1_3mm_brain_resampled.nii.gz -usesqform -applyisoxfm 3 -noresample
flirt -in ${inDir}/MNI152_T1_3mm.nii.gz -ref "$cat12TemplateFile" -out ${outDir}/MNI152_T1_3mm_resampled.nii.gz -usesqform -applyisoxfm 3 -noresample

echo 
echo "All done!"
