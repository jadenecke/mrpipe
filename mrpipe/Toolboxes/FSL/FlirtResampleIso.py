from mrpipe.Toolboxes.Task import Task
from mrpipe.Helper import Helper
class FlirtResampleIso(Task):

    def __init__(self, infile, reference, output, isoRes, interpolation="spline", name: str = "FlirtResampleIso", clobber=False):
        super().__init__(name=name, clobber=clobber)
        valid_interpolation_cases = ["trilinear", "nearestneighbour", "sinc", "spline"]
        if interpolation not in valid_interpolation_cases:
            raise ValueError(f"Invalid input. Expected one of {valid_interpolation_cases}. Got {interpolation}")

        self.inputImage = infile
        self.outputImage = output
        self.reference = reference
        self.isoRes = str(isoRes)
        self.interpolation = interpolation

        #add input and output images
        self.addInFiles([self.inputImages, self.reference])
        self.addOutFiles([self.outputImage])

    def getCommand(self):
        command = f"flirt -in {self.inputImage} -out {self.outputImage} -ref {self.reference} -usesqform -nosearch -applyisoxfm {self.isoRes} -interp {self.interpolation}"
        return command



