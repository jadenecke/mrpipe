from typing import List

from mrpipe.Toolboxes.Task import Task
from mrpipe.Toolboxes.standalone.Tractseg import Tractseg
from mrpipe.meta.PathClass import Path
from mrpipe.meta.ImageSeries import DWI
from mrpipe.Toolboxes.MRtrix3.dwiextract import DWIEXTRACTFIRSTB0
from mrpipe.meta.Session import Session


class Tracking(Task):

    def __init__(self, inputPeaks: DWI, outputDir: Path,   session, name: str = "Tracking", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputPeaks = inputPeaks
        self.outputDir = outputDir

        #add input and output images
        self.addInFiles([self.inputPeaks,
                         Tractseg.get_expected_output_files(self.outputDir, "tract_segmentation"),
                         Tractseg.get_expected_output_files(self.outputDir, "endings_segmentation"),
                         Tractseg.get_expected_output_files(self.outputDir, "TOM")])
        self.addOutFiles(self.addOutFiles(Tractseg.get_expected_output_files(self.outputDir, "tck")))

    def getCommand(self):
        cpusPerTask = getattr(self.parent, "SLURM_cpusPerTask", None)
        command = f"Tracking -i {self.inputPeaks} -o {self.outputDir}  --tracking_format tck --nr_fibers 10000"
        if cpusPerTask:
            command += f" --nr_cpus {cpusPerTask}"
        return command





