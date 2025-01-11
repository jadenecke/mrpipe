from mrpipe.Toolboxes.Task import Task


class CP(Task):

    def __init__(self, infile, outfile, name="CP", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.infile = infile
        self.outfile = outfile

        # add input and output images
        self.addInFiles([self.infile])
        self.addOutFiles([self.outfile])

    def getCommand(self):
        command = f"cp {self.infile} {self.outfile}"
        return command


