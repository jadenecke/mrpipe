import re
from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.PathClass import Path
from mrpipe.meta.ImageSeries import DWI


class Tractseg(Task):

    def __init__(self, inputPeaks: DWI, outputDir: Path, outputType: "str", mask: Path,  session, name: str = "tractseg", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputPeaks = inputPeaks
        self.outputDir = outputDir
        self.outputType = outputType
        self.mask = mask

        valid_output_type = ["tract_segmentation", "endings_segmentation", "TOM"]
        if not any(re.match(pattern=p, string=self.outputType) for p in valid_output_type):
            raise ValueError(f"Invalid input. Expected one of {valid_output_type}. Got {type}")


        #add input and output images
        self.addInFiles([self.inputPeaks, self.mask])
        self.addOutFiles(Tractseg.get_expected_output_files(self.outputDir, self.outputType))

    def getCommand(self):
        cpusPerTask = getattr(self.parent, "SLURM_cpusPerTask", None)

        command = f"TractSeg -i {self.inputPeaks} -o {self.outputDir} --brain_mask {self.mask} --output_type {self.outputType}"
        if cpusPerTask:
            command += f" --nr_cpus {cpusPerTask}"
        return command

    @staticmethod
    def get_expected_output_files(outputdir, outputType):
        tcklist = [
            "AF_left",
            "AF_right",
            "ATR_left",
            "ATR_right",
            "CA",
            "CC_1",
            "CC_2",
            "CC_3",
            "CC_4",
            "CC_5",
            "CC_6",
            "CC_7",
            "CC",
            "CG_left",
            "CG_right",
            "CST_left",
            "CST_right",
            "FPT_left",
            "FPT_right",
            "FX_left",
            "FX_right",
            "ICP_left",
            "ICP_right",
            "IFO_left",
            "IFO_right",
            "ILF_left",
            "ILF_right",
            "MCP",
            "MLF_left",
            "MLF_right",
            "OR_left",
            "OR_right",
            "POPT_left",
            "POPT_right",
            "SCP_left",
            "SCP_right",
            "SLF_I_left",
            "SLF_I_right",
            "SLF_II_left",
            "SLF_II_right",
            "SLF_III_left",
            "SLF_III_right",
            "ST_FO_left",
            "ST_FO_right",
            "ST_OCC_left",
            "ST_OCC_right",
            "ST_PAR_left",
            "ST_PAR_right",
            "ST_POSTC_left",
            "ST_POSTC_right",
            "ST_PREC_left",
            "ST_PREC_right",
            "ST_PREF_left",
            "ST_PREF_right",
            "ST_PREM_left",
            "ST_PREM_right",
            "STR_left",
            "STR_right",
            "T_OCC_left",
            "T_OCC_right",
            "T_PAR_left",
            "T_PAR_right",
            "T_POSTC_left",
            "T_POSTC_right",
            "T_PREC_left",
            "T_PREC_right",
            "T_PREF_left",
            "T_PREF_right",
            "T_PREM_left",
            "T_PREM_right",
            "UF_left",
            "UF_right"
        ]
        if outputType == "tract_segmentation":
            return [outputdir.join("bundle_segmentations").join(tck + ".nii.gz") for tck in tcklist]
        if outputType == "TOM":
            return [outputdir.join("TOM").join(tck + ".nii.gz") for tck in tcklist]
        if outputType == "endings_segmentation":
            return [[outputdir.join("endings_segmentations").join(tck + "_b.nii.gz"),
                     outputdir.join("endings_segmentations").join(tck + "_e.nii.gz")] for tck in tcklist]
        if outputType == "tck":
            return [outputdir.join("TOM_trackings").join(tck + ".tck") for tck in tcklist]
        return None



