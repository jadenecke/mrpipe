from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.PathClass import Path
from mrpipe.meta import LoggerModule


logger = LoggerModule.Logger()

class MARS_Brainstem(Task):
    def __init__(self, t1: Path, brainstemSegOut: Path, MarsBrainstemSIF: Path, name: str = "MARS-Brainstem", clobber=False):
        super().__init__(name=name, clobber=clobber)

        self.t1 = t1
        self.MarsBrainstemSIF = MarsBrainstemSIF
        self.brainstemSegOut = brainstemSegOut
        self.command = ""

        #add input and output images
        self.addInFiles([self.t1])
        self.addOutFiles([self.brainstemSegOut])

    def getCommand(self):
        command = "singularity run --nv " + \
                  f"-B {self.t1.get_directory()} " + \
                  f"-B {self.brainstemSegOut.get_directory()} " + \
                  f"{self.MarsBrainstemSIF} " + \
                  f"-o {self.brainstemSegOut} "
        if self.clobber:
            command += f"-x "
        command += f"{self.t1}"
        return command

