import os
import numpy as np
import nibabel as nib
from skimage.measure import label
import argparse


def load_nifti(file_path):
    """Load a NIFTI file and return its data and affine transform."""
    img = nib.load(file_path)
    return img.get_fdata(), img.affine, img.header


def filter_overlapping_components(input_mask_file, reference_mask_file, output_file=None, inclusive=False, threshold=0.0):
    """
    Filter out connected components from input mask that overlap with reference mask.

    Parameters:
    -----------
    input_mask_file : str
        Path to the input mask NIFTI file containing connected components to filter
    reference_mask_file : str
        Path to the reference mask NIFTI file - components that overlap with this will be removed
    output_file : str, optional
        Path to save the filtered mask, if None, will use input_mask_file stem + '_filtered.nii.gz'
    inclusive : bool, optional
        If True, keep components that overlap. If False (default), remove components that overlap.
    threshold : float, optional
        Overlap threshold (0.0 to 1.0). Component is considered overlapping if 
        (overlap voxels / component voxels) > threshold. Default is 0.0 (any overlap).

    Returns:
    --------
    tuple
        (filtered_mask, num_original, num_removed, num_remaining)
    """
    # Load masks
    input_data, input_affine, input_header = load_nifti(input_mask_file)
    reference_data, _, _ = load_nifti(reference_mask_file)

    # Check if shapes match
    if input_data.shape != reference_data.shape:
        raise ValueError(f"Shape mismatch: input {input_data.shape} vs reference {reference_data.shape}")

    # Convert to binary masks
    input_binary = input_data > 0
    reference_binary = reference_data > 0

    # Label connected components in the input mask
    labeled_components, num_components = label(input_binary, return_num=True)

    print(f"Found {num_components} connected components in the input mask")

    # Initialize filtered mask
    filtered_mask = np.zeros_like(input_data)

    # Track components
    removed_components = []
    kept_components = []

    # Process each component
    for component_idx in range(1, num_components + 1):
        # Extract this component
        component_mask = labeled_components == component_idx
        
        # Calculate overlap ratio
        overlap_voxels = np.sum(component_mask & reference_binary)
        total_voxels = np.sum(component_mask)
        overlap_ratio = overlap_voxels / total_voxels

        if inclusive:
            # Check if this component overlaps with the reference mask more than threshold
            if overlap_ratio > threshold:
                # Significant overlap, so we will keep this component
                filtered_mask[component_mask] = 1
                kept_components.append(component_idx)
            else:
                # Insufficient overlap, remove this component
                removed_components.append(component_idx)
        else:
            # Check if this component overlaps with the reference mask more than threshold
            if overlap_ratio > threshold:
                # Significant overlap, so we will remove this component
                removed_components.append(component_idx)
            else:
                # Insufficient overlap, keep this component
                filtered_mask[component_mask] = 1
                kept_components.append(component_idx)


    # Determine output filename if not provided
    if output_file is None:
        input_stem = os.path.splitext(os.path.basename(input_mask_file))[0]
        # Remove .nii if present in the stem (for cases like file.nii.gz)
        if input_stem.endswith('.nii'):
            input_stem = input_stem[:-4]
        output_file = f"{input_stem}_filtered.nii.gz"

    # Create and save the filtered NIFTI image
    filtered_img = nib.Nifti1Image(filtered_mask, input_affine, input_header)
    nib.save(filtered_img, output_file)

    print(f"Removed {len(removed_components)} components")
    print(f"Kept {len(kept_components)} components")
    print(f"Filtered mask saved to {output_file}")

    return filtered_mask, num_components, len(removed_components), len(kept_components)


def main():
    parser = argparse.ArgumentParser(description='Filter connected components in a mask that overlap with a reference mask')
    parser.add_argument('--input', '-i', required=True,
                        help='Path to the input mask NIFTI file containing connected components to filter')
    parser.add_argument('--reference', '-r', required=True,
                        help='Path to the reference mask NIFTI file - components that overlap with this will be removed')
    parser.add_argument('--inclusive', required=False, action='store_true',
                        help='Default is exclusive, i.e. remove everything that touches the reference mask. This will switch to inclusive, i.e. only keep CCs that overlap with the reference mask.')
    parser.add_argument('--output', '-o', default=None,
                        help='Path to save the filtered mask (default: input_stem_filtered.nii.gz)')
    parser.add_argument('--restrictive', required=False, action='store_true',
                        help='If set, the overlap threshold is set to 0.5 (i.e. >50%% overlap required) instead of any overlap.')

    args = parser.parse_args()

    threshold = 0.5 if args.restrictive else 0.0
    filter_overlapping_components(args.input, args.reference, args.output, args.inclusive, threshold)


if __name__ == "__main__":
    main()
