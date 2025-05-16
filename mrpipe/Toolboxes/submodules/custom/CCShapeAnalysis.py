import os
import numpy as np
import nibabel as nib
from scipy import ndimage
from skimage.measure import regionprops, label, marching_cubes, mesh_surface_area
from skimage.morphology import binary_dilation, convex_hull_image
from scipy.spatial.distance import cdist
import pandas as pd
import argparse

from tqdm import tqdm


def load_nifti(file_path):
    """Load a NIFTI file and return its data and affine transform."""
    img = nib.load(file_path)
    return img.get_fdata(), img.affine, img.header


def get_voxel_volume(affine):
    """Calculate voxel volume in mm³ from the affine transformation matrix."""
    # Extract the scaling factors from the affine matrix
    sx, sy, sz = np.array([np.sqrt(np.sum(affine[:3, i] ** 2)) for i in range(3)])
    return sx * sy * sz

def get_voxel_dims(affine):
    """Calculate voxel volume in mm³ from the affine transformation matrix."""
    # Extract the scaling factors from the affine matrix
    sx, sy, sz = np.array([np.sqrt(np.sum(affine[:3, i] ** 2)) for i in range(3)])
    return np.array([sx, sy, sz])


def calculate_min_distance(lesion_mask, ventricle_mask):
    """Calculate minimum distance from lesion to ventricle edge."""
    # Find edges
    ventricle_edge = binary_dilation(ventricle_mask) & ~ventricle_mask
    if not np.any(ventricle_edge):
        return float('inf')  # No ventricle edge found

    # Get coordinates of edges
    ventricle_edge_coords = np.array(np.where(ventricle_edge)).T

    if not np.any(lesion_mask):
        return float('inf')  # No lesion found

    lesion_coords = np.array(np.where(lesion_mask)).T

    if len(ventricle_edge_coords) == 0 or len(lesion_coords) == 0:
        return float('inf')

    # Calculate minimum Euclidean distance
    distances = cdist(lesion_coords, ventricle_edge_coords, 'euclidean')
    return np.min(distances)


def calculate_eigenvalues(component_mask, affine):
    """Calculate eigenvalues for a component and derive fractional anisotropy."""
    # Get properties of the region
    props = regionprops(component_mask.astype(int))[0]

    # Get inertia tensor eigenvalues (already sorted in ascending order)
    eigenvalues = props.inertia_tensor_eigvals

    # Adjust eigenvalues according to voxel dimensions
    voxel_dims = get_voxel_dims(affine)
    adjusted_eigenvalues = eigenvalues * voxel_dims ** 2

    # Calculate fractional anisotropy if there are 3 eigenvalues
    if len(adjusted_eigenvalues) == 3:
        e1, e2, e3 = adjusted_eigenvalues
        # Calculate mean diffusivity
        mean_diff = (e1 + e2 + e3) / 3

        # Check for division by zero
        if mean_diff == 0:
            fa = 0
        else:
            # Calculate fractional anisotropy
            numerator = np.sqrt((e1 - mean_diff) ** 2 + (e2 - mean_diff) ** 2 + (e3 - mean_diff) ** 2)
            denominator = np.sqrt(2 * (e1 ** 2 + e2 ** 2 + e3 ** 2))

            if denominator == 0:
                fa = 0
            else:
                fa = np.sqrt(3 / 2) * (numerator / denominator)

        return adjusted_eigenvalues, fa
    else:
        # Handle case with fewer than 3 eigenvalues
        padded_eigvals = np.pad(adjusted_eigenvalues, (0, 3 - len(adjusted_eigenvalues)))
        return padded_eigvals, 0.0


def calculate_shape_metrics(component_mask, affine):
    """
    Calculate various shape metrics for a component.
    
    References:
    1. Compactness: Bribiesca, E. (2008). An easy measure of compactness for 2D and 3D shapes. Pattern Recognition, 41(2), 543-554.
       Formula: V / (S^(3/2)), where V is volume and S is surface area
       
    2. Sphericity: Wadell, H. (1935). Volume, shape, and roundness of quartz particles. The Journal of Geology, 43(3), 250-280.
       Formula: ((36π * V^2)^(1/3)) / S, where V is volume and S is surface area
       
    3. Circularity: From medical image analysis literature, adapted from 2D definition
       Formula: 4π * area / perimeter^2 (in 2D), approximated in 3D using sphericity
       
    4. Convexity: Zunic, J., & Rosin, P. L. (2004). A new convexity measure for polygons. IEEE Transactions on Pattern Analysis and Machine Intelligence, 26(7), 923-934.
       Formula: convex perimeter / perimeter
       
    5. Solidity: Defined in multiple imaging references including Shapiro, L. G., & Stockman, G. C. (2001). Computer Vision. Prentice Hall.
       Formula: volume / convex hull volume
       
    6. Curvature: Approximated based on principles from differential geometry, simplified for discrete volumes
       as described in Pottmann, H., et al. (2007). Discrete surfaces for architectural design. Curves and Surface Design.
    """
    # Get voxel dimensions in mm
    voxel_dims = get_voxel_dims(affine)
    voxel_volume = np.prod(voxel_dims)
    
    # Calculate surface volume
    volume = np.sum(component_mask) * voxel_volume

     # Calculate surface area using marching cubes
    verts, faces, _, _ = marching_cubes(component_mask, spacing=voxel_dims)
    # Calculate surface area
    surface_area = mesh_surface_area(verts, faces)

    # Compute convex hull
    convex_hull = convex_hull_image(component_mask)
    convex_volume = np.sum(convex_hull) * voxel_volume
    
    # Calculate metrics
    # Compactness: V / (S^(3/2)) [Bribiesca, 2008]
    # larger values indicate more compact shapes
    compactness = 1 - (volume / (surface_area ** 1.5)) if surface_area > 0 else 1
    
    # Sphericity: (36π * V^2)^(1/3) / S [Wadell, 1935] # checked, seems to be correct (if volume and surface area calculations are correct)
    # 1 for perfect sphere, < 1 for less spherical shapes
    sphericity = ((36 * np.pi * volume**2)**(1/3)) / surface_area if surface_area > 0 else 0
    
    # Circularity: surface area of a perfect sphere with the same volume over the shapes surface area
    # TODO: I think it is the same as sphericity?
    circularity = ((np.pi**(1/3.0) * (6 * volume)**(2/3.0)) / surface_area)

    # Solidity: volume / convex hull volume # how much it is "filled out" even though it might not be a perfect sphere.
    solidity = volume / convex_volume if convex_volume > 0 else 0

    
    return {
        'Compactness': compactness,
        'Sphericity': sphericity,
        'Circularity': circularity,
        'Solidity': solidity,
    }


def create_attribute_image(labeled_lesions, num_components, attribute_type, results_df, lesion_affine, lesion_header):
    """Create a NIFTI image with lesions colored by the selected attribute."""
    # Initialize an empty volume with the same shape as the labeled lesions
    attribute_img = np.zeros_like(labeled_lesions, dtype=np.float32)
    
    # Map each component to its attribute value
    for component_idx in range(1, num_components + 1):
        component_mask = labeled_lesions == component_idx
        
        # Get the attribute value for this component
        if attribute_type == 'volume':
            value = results_df.loc[results_df['Component_ID'] == component_idx, 'Volume_mm3'].values[0]
        elif attribute_type == 'distance':
            value = results_df.loc[results_df['Component_ID'] == component_idx, 'Min_Distance_to_Ventricle_mm'].values[0]
        elif attribute_type == 'fa':
            value = results_df.loc[results_df['Component_ID'] == component_idx, 'Fractional_Anisotropy'].values[0]
        elif attribute_type == 'compactness':
            value = results_df.loc[results_df['Component_ID'] == component_idx, 'Compactness'].values[0]
        elif attribute_type == 'sphericity':
            value = results_df.loc[results_df['Component_ID'] == component_idx, 'Sphericity'].values[0]
        elif attribute_type == 'circularity':
            value = results_df.loc[results_df['Component_ID'] == component_idx, 'Circularity'].values[0]
        elif attribute_type == 'solidity':
            value = results_df.loc[results_df['Component_ID'] == component_idx, 'Solidity'].values[0]
        else:
            raise ValueError(f"Invalid attribute type: {attribute_type}")
        
        # Assign the attribute value to the component voxels
        attribute_img[component_mask] = value
    
    # Create a new NIFTI image
    nifti_img = nib.Nifti1Image(attribute_img, lesion_affine, lesion_header)
    
    return nifti_img


def analyze_lesions(lesion_file, ventricle_file, attribute_type='volume', output_stem=None):
    """Analyze lesions and create output files with results."""
    # Determine output stem if not provided
    if output_stem is None:
        output_stem = os.path.splitext(os.path.basename(lesion_file))[0]
        # Remove .nii if present in the stem (for cases like file.nii.gz)
        if output_stem.endswith('.nii'):
            output_stem = output_stem[:-4]
    
    # Define output filenames
    output_csv = f"{output_stem}_stats.csv"
    output_nifti = f"{output_stem}_attribute.nii.gz"
    
    # Load the NIFTI files
    lesion_data, lesion_affine, lesion_header = load_nifti(lesion_file)
    ventricle_data, ventricle_affine, _ = load_nifti(ventricle_file)

    # Check if shapes match
    if lesion_data.shape != ventricle_data.shape:
        raise ValueError(f"Shape mismatch: lesion {lesion_data.shape} vs ventricle {ventricle_data.shape}")

    # Label connected components in the lesion mask
    labeled_lesions, num_components = label(lesion_data > 0, return_num=True)

    # Convert ventricle mask to binary
    ventricle_mask = ventricle_data > 0

    # Calculate voxel volume
    voxel_vol = get_voxel_volume(lesion_affine)

    # Initialize results
    results = []

    print(f"Found {num_components} lesion components")

    # Analyze each lesion component
    for component_idx in tqdm(range(1, num_components + 1)):
        # Extract this component
        component_mask = labeled_lesions == component_idx

        # Calculate volume
        volume_mm3 = np.sum(component_mask) * voxel_vol

        # Calculate minimum distance to ventricle
        min_dist = calculate_min_distance(component_mask, ventricle_mask)

        # Calculate eigenvalues and fractional anisotropy
        if np.sum(component_mask) > 1:  # Need at least 2 voxels for eigenvalue decomposition
            eigenvalues, fa = calculate_eigenvalues(component_mask, lesion_affine)
            e1, e2, e3 = eigenvalues if len(eigenvalues) == 3 else (eigenvalues[0], eigenvalues[1] if len(eigenvalues) > 1 else 0, 0)
        else:
            e1, e2, e3, fa = 0, 0, 0, 0

        # Convert min_dist from voxel units to mm
        min_dist_mm = min_dist * np.mean([np.sqrt(np.sum(lesion_affine[:3, i] ** 2)) for i in range(3)])
        
        # Calculate shape metrics
        shape_metrics = calculate_shape_metrics(component_mask, lesion_affine)

        # Store results
        result_dict = {
            'Component_ID': component_idx,
            'Volume_mm3': volume_mm3,
            'Min_Distance_to_Ventricle_mm': min_dist_mm,
            'Eigenvalue_1': e1,
            'Eigenvalue_2': e2,
            'Eigenvalue_3': e3,
            'Fractional_Anisotropy': fa
        }
        
        # Add shape metrics to the result dictionary
        result_dict.update(shape_metrics)
        
        results.append(result_dict)

    # Create dataframe and save to CSV
    results_df = pd.DataFrame(results)
    results_df.to_csv(output_csv, index=False)
    print(f"Statistics saved to {output_csv}")
    

    if attribute_type == 'all':
        for attribute in ['volume', 'distance', 'fa', 'compactness', 'sphericity', 'circularity', 'solidity']:
            output_nifti = f"{output_stem}_{attribute}_attribute.nii.gz"
            attribute_img = create_attribute_image(
                labeled_lesions,
                num_components,
                attribute,
                results_df,
                lesion_affine,
                lesion_header
            )
            nib.save(attribute_img, output_nifti)
            print(f"Attribute image saved to {output_nifti}")
    elif attribute_type in ['volume', 'distance', 'fa', 'compactness', 'sphericity', 'circularity', 'solidity']:
        # Create attribute image
        attribute_img = create_attribute_image(
            labeled_lesions,
            num_components,
            attribute_type,
            results_df,
            lesion_affine,
            lesion_header
        )
        # Save the attribute image
        nib.save(attribute_img, output_nifti)
        print(f"Attribute image saved to {output_nifti}")
    else:
        print("Not saving any attribute image")

    return results_df


def main():
    parser = argparse.ArgumentParser(description='Analyze brain lesion in relation to ventricles')
    parser.add_argument('--lesion', '-l', required=True, help='Path to the lesion mask NIFTI file')
    parser.add_argument('--ventricle', '-v', required=True, help='Path to the ventricle mask NIFTI file')
    parser.add_argument('--attribute', '-a', 
                        choices=['volume', 'distance', 'fa', 'compactness', 'sphericity', 
                                 'circularity', 'solidity', 'none', 'all'],
                        default='none',
                        help='Attribute to color the output image')
    parser.add_argument('--output_stem', '-o', default=None,
                        help='Stem for output filenames (default: derived from lesion filename)')

    args = parser.parse_args()

    analyze_lesions(args.lesion, args.ventricle, args.attribute, args.output_stem)


if __name__ == "__main__":
    main()