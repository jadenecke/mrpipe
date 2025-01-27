from mrpipe.Toolboxes.envs import EnvClass
from mrpipe.modalityModules.PathDicts.LibPaths import LibPaths
import os
import mrpipe.Toolboxes

class Envs:
    def __init__(self, libPaths: LibPaths):
        #catch library Paths
        self.libPaths = libPaths

        #create Environments to call
        self.envMRPipe = EnvClass.EnvClass(condaEnv="mrpipe")
        #TODO change ants, and re-implement center of mass for pet images
        self.envANTS = EnvClass.EnvClass(modules="ants/2.3.4", condaEnv="mrpipe") # ants >= 2.3.5 is sensitive because this switched from using qform standard to sform standard which interacts with recenterToCOM because that one only (correctly) changes the sform but not the qform.
        self.envHDBET = EnvClass.EnvClass(modules="cuda/10.0", condaEnv=os.path.abspath(os.path.join(os.path.dirname(mrpipe.Toolboxes.__file__), os.pardir, os.pardir, "venv", "hdbet")),
                                          cudaExtraPaths=self.libPaths.libcudnn)
        self.envSynthSeg = EnvClass.EnvClass(modules="cuda/10.0", condaEnv=os.path.abspath(os.path.join(os.path.dirname(mrpipe.Toolboxes.__file__), os.pardir, os.pardir, "venv", "synthseg")),
                                          cudaExtraPaths=self.libPaths.libcudnn,
                                          path=[os.path.join(os.path.abspath(os.path.dirname(mrpipe.Toolboxes.__file__)),
                                                            "submodules", "synthseg")])
        self.envFSL = EnvClass.EnvClass(modules="fsl/6.0.3", condaEnv="mrpipe")
        self.envR = EnvClass.EnvClass(modules="R/4.0.0", condaEnv="mrpipe")
        self.envFSL_R = EnvClass.EnvClass(modules=["R/4.0.0", "fsl/6.0.3"], condaEnv="mrpipe")
        self.envQCVis = EnvClass.EnvClass(modules=["fsl/6.0.3", "R/4.0.0"], condaEnv="mrpipe")
        self.envSPM12 = EnvClass.EnvClass(modules=["matlab/R2023a"], condaEnv="mrpipe")
        self.envChiSep = EnvClass.EnvClass(modules=["matlab/R2023a", "romeo/3.2.8"], condaEnv="mrpipe")
        self.envSingularity = EnvClass.EnvClass(modules=["singularity/3.6.1"], condaEnv="mrpipe")
