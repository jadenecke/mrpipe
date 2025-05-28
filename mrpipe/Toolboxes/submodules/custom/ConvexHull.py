import os
import numpy as np
import nibabel as nib
from skimage.morphology import convex_hull_image
import argparse


def load_nifti(file_path):
    """Load a NIFTI file and return its data and affine transform."""
    img = nib.load(file_path)
    return img.get_fdata(), img.affine, img.header


def create_convex_hull_mask(binary_mask):
    """
    Create a convex hull mask from a binary mask using scikit-image.
    
    Parameters:
    -----------
    binary_mask : numpy.ndarray
        Input binary mask
        
    Returns:
    --------
    numpy.ndarray
        Binary mask of the convex hull
    """
    # Convert to boolean array if not already
    mask_bool = binary_mask.astype(bool)
    
    # If the mask is empty or has less than 4 points, return the original
    if np.sum(mask_bool) < 4:
        return binary_mask
    
    # Calculate convex hull
    hull_mask = convex_hull_image(mask_bool)
    
    # Convert back to same data type as input
    return hull_mask.astype(binary_mask.dtype)


def main():
    parser = argparse.ArgumentParser(description='Calculate convex hull from binary NIFTI mask')
    parser.add_argument('--input', '-i', required=True,
                        help='Path to the input binary mask NIFTI file')
    parser.add_argument('--output', '-o', required=True,
                        help='Path to save the convex hull mask')

    args = parser.parse_args()

    # Load input mask
    data, affine, header = load_nifti(args.input)

    # Calculate convex hull
    hull_mask = create_convex_hull_mask(data > 0)

    # Save result
    output_img = nib.Nifti1Image(hull_mask, affine, header)
    nib.save(output_img, args.output)

    print(f"Convex hull mask saved to {args.output}")


if __name__ == "__main__":
    main()