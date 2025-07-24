import argparse
import os
from argparse import RawTextHelpFormatter

parser = argparse.ArgumentParser(
        description='Count number of connected components',
        formatter_class=RawTextHelpFormatter)

parser.add_argument('-m', '--mask', dest="maskPath", type=str,
                    metavar="path/to/image.nii.gz", default=None,
                    help="Path to Image file.", required=True)
parser.add_argument('-c', '--connectivity', dest="connectivity", type=int,
                    metavar="6|18|26", default=26,
                    help="Connectivity type: 6, 18, or 26 for 3D images. Default: 6")

args = parser.parse_args()

if not os.path.isfile(args.maskPath):
    raise IOError("Input Mask does not exist: {}".format(args.maskPath))

def count_connected_components(nifti_mask_path, connectivity=26):
    import nibabel as nib
    from scipy.ndimage import label
    import scipy.ndimage as ndi

    mask = nib.load(nifti_mask_path)
    mask_data = mask.get_fdata()

    # Label connected components
    if connectivity == 6:
        structure = ndi.generate_binary_structure(3, 1)  # 6-connectivity
    elif connectivity == 18:
        structure = ndi.generate_binary_structure(3, 2)  # 18-connectivity
    elif connectivity == 26:
        structure = ndi.generate_binary_structure(3, 3)  # 26-connectivity
    else:
        # Default to 26-connectivity if invalid value provided
        structure = ndi.generate_binary_structure(3, 3)

    _, num_features = label(mask_data, structure=structure)

    return num_features


print(count_connected_components(args.maskPath, args.connectivity))
