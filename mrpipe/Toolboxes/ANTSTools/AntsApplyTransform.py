from mrpipe.Toolboxes.Task import Task
from typing import List
from mrpipe.meta.PathClass import Path
from mrpipe.Helper import Helper
import re
from mrpipe.meta import LoggerModule

logger = LoggerModule.Logger()

class AntsApplyTransforms(Task):
    """
     interpolation: Linear NearestNeighbor MultiLabel[<sigma=imageSpacing>,<alpha=4.0>] Gaussian[<sigma=imageSpacing>,<alpha=1.0>] BSpline[<order=3>] CosineWindowedSinc WelchWindowedSinc HammingWindowedSinc LanczosWindowedSinc
     Transforms: Transforms are not reversed, so the must be specified in inverse order, i.e. are put on top of a stack, meaning last in first out (LIFO) stack
    """
    def __init__(self, input, output, reference, transforms: List[Path], interpolation="BSpline", dim=3,
                 name: str = "AntsApplyTransforms", clobber=False, verbose=False, inverse_transform: List[bool] = None):
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
        if inverse_transform is None:
            self.inverse_transforms = None
        else:
            self.inverse_transforms = Helper.ensure_list(inverse_transform, flatten=True)
            if len(self.transforms) != len(self.inverse_transforms):
                logger.critical(f"InverseTransform must have the same length as transforms ({len(self.transforms)}), but has length {len(self.inverse_transforms)}")

        self.addOutFiles([self.output])
        self.addInFiles([self.input, self.reference, self.transforms])

    def getCommand(self):
        command = f"antsApplyTransforms -d {self.dim} -i {self.input} -r {self.reference} -o {self.output} -n {self.interpolation}"
        if self.inverse_transforms is not None:
            for transform, inverse_transform in zip(self.transforms, self.inverse_transforms):
                if inverse_transform:
                    command += f" -t [{transform}, 1]"
                else:
                    command += f" -t {transform}"
        else:
            for transform in self.transforms:
                command += f" -t {transform}"
        if self.verbose:
            command += " -v"
        return command



