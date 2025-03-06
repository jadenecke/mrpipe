import argparse
import os
from argparse import RawTextHelpFormatter

parser = argparse.ArgumentParser(
        description='Recenter image origin to Center of Mass.',
        formatter_class=RawTextHelpFormatter)

parser.add_argument('-i', '--image', dest="imagePath", type=str,
                    metavar="path/to/image.nii.gz", default=None,
                    help="Path to Image file.", required=True)
parser.add_argument('-m', '--mask', dest="maskPath", type=str,
                    metavar="path/to/image.nii.gz", default=None,
                    help="Path to Image file.", required=True)
parser.add_argument('-o', '--output', dest='output', type=str, default=None,
                    help='Output filename, i.e. CMB.png.', required=True)
parser.add_argument('--radius', dest='radius', type=int, default=15,
                    help='Radius of circle arround MB for easier identification (in mm)')
parser.add_argument('--zoom', dest='zoom', type=float, default=1,
                    help='Zoom level. 1 equals whole brain, while > 1 yields higher magnification, suggested values are 2-4')

args = parser.parse_args()

if not os.path.isfile(args.imagePath):
    raise IOError("Input Image does not exist: {}".format(args.imagePath))
if not os.path.isfile(args.maskPath):
    raise IOError("Input Mask does not exist: {}".format(args.maskPath))

if (not os.path.isdir(os.path.dirname(args.output)) and os.path.dirname(args.output) != ''):
    raise IOError("Tried to save output image to directory which does not exist. Make sure the the path is correcct and the output directory exists: {}".format(os.path.dirname(args.output)))

def visualize_connected_components(nifti_image_path, nifti_mask_path, output_path, radius_mm, zoom):
    import nibabel as nib
    import numpy as np
    import matplotlib.pyplot as plt
    from scipy.ndimage import label
    from skimage.measure import regionprops
    # Load nifti image and mask
    img = nib.load(nifti_image_path)
    mask = nib.load(nifti_mask_path)


    img_data = img.get_fdata()
    mask_data = mask.get_fdata()
    voxel_size = img.header.get_zooms()

    # Label connected components
    labeled_mask, num_features = label(mask_data)

    # Get bounding boxes of connected components
    regions = regionprops(labeled_mask)

    # Calculate the number of rows and columns for the mosaic
    cols = int(np.ceil(np.sqrt(num_features)))
    rows = int(np.ceil(num_features / cols))

    fig, axes = plt.subplots(rows, cols, figsize=(cols * 5, rows * 5), facecolor='black')

    # Remove space between images
    plt.subplots_adjust(wspace=0, hspace=0)

    for i, region in enumerate(regions):
        print(f"Visualizing component: {i}")
        minr, minc, minz, maxr, maxc, maxz = region.bbox
        print(f'BB: {[minr, minc, minz, maxr, maxc, maxz]}')
        z = int((minz + maxz) / 2)
        x = int((minr + maxr) / 2)
        y = int((minc + maxc) / 2)

        print(f'Microbleed center at  y={y}, x={x}, z={z}.')

        xVisRange = int(np.shape(img_data)[0] / 2 / zoom)
        yVisRange = int(np.shape(img_data)[1] / 2 / zoom)

        xVisMin = np.max([0, x - xVisRange])
        xVisMax = np.min([np.shape(img_data)[0]-1, x + xVisRange])
        yVisMin = np.max([0, y - yVisRange]) 
        yVisMax = np.min([np.shape(img_data)[1]-1, y + yVisRange])

        print(f'Limiting view to y={yVisMin}:{yVisMax} and x={xVisMin}:{xVisMax}.')

        component_mask = labeled_mask[xVisMin:xVisMax, yVisMin:yVisMax, z] == region.label
        component_img = img_data[xVisMin:xVisMax, yVisMin:yVisMax, z]

        xCenterNew = x - xVisMin
        yCenterNew = y - yVisMin

        ax = axes[i // cols, i % cols]
        ax.imshow(component_img.T, cmap='gray', origin='lower',
                  extent=(0, component_img.shape[0] * voxel_size[0],
                          0, component_img.shape[1] * voxel_size[1]))

        alpha_mask = np.zeros_like(component_mask.T, dtype=float)
        alpha_mask[component_mask.T == 1] = 0.5  # Set alpha to 0.5 where mask is 1

        ax.imshow(component_mask.T, cmap='rainbow', origin='lower', alpha=alpha_mask,
                  extent=(0, component_mask.shape[0] * voxel_size[0],
                          0, component_mask.shape[1] * voxel_size[1]))

        # Calculate the center of the bounding box
        center_y = yCenterNew * voxel_size[0]
        center_x = xCenterNew * voxel_size[1]

        # Convert radius from mm to pixels
        radius_px = radius_mm / voxel_size[0]

        # Create a green ring (two concentric circles)
        inner_circle = plt.Circle((center_x, center_y), radius_px - 1, color='green', alpha=0.5, fill=False, linewidth=2)
        outer_circle = plt.Circle((center_x, center_y), radius_px + 1, color='green', alpha=0.5, fill=False, linewidth=2)
        ax.add_patch(inner_circle)
        ax.add_patch(outer_circle)

        ax.set_title(f'Component {i + 1}, Slice {z + 1}', color='white')
        ax.axis('off')

    for j in range(num_features, rows * cols):
        fig.delaxes(axes.flat[j])

    plt.tight_layout()
    plt.savefig(output_path, facecolor='black')
    plt.close()

visualize_connected_components(args.imagePath, args.maskPath, args.output, args.radius, args.zoom)
