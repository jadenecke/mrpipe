import argparse
import nibabel as nib
import numpy as np

def main(input_file, output_file, projection_type, z_stack_height):
    # Load the NIfTI file
    img = nib.load(input_file)
    img_data = img.get_fdata()
    header = img.header

    # Get voxel size
    voxel_size = header.get_zooms()

    # Calculate the number of slices for the z-stack height
    z_slices = int(z_stack_height / voxel_size[2])

    proj_data = np.zeros_like(img_data)

    # Perform the projection for each z-slice
    for z in range(img_data.shape[2]):
        if projection_type == 'max':
            proj_data[:, :, z] = np.max(img_data[:, :, max(0, z - z_slices):z + 1], axis=2)
        elif projection_type == 'min':
            proj_data[:, :, z] = np.min(img_data[:, :, max(0, z - z_slices):z + 1], axis=2)
        else:
            raise ValueError("Invalid projection type. Use 'max' or 'min'.")

    # Create a new NIfTI image
    proj_img = nib.Nifti1Image(proj_data, img.affine, img.header)

    # Save the new NIfTI image
    nib.save(proj_img, output_file)

    print(f'Projection saved to {output_file}')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform maximum or minimum intensity projection on a NIfTI image.")
    parser.add_argument('-i', '--input_file', dest='input_file', type=str, help='Path to the input NIfTI file.')
    parser.add_argument('-o', '--output_file', dest='output_file', type=str, help='Path to the output NIfTI file.')
    parser.add_argument('-p', '--projection_type', dest='projection_type', type=str, choices=['max', 'min'], help='Type of projection: max or min.', default = "min")
    parser.add_argument('-z', '--z_stack_height', dest='z_stack_height', type=float, help='Z-stack height in millimeters.', default=8)

    args = parser.parse_args()
    main(args.input_file, args.output_file, args.projection_type, args.z_stack_height)
