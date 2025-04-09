import argparse
import os
from argparse import RawTextHelpFormatter

parser = argparse.ArgumentParser(
        description='Count number of connected components',
        formatter_class=RawTextHelpFormatter)

parser.add_argument('-m', '--mask', dest="maskPath", type=str,
                    metavar="path/to/image.nii.gz", default=None,
                    help="Path to Image file.", required=True)

args = parser.parse_args()

if not os.path.isfile(args.maskPath):
    raise IOError("Input Mask does not exist: {}".format(args.maskPath))

def count_connected_components(nifti_mask_path):
    import nibabel as nib
    from scipy.ndimage import label


    mask = nib.load(nifti_mask_path)
    mask_data = mask.get_fdata()


    # Label connected components
    _, num_features = label(mask_data)

    return num_features


print(count_connected_components(args.maskPath))
