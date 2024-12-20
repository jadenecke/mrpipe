from mrpipe.meta.PathCollection import PathCollection
from mrpipe.meta.PathClass import Path

class LibPaths(PathCollection):
    def __init__(self,
                 libcudnn="/path/to/libcudnn",
                 sti_suite="/path/to/STISuite",
                 medi_toolbox="/path/to/MEDI_toolbox",
                 matlab_onnx="/path/to/matlab_onnx",
                 matlab_ToolsForNifti="/path/to/matlab_ToolsForNifti"):
        self.libcudnn = Path(libcudnn, isDirectory=True)
        self.sti_suite = Path(sti_suite, isDirectory=True)
        self.medi_toolbox = Path(medi_toolbox, isDirectory=True)
        self.matlab_onnx = Path(matlab_onnx, isDirectory=True)
        self.matlab_ToolsForNifti=Path(matlab_ToolsForNifti, isDirectory=True)


