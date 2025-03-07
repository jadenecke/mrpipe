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
                 shivaiSIF = "/path/to/shivai.sif",
                 shivaiModelDir = "/path/to/shivaiModelDir",
                 shivaiConfig = "/path/to/shivaiConfig.yml"):
        self.libcudnn = Path(libcudnn, isDirectory=True)
        self.sti_suite = Path(sti_suite, isDirectory=True)
        self.medi_toolbox = Path(medi_toolbox, isDirectory=True)
        self.chiSepToolbox = Path(chiSepToolbox, isDirectory=True)
        self.matlab_onnx = Path(matlab_onnx, isDirectory=True)
        self.matlab_ToolsForNifti = Path(matlab_ToolsForNifti, isDirectory=True)
        self.lstai_singularityContainer = lstai_singularityContainer
        self.clearswi_singularityContainer = clearswi_singularityContainer
        self.antspynet_singularityContainer = antspynet_singularityContainer
        self.shivaiSIF = shivaiSIF
        self.shivaiModelDir = shivaiModelDir
        self.shivaiConfig = shivaiConfig


