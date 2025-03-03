import nibabel as nib
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import label
from skimage.measure import regionprops


def visualize_connected_components(nifti_image_path, nifti_mask_path, output_path, radius_mm):
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
        minr, minc, minz, maxr, maxc, maxz = region.bbox

        z = round((minz + maxz) / 2)
        component_mask = labeled_mask[:, :, z] == region.label
        component_img = img_data[:, :, z]

        ax = axes[i // cols, i % cols]
        ax.imshow(component_img.T, cmap='gray', origin='lower',
                  extent=(0, component_img.shape[0] * voxel_size[0],
                          0, component_img.shape[1] * voxel_size[1]))

        alpha_mask = np.zeros_like(component_mask.T, dtype=float)
        alpha_mask[component_mask.T == 1] = 0.5  # Set alpha to 0.5 where mask is 1

        ax.imshow(component_mask.T, cmap='Reds', origin='lower', alpha=alpha_mask,
                  extent=(0, component_mask.shape[0] * voxel_size[0],
                          0, component_mask.shape[1] * voxel_size[1]))

        # Calculate the center of the bounding box
        center_y = (minc + maxc) / 2 * voxel_size[0]
        center_x = (minr + maxr) / 2 * voxel_size[1]

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


# Example usage
visualize_connected_components('/Users/jdenecke/Documents/mrpipeTest/data_bids/sub-001/ses-01/FLAIR2/sub-001_ses-01_FLAIR.nii.gz', '/Users/jdenecke/Documents/mrpipeTest/data_bids/sub-001/ses-01/FLAIR2/seg.nii.gz', '/Users/jdenecke/Documents/mrpipeTest/data_bids/sub-001/ses-01/FLAIR2/seg.png', radius_mm=15)
