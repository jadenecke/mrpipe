from mrpipe.Toolboxes.Task import Task
class N4BiasFieldCorrect(Task):

    def getRequiredModules(self):
        return "ants/2.3.4"

    def getCommand(self):
        command = f"N4BiasFieldCorrection -i {self.inputImage} -o {self.outputImage}"
        if self.mask:
            command += f" -m {self.mask}"
        if self.verbose:
            command += f" -v"
        return command

    def __init__(self, infile, outfile, name: str, mask=None, verbose=False):
        super().__init__(name)
        self.addInFiles(infile)
        self.inputImage = infile
        self.addOutFiles(outfile)
        self.outputImage = outfile
        self.mask = mask
        self.verbose = verbose

