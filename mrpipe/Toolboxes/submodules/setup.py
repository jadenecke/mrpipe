import os.path
from mrpipe.Helper import Helper
from mrpipe.meta import LoggerModule

logger = LoggerModule.Logger()

@staticmethod
def setup_submodules():
    logger.debug("Setting up submodules")
    # setup cat12 in spm12
    logger.debug("Checking for Cat12 symlink within SPM12 toolbox directory")
    cat12_dir = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "cat12")
    cat12_in_spm12_dir = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "spm12", "toolbox", "cat12")
    if not os.path.isdir(cat12_in_spm12_dir):
        logger.process("Setting up cat12 symlink within SPM12 toolbox directory")
        os.symlink(cat12_dir, cat12_in_spm12_dir)


