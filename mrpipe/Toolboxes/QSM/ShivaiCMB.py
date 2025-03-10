from mrpipe.Toolboxes.Task import Task
import os
import mrpipe.Toolboxes
from typing import List
from mrpipe.meta.PathClass import Path
from mrpipe.meta import LoggerModule
logger = LoggerModule.Logger()

class ShivaiCMB(Task):

    #Note:
    # Running shiva


    def __init__(self, subSesString: str, swi: Path, t1: Path, segmentation: Path, tempInDir: Path, outputDir: Path, outputFiles: List[Path], shivaiSIF: Path, shivaiModelDir: Path,
                 shivaiConfig: Path, predictionType="CMB", ncores=1, name: str = "shivaiCMB", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.subSesString = subSesString
        self.swi = swi
        self.t1 = t1
        self.segmentation = segmentation
        self.tempInDir = tempInDir
        self.shivaiSIF = shivaiSIF
        self.outputDir = outputDir
        self.outputFiles = outputFiles
        self.shivaiModelDir = shivaiModelDir
        self.shivaiConfig = shivaiConfig
        self.predictionType = predictionType
        self.ncores = ncores
        self.command = ""

        #add input and output images
        self.addInFiles([self.swi, self.t1, self.segmentation])
        self.addOutFiles([self.outputFiles])

    def getCommand(self):
        self.createDirStructure()
        #self.addCleanup("rm -rv " + str(self.tempInDir))
        command = "singularity run --nv " + \
                  f"--bind {self.shivaiModelDir}:/mnt/model:ro " + \
                  f"--bind {self.tempInDir}:/mnt/data/input:ro " + \
                  f"--bind {self.outputDir}:/mnt/data/output " + \
                  f"--bind {self.shivaiConfig.get_directory()}:/mnt/config:ro " + \
                  f"{self.shivaiSIF} shiva " + \
                  "--in /mnt/data/input " + \
                  "--out /mnt/data/output " + \
                  "--prediction CMB " + \
                  f"--config /mnt/config/{self.shivaiConfig.get_filename()} " + \
                  "--input_type standard " + \
                  "--run_plugin Linear " + \
                  "--remove_intermediates " + \
                  f"--ai_threads {self.ncores} " + \
                  "--brain_seg custom " + \
                  "--use_t1"
        return command

    def createDirStructure(self):
        self.tempInDir.createDirectory()
        subDir = self.tempInDir.join(self.subSesString)
        subDir.createDirectory()
        t1Dir = subDir.join("t1")
        t1Dir.createDirectory()
        self.t1.createSymLink(t1Dir.join(self.subSesString + "_T1" + self.t1.get_filetype()))
        swiDir = subDir.join("swi")
        swiDir.createDirectory()
        self.swi.createSymLink(swiDir.join(self.subSesString + "_SWI" + self.swi.get_filetype()))
        segDir = subDir.join("seg")
        segDir.createDirectory()
        self.segmentation.createSymLink(segDir.join(self.subSesString + "_seg" + self.segmentation.get_filetype()))


# singularity run --nv --bind /cluster2/Forks_n_Stuff/SHiVAi/models:/mnt/model:ro,
# /cluster/chiSepTestNew/shivai:/mnt/data/input:ro,
# /cluster/jdenecke/chiSepTestNew/shivai_out:/mnt/data/output,
# /cluster2/Forks_n_Stuff/SHiVAi/apptainer:/mnt/config:ro
# /cluster2/singularityContainer/shivai/shivai_latest.sif
# shiva --in /mnt/data/input --out /mnt/data/output
# --prediction CMB --config /mnt/config/config_example.yml
# --input_type standard --run_plugin Linear --keep_all --ai_threads 8 --brain_seg custom --use_t1




