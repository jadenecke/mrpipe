import argparse
import nibabel as nib
import numpy as np

def extract_rois(atlas_path, roi_numbers, output_path, binarize):
    # Load the atlas
    atlas_img = nib.load(atlas_path)
    atlas_data = atlas_img.get_fdata()

    

    # Binarize if requested
    if binarize:
        selected_rois = np.isin(atlas_data, roi_numbers).astype(np.uint8)
    else:
    	# Extract specified ROIs
    	selected_rois = np.isin(atlas_data, roi_numbers) * atlas_data

    # Save the result as a new NIfTI file
    new_img = nib.Nifti1Image(selected_rois, atlas_img.affine, atlas_img.header)
    nib.save(new_img, output_path)
    print(f"Processed image saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract selected ROIs from a NIfTI atlas.")
    parser.add_argument('--atlas_path', '-a', type=str, help="Path to the NIfTI atlas file")
    parser.add_argument("--roi_numbers", '-r', type=int, nargs="+", help="List of ROI numbers to extract")
    parser.add_argument("--output_path", "-o", type=str, help="Path to save the processed NIfTI file")
    parser.add_argument("--binarize", '-b', action="store_true", help="Convert output to binary mask")

    args = parser.parse_args()
    extract_rois(args.atlas_path, args.roi_numbers, args.output_path, args.binarize)
