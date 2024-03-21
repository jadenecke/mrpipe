from mrpipe.Toolboxes.Task import Task
from mrpipe.Helper import Helper
class Add(Task):

    def __init__(self, infiles, output, name: str = "add", clobber=False):
        super().__init__(name=name, clobber=clobber)
        if len(infiles) < 2:
            raise ValueError("Not enough input files, need at least a list with 2 files")
        self.inputImages = Helper.ensure_list(infiles, flatten=True)
        self.outputImage = output

        #add input and output images
        self.addInFiles(self.inputImages)
        self.addOutFiles([self.outputImage])

    def getCommand(self):
        command = f"fslmaths "
        for i, name in enumerate(self.inputImages):
            if i == 0:
                command += f" {name}"
            else:
                command += f" -add {name}"
        command += f" {self.outputImage}"
        return command



