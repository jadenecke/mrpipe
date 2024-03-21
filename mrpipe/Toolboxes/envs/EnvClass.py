from mrpipe.Helper import Helper
from typing import List

class EnvClass:
    def __init__(self, modules=[], condaEnv:str = "mrpipe", purgeModules=True,
                 defaultModules=["singularity/3.6.1", "anaconda3/2020-07"], singularityBindPaths:List[str] = [],
                 cudaExtraPaths:List[str] = [], path:List[str] = None):
        #this class must have default parameter for every single one of its arguments
        self.modules = Helper.ensure_list(modules)
        self.condaEnv = condaEnv
        self.purgeModules = purgeModules
        if defaultModules:
            self.modules = self.modules + defaultModules
        self.singularityBindPaths = Helper.ensure_list(singularityBindPaths)
        self.cudaExtraPaths = Helper.ensure_list(cudaExtraPaths)
        self.path = Helper.ensure_list(path)

    def _getModules(self):
        return [f'module load {m}' for m in self.modules]

    def _getCondaEnv(self):

        return ["active_env=$(conda info | grep 'active environment' | cut -d ':' -f 2 | xargs)",
                """if [ "$active_env" == "None" ]; then conda activate base; fi""",
                f'source activate {self.condaEnv}']

    def _getSingularityBindPaths(self):
        return [f'SINGULARITY_BINDPATH=${{SINGULARITY_BINDPATH}}:{path}' for path in self.singularityBindPaths]

    def _getcudaExtraPaths(self):
        return [f'LD_LIBRARY_PATH=$LD_LIBRARY_PATH:{path}' for path in self.cudaExtraPaths]

    def getSetup(self):
        setupLines = []

        #modules
        if self.purgeModules:
            setupLines += ["module purge"]
        setupLines += self._getModules()
        setupLines += ["module list"]

        # conda
        setupLines += ["source deactivate"]
        setupLines += self._getCondaEnv()

        #Path Variable
        if self.path is not None:
            for path in self.path:
                setupLines += [f"export PATH=$PATH:{path}"]

        #singularity extra paths
        if self.singularityBindPaths:
            setupLines += self._getSingularityBindPaths()
            setupLines += ["echo $SINGULARITY_BINDPATH"]

        #cuda
        if self.cudaExtraPaths:
            setupLines += self._getcudaExtraPaths()
            setupLines += ["echo $LD_LIBRARY_PATH"]
            setupLines += ["nvidia-smi"]

        setupLines.reverse()
        return setupLines

