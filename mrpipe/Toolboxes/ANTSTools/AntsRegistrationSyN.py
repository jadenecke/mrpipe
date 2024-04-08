from mrpipe.Toolboxes.Task import Task

class AntsRegistrationSyN(Task):
    """
     -t:  transform type
        t: translation (1 stage)
        r: rigid (1 stage)
        a: rigid + affine (2 stages)
        s: rigid + affine + deformable syn (3 stages)
        sr: rigid + deformable syn (2 stages)
        so: deformable syn only (1 stage)
        b: rigid + affine + deformable b-spline syn (3 stages)
        br: rigid + deformable b-spline syn (2 stages)
        bo: deformable b-spline syn only (1 stage)

    """
    def __init__(self, moving, fixed, outprefix, type, expectedOutFiles = None, ncores=1, dim=3, precision="d", name: str = "AntsRegistrationSyN", clobber=False):
        super().__init__(name=name, clobber=clobber)
        valid_type_cases = ['t', 'r', 'a', 's', 'sr', 'so', 'b', 'br', 'bo']
        if type not in valid_type_cases:
            raise ValueError(f"Invalid input. Expected one of {valid_type_cases}. Got {type}")

        if not (dim == 2 or dim == 3):
            raise ValueError(f"Dim must be either 2 or 3. Got {dim}")

        if precision not in ["d", "f"]:
            raise ValueError(f"Precision must be d or f. Got {precision}")

        self.moving = moving
        self.fixed = fixed
        self.outprefix = outprefix
        self.type = type
        if expectedOutFiles is not None:
            self.expectedOutFiles = expectedOutFiles
        self.ncores = ncores
        self.dim = dim
        self.precision = precision

        if expectedOutFiles is not None:
            self.addOutFiles([self.expectedOutFiles])
        self.addInFiles([self.moving, self.fixed])

    def getCommand(self):
        command = f"antsRegistrationSyN.sh -d {self.dim} -f {self.fixed} -m {self.moving} -o {self.outprefix} -n {self.ncores} -p {self.precision} -t {self.type}"
        return command



