import argparse
import os
from argparse import RawTextHelpFormatter

parser = argparse.ArgumentParser(
        description='Characterize connected components in a binary image. Output is: Count, Min, Max, Mean, Std',
        formatter_class=RawTextHelpFormatter)

parser.add_argument('-i', '--input', dest="imagePath", type=str,
                    metavar="path/to/mask.nii.gz", default=None,
                    help="Path to mask file.", required=True)
parser.add_argument('-c', '--connectivity', dest="connectivity", type=int,
                    metavar="6|18|26", default=26,
                    help="Connectivity type: 6, 18, or 26 for 3D images. Default: 6")

args = parser.parse_args()

if not os.path.isfile(args.imagePath):
    raise IOError("Input Image does not exist: {}".format(args.imagePath))


def characterise_connected_components(nifti_image_path, connectivity=26):
    try:
        import nibabel as nib
        import numpy as np
        from scipy.ndimage import label
        from skimage.measure import regionprops
        import scipy.ndimage as ndi

        # Load nifti image
        img = nib.load(nifti_image_path)
        img_data = img.get_fdata()

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
            return "0,NA,NA,NA,NA"

        # Calculate statistics
        regions = regionprops(labeled_mask)
        cc_sizes = [region.area for region in regions]

        min_size = np.min(cc_sizes)
        max_size = np.max(cc_sizes)
        mean_size = np.mean(cc_sizes)
        std_size = np.std(cc_sizes)

        # Format results as comma-separated string
        result = f"{num_cc},{min_size},{max_size},{mean_size:.2f},{std_size:.2f}"
        return result

    except Exception as e:
        print(f"Error: {str(e)}")
        return "NA,NA,NA,NA,NA"


# Call the function with the provided arguments and print the result
result = characterise_connected_components(args.imagePath, args.connectivity)
print(result)
