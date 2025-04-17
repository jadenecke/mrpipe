from mrpipe.Toolboxes.Task import Task
import os
import mrpipe.Toolboxes
from mrpipe.Helper import Helper
from mrpipe.meta.PathCollection import PathCollection
from mrpipe.meta.PathClass import Path
from mrpipe.meta import LoggerModule
from mrpipe.meta.PathClass import NiftiFilePath
from mrpipe.meta.PathClass import StatsFilePath
logger = LoggerModule.Logger()


class SynthSeg(Task):

    def __init__(self, infile: Path, posterior: Path, posteriorProb: Path, volumes: Path, resample: Path, qc: Path, useGPU=False, ncores=1, name: str = "synthseg", clobber=False):
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
        #TODO fix that casting later and define all appropriate Paths to be niftiFilePaths

        command = f"python {self.command} --i {self.inputImage} --o {self.outputPosterior} --post {self.outputPosteriorProb} "
        #Synthseg will not create outputResample if the input image Resolution is 1mm isotropic, even if you ask for it. Therefore if the input is 1mm Iso, just copy it to resampled image.
        # niiPath = NiftiFilePath(path=self.inputImage, shouldExist=True, isDirectory=False)
        # voxelSize = niiPath.get_voxelsize()
        # if all([v == 1 for v in voxelSize]): #TODO: see whether this causes problems or synthseg overwrites it if necessary.
        self.inputImage.createSymLink(self.outputResample)
        #else:
        command += f"--resample {self.outputResample} "
        command += f"--vol {self.outputVolumes} --qc {self.outputQC} "
        if not self.useGPU:
            command += f"--cpu --threads {self.ncores}"
        return command


    @staticmethod
    def extract_structure_names():
        # filepath to label text file
        fp = os.path.join(os.path.abspath(os.path.dirname(mrpipe.Toolboxes.__file__)), "submodules", "synthseg", "data", "labels table.txt")

        # Open the file
        with open(fp, 'r') as file:
            # Read the lines
            lines = file.readlines()

        structDict = {}

        # Iterate over each line
        for line in lines:
            # Split the line into words
            if not line:
                continue
            words = line.split()

            # If the first word is a digit (i.e., a label), add the structure name to the list
            if len(words) > 1:
                if words[0].isdigit():
                    structDict[Helper.clean('_'.join(words[1:]))] = int(words[0])

        # Return the list of structure names
        return sorted(structDict, key=structDict.get)

    class PosteriorPaths(PathCollection):
        def __init__(self, basename):
            #TODO This behavior to save the order in which names were added to make sure they are recieved in the order they were added does work, however it will break if the Paths are yamld and read from disk again (I think).
            self.names = []
            for name in SynthSeg.extract_structure_names():
                setattr(self, name, Path(basename + f"_SynthSegProb_{name}.nii.gz"))
                self.names.append(name)

        def getAllPaths(self):
            return [getattr(self, name) for name in self.names]

