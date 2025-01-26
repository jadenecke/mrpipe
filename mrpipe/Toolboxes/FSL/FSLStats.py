from mrpipe.Toolboxes.Task import Task
from mrpipe.Helper import Helper
from typing import List
import os
from mrpipe.meta.PathClass import StatsFilePath
from mrpipe.meta.PathClass import Path

"""
Pre Options:
preoption -json: output in JSON format to standard out
preoption -t will give a separate output line for each 3D volume of a 4D timeseries
preoption -K < indexMask > will generate seperate n submasks from indexMask, for indexvalues 1..n where n is the maximum index value in indexMask, and generate statistics for each submask

Options:
-l <lthresh> : set lower threshold
-u <uthresh> : set upper threshold
-r           : output <robust min intensity> <robust max intensity>
-R           : output <min intensity> <max intensity>
-e           : output mean entropy ; mean(-i*ln(i))
-E           : output mean entropy (of nonzero voxels)
-v           : output <voxels> <volume>
-V           : output <voxels> <volume> (for nonzero voxels)
-m           : output mean
-M           : output mean (for nonzero voxels)
-s           : output standard deviation
-S           : output standard deviation (for nonzero voxels)
-w           : output smallest ROI <xmin> <xsize> <ymin> <ysize> <zmin> <zsize> <tmin> <tsize> containing nonzero voxels
-x           : output co-ordinates of maximum voxel
-X           : output co-ordinates of minimum voxel
-c           : output centre-of-gravity (cog) in mm coordinates
-C           : output centre-of-gravity (cog) in voxel coordinates
-p <n>       : output nth percentile (n between 0 and 100)
-P <n>       : output nth percentile (for nonzero voxels)
-a           : use absolute values of all image intensities
-n           : treat NaN or Inf as zero for subsequent stats
-k <mask>    : use the specified image (filename) for masking - overrides lower and upper thresholds
-d <image>   : take the difference between the base image and the image specified here
-h <nbins>   : output a histogram (for the thresholded/masked voxels only) with nbins
-H <nbins> <min> <max>   : output a histogram (for the thresholded/masked voxels only) with nbins and histogram limits of min and max
"""

class FSLStats(Task):
    def __init__(self, infile: Path, output: StatsFilePath, options: List[str], mask: Path = None,
                 preoptions: List[str] = None, name: str = "FSLStats", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.inputImage = infile
        self.options = Helper.ensure_list(options, flatten=True)
        if preoptions is None:
            self.preOptions = []
        else:
            self.preOptions = Helper.ensure_list(preoptions, flatten=True)
        self.outputFile = output
        self.mask = mask

        #add input and output images
        self.addInFiles([self.inputImage])
        if self.mask is not None:
            self.addInFiles([self.mask])
        self.addOutFiles(self.outputFile)

    def getCommand(self):
        appendToJSON_scriptPath = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "appendToJSON.py")
        command = f"python3 {appendToJSON_scriptPath} {self.outputFile.path} {self.outputFile.attributeName} $(fslstats"
        for opt in self.preOptions:
            command += f" {opt}"
        command += f" {self.inputImage.path}"
        for opt in self.options:
            if opt == "-k":
                command += f" -k {self.mask.path}"
            elif opt == "-V":
                command += " -V  | awk '{print $2}'"
                break
            else:
                command += f" {opt}"
        command += " )"
        return command


class FSLStatsToFile(Task):
    def __init__(self, infile: Path, output: Path, options: List[str], mask: Path = None,
                 preoptions: List[str] = None, name: str = "FSLStatsToFile", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.inputImage = infile
        self.options = Helper.ensure_list(options, flatten=True)
        if preoptions is None:
            self.preOptions = []
        else:
            self.preOptions = Helper.ensure_list(preoptions, flatten=True)
        self.outputFile = output
        self.mask = mask

        #add input and output images
        self.addInFiles([self.inputImage])
        if self.mask is not None:
            self.addInFiles([self.mask])
        self.addOutFiles(self.outputFile)

    def getCommand(self):
        command = f"fslstats"
        for opt in self.preOptions:
            command += f" {opt}"
        command += f" {self.inputImage.path}"
        for opt in self.options:
            if opt == "-k":
                command += f" -k {self.mask.path}"
            elif opt == "-V":
                command += " -V  | awk '{print $2}'"
                break
            else:
                command += f" {opt}"
        command += f" > {self.outputFile}"
        return command



class FSLStatsWithCenTauRZ(Task):
    def __init__(self, infile: Path, output: StatsFilePath, tracer: str, centaurMask: str, options: List[str], mask: Path = None,
                 preoptions: List[str] = None, name: str = "FSLStats", clobber=False):
        super().__init__(name=name, clobber=clobber)
        self.inputImage = infile
        self.tracer = tracer
        self.centaurMask = centaurMask
        self.options = Helper.ensure_list(options, flatten=True)
        if preoptions is None:
            self.preOptions = []
        else:
            self.preOptions = Helper.ensure_list(preoptions, flatten=True)
        self.outputFile = output
        self.mask = mask

        #add input and output images
        self.addInFiles([self.inputImage])
        if self.mask is not None:
            self.addInFiles([self.mask])
        self.addOutFiles(self.outputFile)

    def getCommand(self):
        appendToJSON_scriptPath = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "appendToJSON.py")
        suvrToCenTauRZ_scriptPath = os.path.join(Helper.get_libpath(), "Toolboxes", "submodules", "custom", "SUVRToCenTauRZ.R")
        command = f"python3 {appendToJSON_scriptPath} {self.outputFile.path} {self.outputFile.attributeName} $(fslstats"
        for opt in self.preOptions:
            command += f" {opt}"
        command += f" {self.inputImage.path}"
        for opt in self.options:
            if opt == "-k":
                command += f" -k {self.mask.path}"
            elif opt == "-V":
                command += " -V  | awk '{print $2}'"
                break
            else:
                command += f" {opt}"
        command += " | xargs -I {}"
        command += f" {suvrToCenTauRZ_scriptPath}"
        command += " -i {}"
        command += f" -t {self.tracer} -m {self.centaurMask})"
        return command

