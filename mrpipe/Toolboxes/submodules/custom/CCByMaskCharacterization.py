import os
import numpy as np
import nibabel as nib
from skimage.measure import label, regionprops
import pandas as pd
import argparse
from collections import defaultdict, Counter


def load_nifti(file_path):
    """Load a NIFTI file and return its data and affine transform."""
    img = nib.load(file_path)
    return img.get_fdata(), img.affine, img.header


def cc_overlap_analysis(cc_mask_file, reference_mask_files, output_csv=None, mask_names=None):
    """
    Analyze connected components in a mask and determine which reference mask each overlaps with most.

    Parameters:
    -----------
    cc_mask_file : str
        Path to the NIFTI file containing connected components to analyze
    reference_mask_files : list
        List of paths to reference mask NIFTI files
    output_csv : str, optional
        Path to save the CSV results, if None, will use cc_mask_file stem + '_overlap.csv'
    mask_names : list, optional
        List of names for each reference mask, if None, will use filenames

    Returns:
    --------
    pandas.DataFrame
        DataFrame containing the results
    """
    # Load CC mask
    cc_data, cc_affine, _ = load_nifti(cc_mask_file)

    # Create binary mask and label connected components
    cc_binary = cc_data > 0
    labeled_components, num_components = label(cc_binary, return_num=True)

    print(f"Found {num_components} connected components in the CC mask")

    # Load reference masks
    reference_masks = []
    if mask_names is None:
        mask_names = []

    for i, mask_file in enumerate(reference_mask_files):
        ref_data, ref_affine, _ = load_nifti(mask_file)

        # Check if shapes match
        if ref_data.shape != cc_data.shape:
            raise ValueError(f"Shape mismatch: CC {cc_data.shape} vs reference {i + 1} {ref_data.shape}")

        # Convert to binary
        ref_binary = ref_data > 0
        reference_masks.append(ref_binary)

        # If no mask name is provided, use the filename
        if mask_names is None or len(mask_names) <= i:
            mask_name = os.path.splitext(os.path.basename(mask_file))[0]
            if mask_name.endswith('.nii'):
                mask_name = mask_name[:-4]
            mask_names.append(mask_name)

    # Add "Undetermined" category for ties
    mask_names.append("Undetermined")

    # Create a dictionary to count components by mask
    component_counts = {name: 0 for name in mask_names}

    # Create a list to store component details for the dataframe
    component_details = []

    # Process each component
    for component_idx in range(1, num_components + 1):
        # Extract this component
        component_mask = labeled_components == component_idx
        component_size = np.sum(component_mask)

        # Calculate overlap with each reference mask
        overlaps = []
        for i, ref_mask in enumerate(reference_masks):
            overlap_size = np.sum(component_mask & ref_mask)
            overlap_percentage = (overlap_size / component_size) * 100 if component_size > 0 else 0
            overlaps.append((mask_names[i], overlap_size, overlap_percentage))

        # Sort by overlap size in descending order
        overlaps.sort(key=lambda x: x[1], reverse=True)

        # Check if there's a tie for maximum overlap
        if len(overlaps) >= 2 and overlaps[0][1] == overlaps[1][1] and overlaps[0][1] > 0:
            assigned_mask = "Undetermined"
        else:
            assigned_mask = overlaps[0][0] if overlaps and overlaps[0][1] > 0 else "None"

        # Update counts
        component_counts[assigned_mask if assigned_mask in component_counts else "Undetermined"] += 1

        # Store component details
        detail = {
            "Component_ID": component_idx,
            "Component_Size_Voxels": component_size,
            "Assigned_Mask": assigned_mask
        }

        # Add overlap percentages for each reference mask
        for name, _, percentage in overlaps:
            detail[f"{name}_Overlap_Percentage"] = percentage

        component_details.append(detail)

    # Create detailed dataframe
    detail_df = pd.DataFrame(component_details)

    # Create summary dataframe
    summary_data = {
        "Mask_Name": list(component_counts.keys()),
        "Component_Count": list(component_counts.values())
    }
    summary_df = pd.DataFrame(summary_data)

    # Determine output filename if not provided
    if output_csv is None:
        cc_stem = os.path.splitext(os.path.basename(cc_mask_file))[0]
        if cc_stem.endswith('.nii'):
            cc_stem = cc_stem[:-4]
        output_csv = f"{cc_stem}_overlap.csv"

    # Save summary to CSV
    summary_df.to_csv(output_csv, index=False)

    # Save detailed results to a separate CSV
    detail_output_csv = output_csv.replace('.csv', '_details.csv')
    detail_df.to_csv(detail_output_csv, index=False)

    print(f"Summary results saved to {output_csv}")
    print(f"Detailed results saved to {detail_output_csv}")

    # Print summary
    print("\nSummary of CC assignment to masks:")
    for mask_name, count in component_counts.items():
        print(f"  {mask_name}: {count} components")

    return summary_df, detail_df


def main():
    parser = argparse.ArgumentParser(description='Analyze connected components and their overlap with multiple reference masks')
    parser.add_argument('--cc_mask', '-c', required=True,
                        help='Path to the mask NIFTI file containing connected components to analyze')
    parser.add_argument('--reference_masks', '-r', required=True, nargs='+',
                        help='Paths to reference mask NIFTI files to check for overlap')
    parser.add_argument('--mask_names', '-n', nargs='+', default=None,
                        help='Names for each reference mask (optional, will use filenames if not provided)')
    parser.add_argument('--output', '-o', default=None,
                        help='Path to save the CSV results (default: cc_mask_stem_overlap.csv)')

    args = parser.parse_args()

    # Validate mask names match reference masks if provided
    if args.mask_names and len(args.mask_names) != len(args.reference_masks):
        raise ValueError("Number of mask names must match number of reference masks")

    cc_overlap_analysis(args.cc_mask, args.reference_masks, args.output, args.mask_names)


if __name__ == "__main__":
    main()