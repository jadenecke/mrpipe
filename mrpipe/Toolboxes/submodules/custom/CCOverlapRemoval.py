import os
import numpy as np
import nibabel as nib
from skimage.measure import label
import argparse


def load_nifti(file_path):
    """Load a NIFTI file and return its data and affine transform."""
    img = nib.load(file_path)
    return img.get_fdata(), img.affine, img.header


def filter_overlapping_components(input_mask_file, reference_mask_file, output_file=None, inclusive=False):
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

        if inclusive:
            # Check if this component overlaps with the reference mask
            if np.any(component_mask & reference_binary):
                # There is overlap, so we will remove this component
                removed_components.append(component_idx)
            else:
                # No overlap, keep this component
                filtered_mask[component_mask] = 1
                kept_components.append(component_idx)
        else:
            # Check if this component DOES NOT overlap with the reference mask
            if np.any(component_mask & reference_binary):
                # There is overlap, so we will keep this component
                filtered_mask[component_mask] = 1
                kept_components.append(component_idx)
            else:
                # No overlap, remove this component
                removed_components.append(component_idx)

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

    print(f"Removed {len(removed_components)} components that overlapped with reference mask")
    print(f"Kept {len(kept_components)} components with no overlap")
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

    args = parser.parse_args()

    filter_overlapping_components(args.input, args.reference, args.output, args.inclusive)


if __name__ == "__main__":
    main()
