import re

from mrpipe.Toolboxes.Task import Task
from typing import List
from mrpipe.meta.PathClass import Path
from mrpipe.Helper import Helper
import re
class AntsApplyTransforms(Task):
    """
     interpolation: Linear NearestNeighbor MultiLabel[<sigma=imageSpacing>,<alpha=4.0>] Gaussian[<sigma=imageSpacing>,<alpha=1.0>] BSpline[<order=3>] CosineWindowedSinc WelchWindowedSinc HammingWindowedSinc LanczosWindowedSinc
     Transforms: Transforms are not reversed, so the must be specified in inverse order, i.e. are put on top of a stack, meaning last in first out (LIFO) stack
    """
    def __init__(self, input, output, reference, transforms: List[Path], interpolation="BSpline", dim=3, name: str = "AntsRegistrationSyN", clobber=False, verbose=False, useInverseTransform = False):
        super().__init__(name=name, clobber=clobber)
        valid_type_interpolation = ["Linear", "NearestNeighbor", "MultiLabel.*", "Gaussian.*", "BSpline.*", "CosineWindowedSinc", "WelchWindowedSinc", "HammingWindowedSinc", "LanczosWindowedSinc"]
        if not any(re.match(pattern=p, string=interpolation) for p in valid_type_interpolation):
            raise ValueError(f"Invalid input. Expected one of {valid_type_interpolation}. Got {type}")

        if not (dim == 2 or dim == 3):
            raise ValueError(f"Dim must be either 2 or 3. Got {dim}")

        self.input = input
        self.output = output
        self.reference = reference
        self.interpolation = interpolation
        self.transforms = Helper.ensure_list(transforms, flatten=True)
        self.dim = dim
        self.verbose = verbose
        self.useInverseTransform = useInverseTransform
        if useInverseTransform and len(self.transforms) > 1:
            raise ValueError(f"Implementation only works with one transform. Got {len(self.transforms)} transforms. This must be fixed in the code. Source: {self.name}.")

        self.addOutFiles([self.output])
        self.addInFiles([self.input, self.reference, self.transforms])

    def getCommand(self):
        command = f"antsApplyTransforms -d {self.dim} -i {self.input} -r {self.reference} -o {self.output} -n {self.interpolation}"
        if self.useInverseTransform:
            command += f" -t [{self.transforms[0]}, 1]"
        else:
            for transform in self.transforms:
                command += f" -t {transform}"
        if self.verbose:
            command += " -v"
        return command



