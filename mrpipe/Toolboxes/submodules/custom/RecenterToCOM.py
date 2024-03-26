import argparse
from argparse import RawTextHelpFormatter
import numpy as np
import nibabel as nb
import os
import scipy as scp
parser = argparse.ArgumentParser(
        description='Recenter image origin to Center of Mass.',
        formatter_class=RawTextHelpFormatter)

parser.add_argument('-i', '--image', dest="imagePath", type=str,
                    metavar="path/to/image.nii.gz", default=None,
                    help="Path to Image file.", required=True)
parser.add_argument('-o', '--output', dest='output', type=str, default=None,
                    help='Output filename.', required=True)
parser.add_argument('--abs', dest='abs', action='store_true',
                    help='Take absolute of image before calculating center of mass')
parser.add_argument('-c', '--clobber', dest='clobber', action='store_true',
                    help='Overwrite existing files')
args = parser.parse_args()

if not os.path.isfile(args.imagePath):
    raise IOError("Input File does not exist: {}".format(args.imagePath))

if (not args.clobber) and os.path.isfile(args.output):
    raise IOError("Output file already exists and clobber is False: {}".format(args.output))

img = nb.load(args.imagePath)
if len(img.shape) == 3:
    if args.abs:
        newCenter = scp.ndimage.center_of_mass(np.abs(img.get_fdata()))
    else:
        newCenter = scp.ndimage.center_of_mass(img.get_fdata())
elif len(img.shape) == 4:
    if args.abs:
        newCenter = scp.ndimage.center_of_mass(np.abs(img.get_fdata()[:, :, :, 1]))
    else:
        newCenter = scp.ndimage.center_of_mass(img.get_fdata()[:, :, :, 1])
else:
    raise IOError("Input Image is not 3D or 4D: {}".format(args.imagePath))

affine = img.affine
inverse = np.linalg.inv(affine)
inverse[:3, 3] = newCenter
newAffine = np.linalg.inv(inverse)
img.set_sform(newAffine)
nb.save(img, args.output)

