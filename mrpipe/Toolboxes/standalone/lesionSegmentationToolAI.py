from mrpipe.Toolboxes.Task import Task
import os
import mrpipe.Toolboxes
from typing import List
from mrpipe.Helper import Helper
from mrpipe.meta.PathCollection import PathCollection
from mrpipe.meta.PathClass import Path
from mrpipe.meta import LoggerModule
logger = LoggerModule.Logger()

class LSTAI(Task):

    def __init__(self, t1w: Path, flair: Path, inputDir: Path, outputDir: Path, tempDir: Path, outputFiles: List[Path], lstaiSIF, name: str = "lstai", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.t1w = t1w
        self.flair = flair
        self.inputDir = inputDir
        self.outputDir = outputDir
        self.outputFiles = outputFiles
        self.tempDir = tempDir
        self.lstaiSIF = lstaiSIF


        #add input and output images
        self.addInFiles([self.t1w, self.flair])
        self.addOutFiles([self.outputFiles])

    def getCommand(self):
        if self._createDirs():
            command = "singularity run --nv " + \
                f"-B {self.inputDir}:/custom_apps/lst_input " + \
                f"-B {self.outputDir}:/custom_apps/lst_output " + \
                f"-B {self.tempDir}:/custom_apps/lst_temp " + \
                f"{self.lstaiSIF} " + \
                f"--t1 /custom_apps/lst_input/{self.T1wInputSymlink.get_filename()} " + \
                f"--flair /custom_apps/lst_input/{self.flairInputSymlink.get_filename()} " + \
                "--output /custom_apps/lst_output " + \
                "--temp /custom_apps/lst_temp " + \
                "--probability_map"
            return command
        else:
            return None

    def _createDirs(self):
        self.inputDir.create()
        self.outputDir.create()
        self.tempDir.create()
        for path in self.outFiles:
            path.createDirectory()
        self.T1wInputSymlink = self.t1w.createSymLink(self.inputDir.join(self.t1w.get_filename()))
        self.flairInputSymlink = self.flair.createSymLink(self.inputDir.join(self.flair.get_filename()))
        if self.T1wInputSymlink is None or self.flairInputSymlink is None:
            return False
        else:
            return True




