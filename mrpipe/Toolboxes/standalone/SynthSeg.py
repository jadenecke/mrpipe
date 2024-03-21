from mrpipe.Toolboxes.Task import Task
import os
import mrpipe.Toolboxes
from mrpipe.Helper import Helper
from mrpipe.meta.PathCollection import PathCollection
from mrpipe.meta.PathClass import Path
from mrpipe.meta import LoggerModule
logger = LoggerModule.Logger()


class SynthSeg(Task):

    def __init__(self, infile, posterior, posteriorProb, volumes, resample, qc, useGPU=False, ncores=1, name: str = "synthseg", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.ncores = ncores
        self.inputImage = infile
        self.outputPosterior = posterior
        self.outputPosteriorProb = posteriorProb
        self.outputVolumes = volumes
        self.outputResample = resample
        self.outputQC = qc
        self.useGPU = useGPU
        self.command = os.path.join(os.path.abspath(os.path.dirname(mrpipe.Toolboxes.__file__)), "submodules", "synthseg", "scripts", "commands", "SynthSeg_predict.py")

        #add input and output images
        self.addInFiles([infile])
        self.addOutFiles([self.outputPosterior, self.outputPosteriorProb, self.outputVolumes, self.outputResample, self.outputQC])

    def getCommand(self):
        command = f"python {self.command} --i {self.inputImage} --o {self.outputPosterior} --post {self.outputPosteriorProb} --resample {self.outputResample} --vol {self.outputVolumes} --qc {self.outputQC}"
        if not self.useGPU:
            command += f" --cpu --threads {self.ncores}"
        return command


    @staticmethod
    def extract_structure_names():
        # filepath to label text file
        fp = os.path.join(os.path.abspath(os.path.dirname(mrpipe.Toolboxes.__file__)), "submodules", "synthseg", "data", "labels table.txt")

        # Open the file
        with open(fp, 'r') as file:
            # Read the lines
            lines = file.readlines()

        # Initialize an empty list to store the structure names
        structure_names = []

        # Iterate over each line
        for line in lines:
            # Split the line into words
            if not line:
                continue
            words = line.split()

            # If the first word is a digit (i.e., a label), add the structure name to the list
            if len(words) > 1:
                if words[0].isdigit():
                    structure_names.append(Helper.clean('_'.join(words[1:])))

        # Return the list of structure names
        return structure_names

    class PosteriorPaths(PathCollection):
        def __init__(self, basename):
            for name in SynthSeg.extract_structure_names():
                setattr(self, name, Path(basename + f"_SynthSegProb_{name}.nii.gz"))

        def getAllPaths(self):
            resList = []
            for key, value in self.__dict__.items():
                resList.append(value)
            return resList
