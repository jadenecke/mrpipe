from mrpipe.Toolboxes.Task import Task

class ROI(Task):
    """
    Usage:
    fslroi <input> <output> <xmin> <xsize> <ymin> <ysize> <zmin> <zsize>
    fslroi <input> <output> <tmin> <tsize>
    fslroi <input> <output> <xmin> <xsize> <ymin> <ysize> <zmin> <zsize> <tmin> <tsize>
    """

    def __init__(self, infile, output, roiDef: str, name: str = "fslROI", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.inputImage = infile
        self.roiDef = roiDef
        self.outputImage = output

        #add input and output images
        self.addInFiles([self.inputImage])
        self.addOutFiles([self.outputImage])

    def getCommand(self):
        command = f"fslroi {self.inputImage} {self.outputImage} {self.roiDef}"
        return command



