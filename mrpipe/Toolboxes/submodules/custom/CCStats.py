import argparse
import os
from argparse import RawTextHelpFormatter

parser = argparse.ArgumentParser(
        description='Characterize connected components in a binary image. Returns a single statistic based on the requested parameter.',
        formatter_class=RawTextHelpFormatter)

parser.add_argument('-i', '--input', dest="imagePath", type=str,
                    metavar="path/to/mask.nii.gz", default=None,
                    help="Path to mask file.", required=True)
parser.add_argument('-c', '--connectivity', dest="connectivity", type=int,
                    metavar="6|18|26", default=26,
                    help="Connectivity type: 6, 18, or 26 for 3D images. Default: 26")
parser.add_argument('-s', '--statistic', dest="statistic", type=str,
                    choices=["countCC", "minVoxel", "maxVoxel", "meanVoxel", "stdVoxel", "totalVoxel", "minVolume", "maxVolume", "meanVolume", "stdVolume", "totalVolume"],
                    default="countCC",
                    help="Statistic to return. Default: countCC")

args = parser.parse_args()

if not os.path.isfile(args.imagePath):
    raise IOError("Input Image does not exist: {}".format(args.imagePath))


def characterise_connected_components(nifti_image_path, connectivity=26, statistic="countCC"):
    import nibabel as nib
    import numpy as np
    from scipy.ndimage import label
    from skimage.measure import regionprops
    import scipy.ndimage as ndi

    # Load nifti image
    img = nib.load(nifti_image_path)
    img_data = img.get_fdata()

    # Get voxel dimensions for volume calculation
    voxel_dims = img.header.get_zooms()
    voxel_volume = voxel_dims[0] * voxel_dims[1] * voxel_dims[2]  # in mm³

    # Convert connectivity parameter to structure
    if connectivity == 6:
        structure = ndi.generate_binary_structure(3, 1)  # 6-connectivity
    elif connectivity == 18:
        structure = ndi.generate_binary_structure(3, 2)  # 18-connectivity
    elif connectivity == 26:
        structure = ndi.generate_binary_structure(3, 3)  # 26-connectivity
    else:
        # Default to 26-connectivity if invalid value provided
        structure = ndi.generate_binary_structure(3, 3)

    # Label connected components
    labeled_mask, num_cc = label(img_data, structure=structure)

    # If no connected components found
    if num_cc == 0:
        return "0" if statistic in ["countCC", "totalVoxel", "totalVolume"] else "NA"

    # Calculate statistics
    regions = regionprops(labeled_mask)
    cc_sizesVoxel = [region.area for region in regions]
    cc_sizesVolume = [size * voxel_volume for size in cc_sizesVoxel]

    # Calculate requested statistic
    if statistic == "countCC":
        result = num_cc
    elif statistic == "minVoxel":
        result = np.min(cc_sizesVoxel)
    elif statistic == "maxVoxel":
        result = np.max(cc_sizesVoxel)
    elif statistic == "meanVoxel":
        result = np.mean(cc_sizesVoxel)
    elif statistic == "stdVoxel":
        result = np.std(cc_sizesVoxel)
    elif statistic == "totalVoxel":
        result = np.sum(cc_sizesVoxel)
    elif statistic == "minVolume":
        result = np.min(cc_sizesVolume)
    elif statistic == "maxVolume":
        result = np.max(cc_sizesVolume)
    elif statistic == "meanVolume":
        result = np.mean(cc_sizesVolume)
    elif statistic == "stdVolume":
        result = np.std(cc_sizesVolume)
    elif statistic == "totalVolume":
        result = np.sum(cc_sizesVolume)
    else:
        # Default to count if invalid statistic
        result = num_cc

    # Format the result
    if isinstance(result, (int, np.integer)):
        return str(result)
    else:
        return f"{result:.2f}"


# Call the function with the provided arguments and print the result
result = characterise_connected_components(args.imagePath, args.connectivity, args.statistic)
print(result)
