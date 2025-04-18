from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.PathClass import Path
from mrpipe.meta import LoggerModule

logger = LoggerModule.Logger()

class PINGU_PVS(Task):
    def __init__(self, input_image: Path, temp_dir: Path, output_image: Path, pingu_sif: Path, name: str = "PINGU_PVS", clobber=False):
        super().__init__(name=name, clobber=clobber)

        self.input_image = input_image
        self.temp_dir = temp_dir
        self.output_image = output_image
        self.pingu_sif = pingu_sif
        self.command = ""

        # Add input and output images
        self.addInFiles([self.input_image])
        self.addOutFiles([self.output_image])

    def getCommand(self):
        self.output_image.directory = self.temp_dir.createDirectory()
        command = "singularity run --nv " + \
                  f"-B {self.input_image.get_directory()} " + \
                  f"-B {self.temp_dir} " + \
                  f"-B {self.output_image.get_directory()} " + \
                  f"{self.pingu_sif} " + \
                  f"{self.input_image} " + \
                  f"{self.temp_dir} " + \
                  f"{self.output_image}"
        return command