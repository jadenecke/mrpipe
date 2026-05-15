import os.path
from typing import List

from mrpipe.Toolboxes.submodules.TractSeg.tractseg.libs.preprocessing import clean_up
from mrpipe.meta import LoggerModule
import numpy as np

from mrpipe.meta.ImageWithSideCar import ImageWithSideCar
from mrpipe.modalityModules.PathDicts.BasePaths import PathBase
from mrpipe.meta.PathClass import Path
from mrpipe.meta.PathClass import StatsFilePath
from mrpipe.meta.PathCollection import PathCollection
from mrpipe.meta.ImageSeries import DWI

logger = LoggerModule.Logger()

class PathDictDWI(PathCollection):
    class Bids(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename, *args, **kwargs):
            super().__init__(name="dwi_bids", *args, **kwargs)
            self.basedir = Path(os.path.join(basepaths.bidsPath, filler), isDirectory=True)
            self.basename = Path(os.path.join(basepaths.bidsPath, filler,
                                        nameFormatter.format(subj=sub, ses=ses, basename=basename)))
            self.dwi = DWI(self.basedir, onlyWithReversePhaseEncoding = self.inputArgs.onlyWithReversePhaseEncoding,
                 bval_tol = self.inputArgs.bval_tol, non_gaussian_cutoff=self.inputArgs.non_gaussian_cutoff)


    class Bids_processed(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="dwi_bidsProcessed")
            basenameWithoutPath = nameFormatter.format(subj=sub, ses=ses, basename=basename)
            self.baseString = basenameWithoutPath
            self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler), isDirectory=True)
            self.basename = self.basedir.join(basenameWithoutPath)
            self.basemif = self.basename + ".mif"
            self.acqparams = self.basename + "_acqparams.txt"
            self.index = self.basename + "_index.txt"
            self.denoised = self.basename + "_dns.mif"
            self.degibbs = self.basename + "_dns_dgbs.mif"
            self.firstb0 = self.basename + "_firstb0.nii.gz"
            self.b0ForTopup = self.basename + "_b0ForTopup.nii.gz"
            self.b0MergeForTopup = self.basename + "_b0MergeForTopup.nii.gz"
            self.topup_outdir = self.basedir.join("topup")
            self.topup_out_basename = self.topup_outdir.join("topup_")
            self.topup_b0_hifi = Path(self.topup_out_basename + "b0_hifi.nii.gz")
            self.topup_fieldcoef = Path(self.topup_out_basename + "fieldcoef.nii.gz", static=True)
            self.topup_movepar = Path(self.topup_out_basename + "movepar.txt", static=True)
            self.degibbs_nifti = ImageWithSideCar(self.basename + "_dns_dgbs.nii.gz", self.basename + "_dns_dgbs.json", cleanup=True)
            self.degibbs_bval = self.basename + "_dns_dgbs.bval"
            self.degibbs_bvec = self.basename + "_dns_dgbs.bvec"
            self.topup_b0_hifi_mean = self.topup_out_basename + "b0_hifi_mean.nii.gz"
            self.topup_b0_hifi_mean_stripped = self.topup_out_basename + "b0_hifi_mean_stripped.nii.gz"
            self.topup_b0_hifi_mean_mask = self.topup_out_basename + "b0_hifi_mean_mask.nii.gz"

            self.iso1p5mm = self.Iso1p5mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses,
                                          nameFormatter=nameFormatter,
                                          basename=basename)
            self.iso2mm = self.Iso2mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)
            self.iso3mm = self.Iso3mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)

        class Iso1p5mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                super().__init__(name="dwi_bidsProcessed_iso1p5mm")
                basename = basename + "_iso1p5mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler, "resample_iso1p5mm"), isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))

        class Iso2mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                super().__init__(name="dwi_bidsProcessed_iso2mm")
                basename = basename + "_iso2mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler, "resample_iso2mm"), isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))

        class Iso3mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                super().__init__(name="dwi_bidsProcessed_iso3mm")
                basename = basename + "_iso3mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler, "resample_iso3mm"), isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))

    class Meta_QC(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="dwi_metaQC")
            self.basedir = Path(os.path.join(basepaths.qcPath, filler), isDirectory=True, create=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename), isDirectory=False)
            self.ToT1w_native_slices = self.basename + "_ToT1w_native.png"
            self.shellVisMp4 = self.basename + "_shellVis.mp4"
            self.firstb0 = self.basename + "_firstb0.png"
            self.topup_bmask = self.basename + "_topup_hdbet_mask.png"

    class Bids_statistics(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="dwi_bidsStatistic")
            self.basedir = Path(os.path.join(basepaths.bidsStatisticsPath, filler), isDirectory=True, create=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))



    def __init__(self, sub, ses, basepaths, basedir="DWI", nameFormatter="{subj}_{ses}_{basename}",
                 modalityBeforeSession=False, basename="DWI", *args, **kwargs):
        super().__init__(name="DWI", *args, **kwargs)
        if modalityBeforeSession:
            fillerBids = os.path.join(sub, basedir, ses)
            filler = os.path.join(sub, basename, ses)
        else:
            fillerBids = os.path.join(sub, ses, basedir)
            filler = os.path.join(sub, ses, basename)

        self.subjectName = sub
        self.sessionName = ses
        self.bids = self.Bids(fillerBids, basepaths, sub, ses, nameFormatter, basename, inputArgs=self.inputArgs)
        self.bids_processed = self.Bids_processed(filler, basepaths, sub, ses, nameFormatter, basename)
        self.bids_statistics = self.Bids_statistics(filler, basepaths, sub, ses, nameFormatter, basename)
        self.meta_QC = self.Meta_QC(filler, basepaths, sub, ses, nameFormatter, basename)


    def verify(self):
        if not self.bids.dwi.validate():
            logger.warning(
                f"Subject without valid DWI specifications found, excluding subject {self.subjectName} ({self.sessionName})")
            return None
        return self


