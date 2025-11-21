from mrpipe.meta.PathCollection import PathCollection
from mrpipe.meta.PathClass import Path
from mrpipe.Helper import Helper
import os

class LibPaths(PathCollection):
    def __init__(self,
                 libcudnn="/path/to/libcudnn",
                 sti_suite="/path/to/STISuite",
                 medi_toolbox="/path/to/MEDI_toolbox",
                 matlab_onnx="/path/to/matlab_onnx",
                 matlab_ToolsForNifti="/path/to/matlab_ToolsForNifti",
                 chiSepToolbox=os.path.join(Helper.get_libpath(), "mrpipe", "Toolboxes", "submodules", "chi-separation", "Chisep_Toolbox_v1.1.3"),
                 lstai_singularityContainer = "/path/to/lstair_singularityContainer.sif",
                 clearswi_singularityContainer = "/path/to/clearswi_singularityContainer.sif",
                 antspynet_singularityContainer = "/path/to/antspynet_singularityContainer.sif",
                 shivaiSIF = "/path/to/shivai_0.4.2.sif",
                 shivaiSIFLatest="/path/to/shivai_latest.sif",
                 shivaiModelDir = "/path/to/shivaiModelDir",
                 shivaiConfig = "/path/to/shivaiConfig.yml",
                 MarsWMHSIF = "/path/to/MarsWMHSIF.sif",
                 MarsBrainstemSIF = "/path/to/MarsBrainstemSIF.sif",
                 PINGUPVSSif = "/path/to/PINGUPVSSif.sif"):
        self.libcudnn = Path(libcudnn, isDirectory=True, shouldExist=True)
        self.sti_suite = Path(sti_suite, isDirectory=True, shouldExist=True)
        self.medi_toolbox = Path(medi_toolbox, isDirectory=True, shouldExist=True)
        self.chiSepToolbox = Path(chiSepToolbox, isDirectory=True, shouldExist=True)
        self.matlab_onnx = Path(matlab_onnx, isDirectory=True, shouldExist=True)
        self.matlab_ToolsForNifti = Path(matlab_ToolsForNifti, isDirectory=True, shouldExist=True)
        self.lstai_singularityContainer = Path(lstai_singularityContainer, isDirectory=False, shouldExist=True)
        self.clearswi_singularityContainer = Path(clearswi_singularityContainer, isDirectory=False, shouldExist=True)
        self.antspynet_singularityContainer = Path(antspynet_singularityContainer, isDirectory=False, shouldExist=True)
        self.shivaiSIF = Path(shivaiSIF, isDirectory=False, shouldExist=True)
        self.shivaiSIFLatest = Path(shivaiSIFLatest, isDirectory=False, shouldExist=True)
        self.shivaiModelDir = Path(shivaiModelDir, isDirectory=True, shouldExist=True)
        self.shivaiConfig = Path(shivaiConfig, isDirectory=False, shouldExist=True)
        self.MarsWMHSIF = Path(MarsWMHSIF, isDirectory=False, shouldExist=True)
        self.MarsBrainstemSIF = Path(MarsBrainstemSIF, isDirectory=False, shouldExist=True)
        self.PINGUPVSSif = Path(PINGUPVSSif, isDirectory=False, shouldExist=True)


