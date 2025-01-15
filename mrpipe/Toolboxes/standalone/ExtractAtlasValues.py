from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.PathClass import Path
from mrpipe.Helper import Helper
import os

"""
option_list = list(
  make_option(c("-i", "--in_file"), type="character", default=NA, 
              help="Image file name", metavar="image.nii.gz"),
  make_option(c("-a", "--atlas"), type="character", default=NA, 
              help="Atlas file name", metavar="atlas.nii.gz"),
  make_option(c("-f", "--func"), type="character", default="mean", 
              help="Function to summarize regional values, defaults to mean", metavar="mean"),
  make_option(c("-o", "--out"), type="character", default=NA, 
              help="output file name", metavar="values.csv"),
  make_option(c("-d", "--dots"), type="character", default=NA, 
              help="additional parameter passed to the function call, seperated by spaces and quoted: arg1=val1 arg2=val2", metavar="..."),
  make_option(c("-z", "--keepZeroes"), type="logical", default=FALSE, action="store_true",
              help="Whether to keep zeroes values (usually background) within roi before applying `func`", metavar="FALSE"),
  make_option(c("-n", "--NAtoZero"), type="logical", default=FALSE, action="store_true",
              help="Whether to replace NA values (usually background) with zeroes. Will affect `func` calculation if `--keepZeroes` is also specified.", metavar="FALSE"),            
  make_option(c("-m", "--mask"), type="character", default=NA, 
              help="Mask that is applied to atlas beforehand, e.g. if images were masked themselfs.", metavar="...")
)
"""

class ExtractAtlasValues(Task):

    def __init__(self, infile: Path, atlas: Path, outfile: Path, func: str = "mean", dots: str = None, keep_zeroes: bool = False, na_to_zero: bool = False,
                 mask: Path = None, name="ExtractAtlasValues", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.infile = infile
        self.outfile = outfile
        self.atlas = atlas
        self.func = func
        self.dots = dots
        self.keep_zeroes = keep_zeroes
        self.na_to_zero = na_to_zero
        self.mask = mask

        # add input and output images
        self.addInFiles([self.infile, self.atlas])
        self.addOutFiles([self.outfile])
        if self.mask:
            self.addInFiles([self.mask])

    def getCommand(self):
        command = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "extractAtlasValues.R")
        command += f" -i {self.infile}"
        command += f" -a {self.atlas}"
        command += f" -f {self.func}"
        command += f" -o {self.outfile}"
        if self.dots:
            command += f" -d {self.dots}"
        if self.keep_zeroes:
            command += f" --keepZeroes"
        if self.na_to_zero:
            command += f" --NAtoZero"
        if self.mask:
            command += f" --mask {self.mask}"

        return command


