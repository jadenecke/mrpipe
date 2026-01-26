import argparse
import os
from argparse import RawTextHelpFormatter

parser = argparse.ArgumentParser(
    description='Keep only the largest connected component from a binary image.',
    formatter_class=RawTextHelpFormatter)

parser.add_argument('-i', '--input', dest="imagePath", type=str,
                    metavar="path/to/mask.nii.gz", default=None,
                    help="Path to input mask file.", required=True)
parser.add_argument('-o', '--output', dest="outputPath", type=str,
                    metavar="path/to/output.nii.gz", default=None,
                    help="Path to output mask file.", required=True)
parser.add_argument('-c', '--connectivity', dest="connectivity", type=int,
                    metavar="6|18|26", default=26,
                    help="Connectivity type: 6, 18, or 26 for 3D images. Default: 26")

args = parser.parse_args()

if not os.path.isfile(args.imagePath):
    raise IOError("Input Image does not exist: {}".format(args.imagePath))

# Create output directory if it doesn't exist
output_dir = os.path.dirname(args.outputPath)
if output_dir and not os.path.exists(output_dir):
    os.makedirs(output_dir)


def reduce_to_largest_cc(nifti_image_path, output_path, connectivity=26):
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

        # If no connected components found, save empty mask
        if num_cc == 0:
            nib.save(img, output_path)
            print("0 connected components found. Saved empty mask.")
            return 0

        # Find the largest connected component
        new_mask = np.zeros_like(img_data)
        regions = regionprops(labeled_mask)

        if regions:
            # Sort regions by area and get the largest one
            largest_region = max(regions, key=lambda r: r.area)
            new_mask[labeled_mask == largest_region.label] = 1

            print(f"Largest connected component has {largest_region.area} voxels. "
                  f"Removed {num_cc - 1} smaller components. Saved to {output_path}")
        else:
            print("No valid regions found. Saved empty mask.")
            return 1

        # Create a new image with the same header as the input
        new_img = nib.Nifti1Image(new_mask, img.affine, img.header)

        # Save the new image
        nib.save(new_img, output_path)
        return 0

    except Exception as e:
        print(f"Error: {str(e)}")
        return 1


# Call the function with the provided arguments and print the result
result = reduce_to_largest_cc(args.imagePath, args.outputPath, args.connectivity)
exit(result)