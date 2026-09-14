from mrpipe.Toolboxes.Task import Task
from mrpipe.meta.PathClass import Path, StatsFilePath
from mrpipe.meta.ImageSeries import DWI
from mrpipe.Toolboxes.MRtrix3.dwiextract import DWIEXTRACTFIRSTB0, DWIEXTRACTFIRSTB0FromNifti
from mrpipe.meta.Session import Session


class B0FORTOPUP(Task):

    def __init__(self, inputDWI: DWI, inputT1w: Path, inputB0: Path, Synb0WrapperPath: Path, outputB0: Path, synthB0DiscoSIF: Path, acqparams_eddy: Path, acqparams_topup: Path, index: Path,
                 freesurferLicense: Path, temp_dir: Path, session, topupCorrectionMethod: StatsFilePath, name: str = "generateB0ForTopup", clobber=False):
        super().__init__(name=name, clobber=clobber, session=session)
        self.inputDWI = inputDWI
        self.inputT1w = inputT1w
        self.outputB0 = outputB0
        self.inputB0 = inputB0
        self.temp_dir = temp_dir
        self.synthB0DiscoSIF = synthB0DiscoSIF
        self.acqparams_topup = acqparams_topup
        self.acqparams_eddy = acqparams_eddy
        self.freesurferLicense = freesurferLicense
        self.index = index
        self.Synb0WrapperPath = Synb0WrapperPath
        self.topupCorrectionMethod = topupCorrectionMethod

        self.inputSynb0Dir = self.temp_dir.join("INPUT", isDirectory=True)
        self.outputSynb0Dir = self.temp_dir.join("OUTPUT", isDirectory=True)

        #add input and output images
        self.addInFiles([self.inputT1w, self.inputDWI.get_image_sidecar(), self.inputDWI.getImagepath(), self.inputDWI.get_bvec_path(), self.inputDWI.get_bval_path(), self.inputB0])
        self.addOutFiles([self.outputB0, self.index, self.topupCorrectionMethod, self.acqparams_eddy, self.acqparams_topup]) #TODO eventually add back self.acqparams_eddy and self.acqparams_topup but leave out for now so its not reprocessed

        """
        From FSL: only use on pair of b0, not all:
        https://fsl.fmrib.ox.ac.uk/fsl/docs/diffusion/topup/users_guide/index.html#what-data-to-acquire-in-order-to-use-topup
        All you need is two images acquired with opposing PE-direction (also known as "different polarity PE-blips" or even "blip-up-blip-down data"). 
        This would typically be two images, i.e. two SE-EPI images. When the purpose of estimating the off-resonance field is to apply it to a diffusion data set it is 
        very strongly recommended that the first of those two images is the first image of the full diffusion data set. If that image is used as the first image in
        the 4D --imain image file in topup, and is the first image in the --imain image file in eddy, the resulting fieldmap will automatically be perfectly aligned
        with the diffusion data when running eddy.
        
        We further recommend that one acquires more than just one each (we usually suggest getting three) of the two acquisitions with opposing PE-directions.
        The reason for that is to have "spares" in case the subject happens to make a sudden movement during the acquisition of one of the volumes (intra-volume movement).
        If that happens, and that is the only volume one has acquired with that PE-direction, it may not be possible to estimate the field and the whole diffusion data
        set may need to be discarded. So a good protocol would be to acquire three volumes with one PE-direction followed by a full diffusion data set,
        starting with three volumes, with opposing PE-direction.
        
        We typically don't recommend passing more than a single pair to topup though. The examples with more than one pair in this manual is more to exemplify what is possible.
        Also, before we had extensive experience of running topup we assumed that more than one pair would help with robustness.
        As it turns out it doesn't seem to make any difference, and only means that topup takes longer to run.
        But on the other hand it doesn't seem to make any harm to use more than one pair, save for longer execution time.
        """

    def makeSynb0Dir(self):
        self.inputSynb0Dir.createDirectory()
        self.outputSynb0Dir.createDirectory()
        self.inputT1w.createSymLink(self.inputSynb0Dir.join("T1.nii.gz"))
        self.inputB0.createSymLink(self.inputSynb0Dir.join("b0.nii.gz"))
        self.acqparams_topup.createSymLink(self.inputSynb0Dir.join("acqparams.nii.gz"))

    def getCommand(self):
        self.inputDWI.createAcqpramAndIndex(self.acqparams_topup, self.acqparams_eddy, self.index)
        cpusPerTask = getattr(self.parent, "SLURM_cpusPerTask", None)
        if self.inputDWI.image_reverse and self.inputDWI.contains_b0_reverse:
            self.topupCorrectionMethod.writeValue("Reverse_PE_Available")
            # return "sleep 0.1"
            command = DWIEXTRACTFIRSTB0FromNifti.dwiextractFirstB0FromNifti(inputImage=self.inputDWI.image_reverse.imagePath,
                                                                   inputBval=self.inputDWI.bval_reverse,
                                                                   inputBvec=self.inputDWI.bvec_reverse,
                                                                   inputJson=self.inputDWI.image_reverse.jsonPath,
                                                                   outputB0=self.outputB0,
                                                                   clobber=self.clobber,
                                                                   ncpus=cpusPerTask)
            return command
        else:
            self.topupCorrectionMethod.writeValue("used_SynB0Disco")
            # return "sleep 0.1"
            self.makeSynb0Dir()
            wrapperScriptLines = ["#!/bin/bash \n"]

            wrapperScriptLines.append(f"singularity run -e -B {self.inputSynb0Dir}:/INPUTS -B {self.outputSynb0Dir}:/OUTPUTS -B {self.freesurferLicense}:/extra/freesurfer/license.txt {self.synthB0DiscoSIF} --notopup  \n")
            wrapperScriptLines.append(f"mv {self.outputSynb0Dir.join("b0_u.nii.gz")} {self.outputB0}  \n")
            #wrapperScriptLines.append(f"rm -rv {self.temp_dir} \n")
            with open(self.Synb0WrapperPath, "w") as f:
                f.writelines(wrapperScriptLines)
            return f"bash '{self.Synb0WrapperPath}'"




