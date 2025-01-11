import os.path
from mrpipe.modalityModules.PathDicts.BasePaths import PathBase
from mrpipe.meta.PathClass import Path
from mrpipe.meta.PathCollection import PathCollection
from mrpipe.Toolboxes.standalone.SynthSeg import SynthSeg

class PathDictT1w(PathCollection):

    class Bids(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            super().__init__(name="T1w_bids")
            self.basedir = Path(os.path.join(basepaths.bidsPath, filler), isDirectory=True)
            # self.basename = Path(os.path.join(basepaths.bidsPath, filler,
            #                             nameFormatter.format(subj=sub, ses=ses, basename=basename)))
            # self.T1w = Path(self.basename + ".nii.gz", shouldExist=True)
            self.T1w, T1wImagePatterns, T1wImage_NegativePattern = Path.Identify("T1w nifti", pattern=r"[^\._]+_[^_]+_(.*)\.nii.*",
                                                                                 searchDir=self.basedir,
                                                                                 previousPatterns=[nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".nii*" for pattern in PathDictT1w.getFilePatterns("T1wImagePatterns")],
                                                                                 negativePattern=[nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".nii*" for pattern in PathDictT1w.getFilePatterns("T1wImage_NegativePattern")])
            if T1wImagePatterns is not None:
                PathDictT1w.setFilePatterns("T1wImagePatterns", T1wImagePatterns)
            if T1wImage_NegativePattern is not None:
                PathDictT1w.setFilePatterns("T1wImage_NegativePattern", T1wImage_NegativePattern)
            # self.json = Path(self.basename + ".json", shouldExist=True)
            self.json, T1wJSONPatterns, T1wJSON_NegativePattern = Path.Identify("T1w json", pattern=r"[^\._]+_[^_]+_(.*)\.json",
                                                                                searchDir=self.basedir,
                                                                                previousPatterns=[nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".json" for pattern in PathDictT1w.getFilePatterns("T1wJSONPatterns")],
                                                                                negativePattern=[nameFormatter.format(subj=sub, ses=ses, basename=pattern) + ".json" for pattern in PathDictT1w.getFilePatterns("T1wJSON_NegativePattern")])

            if T1wJSONPatterns is not None:
                PathDictT1w.setFilePatterns("T1wJSONPatterns", T1wJSONPatterns)
            if T1wJSON_NegativePattern is not None:
                PathDictT1w.setFilePatterns("T1wJSON_NegativePattern", T1wJSON_NegativePattern)



    class Bids_processed(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename, t1w: Path):
            super().__init__(name="T1w_bidsProcessed")
            self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
            self.T1w = t1w.copy(self.basename + ".nii.gz")
            self.json = Path(self.basename + ".json")
            self.recentered = self.basename + "_recentered.nii.gz"
            self.N4BiasCorrected = self.basename + "_N4.nii.gz"
            self.hdbet_brain = self.basename + "_brain.nii.gz"
            self.hdbet_mask = (self.basename + "_brain_mask.nii.gz").setStatic() #can not be changed because it is not allowed to specify the mask name in hd-bet. However it always will be hdbet-output name with _mask attached.

            # GM
            self.synthsegGM = self.basename + "_GM.nii.gz"
            self.maskGM_thr0p5 = self.basename + "_mask_GM_thr0p5.nii.gz"
            self.maskGM_thr0p5_ero1mm = self.basename + "_mask_GM_thr0p5_ero1mm.nii.gz"
            self.maskGM_thr0p3 = self.basename + "_mask_GM_thr0p3.nii.gz"
            self.maskGM_thr0p3_ero1mm = self.basename + "_mask_GM_thr0p3_ero1mm.nii.gz"
            # WM
            self.synthsegWM = self.basename + "_WM.nii.gz"
            self.maskWM_thr0p5 = self.basename + "_mask_WM_thr0p5.nii.gz"
            self.maskWM_thr0p5_ero1mm = self.basename + "_mask_WM_thr0p5_ero1mm.nii.gz"
            # CSF
            self.synthsegCSF = self.basename + "_CSF.nii.gz"
            self.maskCSF_thr0p9 = self.basename + "_mask_CSF_thr0p9.nii.gz"
            self.maskCSF_thr0p9_ero1mm = self.basename + "_mask_CSF_thr0p9_ero1mm.nii.gz"
            # GMCortical
            self.synthsegGMCortical = self.basename + "_GMCortical.nii.gz"
            self.maskGMCortical_thr0p3 = self.basename + "_mask_GMCortical_thr0p5.nii.gz"
            self.maskGMCortical_thr0p3_ero1mm = self.basename + "_mask_GMCortical_thr0p5_ero1mm.nii.gz"
            self.maskGMCortical_thr0p5 = self.basename + "_mask_GMCortical_thr0p5.nii.gz"
            self.maskGMCortical_thr0p5_ero1mm = self.basename + "_mask_GMCortical_thr0p5_ero1mm.nii.gz"
            # WMCortical
            self.synthsegWMCortical = self.basename + "_WMCortical.nii.gz"
            self.maskWMCortical_thr0p5 = self.basename + "_mask_WMCortical_thr0p5.nii.gz"
            self.maskWMCortical_thr0p5_ero1mm = self.basename + "_mask_WMCortical_thr0p5_ero1mm.nii.gz"

            self.synthseg = self.SynthSeg(basedir=self.basedir,  sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)
            self.cat12 = self.cat12(basedir=self.basedir, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                          basename=basename, t1wImage=self.T1w)
            self.iso1mm = self.Iso1mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)
            self.iso1p5mm = self.Iso1p5mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)
            self.iso2mm = self.Iso2mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)
            self.iso3mm = self.Iso3mm(filler=filler, basepaths=basepaths, sub=sub, ses=ses, nameFormatter=nameFormatter,
                                      basename=basename)

        class SynthSeg(PathCollection):
            def __init__(self, basedir, sub, ses, nameFormatter, basename):

                self.synthsegDir = basedir.join("SynthSeg", isDirectory=True)
                self.synthsegBasename = self.synthsegDir.join(
                    nameFormatter.format(subj=sub, ses=ses, basename=basename), isDirectory=False)
                self.synthsegPosterior = self.synthsegBasename + "_posterior.nii.gz"
                self.synthsegPosteriorProbabilities = self.synthsegBasename + "_posteriorProbabilities.nii.gz"
                self.synthsegResample = self.synthsegBasename + "_resampled.nii.gz"
                self.synthsegSplitStem = self.synthsegBasename + "_vol"

                # add Synthseg output posteriors:
                self.synthsegPosteriorPathNames = SynthSeg.PosteriorPaths(self.synthsegBasename)
                self.synthsegGM = self.synthsegBasename + "_GM.nii.gz"
                self.synthsegWM = self.synthsegBasename + "_WM.nii.gz"
                self.synthsegCSF = self.synthsegBasename + "_CSF.nii.gz"
                self.synthsegGMCortical = self.synthsegBasename + "_GMCortical.nii.gz"
                self.synthsegWMCortical = self.synthsegBasename + "_WMCortical.nii.gz"

        class cat12(PathCollection):
            def __init__(self, basedir, sub, ses, nameFormatter, basename, t1wImage):
                self.cat12Dir = basedir.join("cat12", isDirectory=True)
                self.cat12BaseFileName = nameFormatter.format(subj=sub, ses=ses, basename=basename)
                self.cat12Basename = self.cat12Dir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename), isDirectory=False)
                self.cat12Script = self.cat12Dir.join("cat12script.m", isDirectory=False)
                self.cat12BaseImage = t1wImage.copy(self.cat12Dir.join(t1wImage.get_filename(), onlyPathStr=True), unzip=True) #TODO fix this so that it does not zip/unzip files on every run.

                #TODO: Next Steps: fix more cat12 output files and add further processing of cat12 masks and volumetric atlasses.

                # add (some / used) cat12 output files:
                self.cat12_T1_grayMatterProbability = self.cat12Dir.join("mri").join(
                    "p1" + self.cat12BaseFileName + ".nii").setStatic()
                self.cat12_T1_whiteMatterProbability = self.cat12Dir.join("mri").join(
                    "p2" + self.cat12BaseFileName + ".nii").setStatic()
                self.cat12_T1_csfProbability = self.cat12Dir.join("mri").join(
                    "p3" + self.cat12BaseFileName + ".nii").setStatic()

                self.cat12_MNI_grayMatterProbability = self.cat12Dir.join("mri").join(
                    "mwp1" + self.cat12BaseFileName + ".nii").setStatic()
                self.cat12_MNI_whiteMatterProbability = self.cat12Dir.join("mri").join(
                    "mwp2" + self.cat12BaseFileName + ".nii").setStatic()
                self.cat12_MNI_csfProbability = self.cat12Dir.join("mri").join(
                    "mwp3" + self.cat12BaseFileName + ".nii").setStatic()

        class Iso1mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                basename = basename + "_iso1mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler, "resample_iso1mm"), isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
                self.baseimage = self.basename + ".nii.gz"
                self.brain = self.basename + "_brain.nii.gz"
                self.brainmask = self.basename + "_brainmask.nii.gz"
                #GM
                self.synthsegGM = self.basename + "_GM.nii.gz"
                self.maskGM_thr0p5 = self.basename + "_mask_GM_thr0p5.nii.gz"
                self.maskGM_thr0p5_ero1mm = self.basename + "_mask_GM_thr0p5_ero1mm.nii.gz"
                self.maskGM_thr0p3 = self.basename + "_mask_GM_thr0p3.nii.gz"
                self.maskGM_thr0p3_ero1mm = self.basename + "_mask_GM_thr0p3_ero1mm.nii.gz"
                # WM
                self.synthsegWM = self.basename + "_WM.nii.gz"
                self.maskWM_thr0p5 = self.basename + "_mask_WM_thr0p5.nii.gz"
                self.maskWM_thr0p5_ero1mm = self.basename + "_mask_WM_thr0p5_ero1mm.nii.gz"
                # CSF
                self.synthsegCSF = self.basename + "_CSF.nii.gz"
                self.maskCSF_thr0p9 = self.basename + "_mask_CSF_thr0p9.nii.gz"
                self.maskCSF_thr0p9_ero1mm = self.basename + "_mask_CSF_thr0p9_ero1mm.nii.gz"
                # GMCortical
                self.synthsegGMCortical = self.basename + "_GMCortical.nii.gz"
                self.maskGMCortical_thr0p3 = self.basename + "_mask_GMCortical_thr0p5.nii.gz"
                self.maskGMCortical_thr0p3_ero1mm = self.basename + "_mask_GMCortical_thr0p5_ero1mm.nii.gz"
                self.maskGMCortical_thr0p5 = self.basename + "_mask_GMCortical_thr0p5.nii.gz"
                self.maskGMCortical_thr0p5_ero1mm = self.basename + "_mask_GMCortical_thr0p5_ero1mm.nii.gz"
                # WMCortical
                self.synthsegWMCortical = self.basename + "_WMCortical.nii.gz"
                self.maskWMCortical_thr0p5 = self.basename + "_mask_WMCortical_thr0p5.nii.gz"
                self.maskWMCortical_thr0p5_ero1mm = self.basename + "_mask_WMCortical_thr0p5_ero1mm.nii.gz"

                #MNI
                self.MNI_prefix = self.basename + "_toMNI"
                self.MNI_toMNI = (self.MNI_prefix + "Warped.nii.gz").setStatic()
                self.MNI_0GenericAffine = (self.MNI_prefix + "0GenericAffine.mat").setStatic()
                self.MNI_1Warp = (self.MNI_prefix + "1Warp.nii.gz").setStatic()
                self.MNI_1InverseWarp = (self.MNI_prefix + "1InverseWarp.nii.gz").setStatic()
                self.MNI_InverseWarped = (self.MNI_prefix + "InverseWarped.nii.gz").setStatic().setCleanup()
                # GM MNI
                self.MNI_synthsegGM = self.MNI_prefix + "_GM.nii.gz"
                self.MNI_maskGM_thr0p5 = self.MNI_prefix + "_mask_GM_thr0p5.nii.gz"
                self.MNI_maskGM_thr0p5_ero1mm = self.MNI_prefix + "_mask_GM_thr0p5_ero1mm.nii.gz"
                self.MNI_maskGM_thr0p3 = self.MNI_prefix + "_mask_GM_thr0p3.nii.gz"
                self.MNI_maskGM_thr0p3_ero1mm = self.MNI_prefix + "_mask_GM_thr0p3_ero1mm.nii.gz"
                # WM MNI
                self.MNI_synthsegWM = self.MNI_prefix + "_WM.nii.gz"
                self.MNI_maskWM_thr0p5 = self.MNI_prefix + "_mask_WM_thr0p5.nii.gz"
                self.MNI_maskWM_thr0p5_ero1mm = self.MNI_prefix + "_mask_WM_thr0p5_ero1mm.nii.gz"
                # CSF MNI
                self.MNI_synthsegCSF = self.MNI_prefix + "_CSF.nii.gz"
                self.MNI_maskCSF_thr0p9 = self.MNI_prefix + "_mask_CSF_thr0p9.nii.gz"
                self.MNI_maskCSF_thr0p9_ero1mm = self.MNI_prefix + "_mask_CSF_thr0p9_ero1mm.nii.gz"
                # GMCortical MNI
                self.MNI_synthsegGMCortical = self.MNI_prefix + "_GMCortical.nii.gz"
                self.MNI_maskGMCortical_thr0p3 = self.MNI_prefix + "_mask_GMCortical_thr0p5.nii.gz"
                self.MNI_maskGMCortical_thr0p3_ero1mm = self.MNI_prefix + "_mask_GMCortical_thr0p5_ero1mm.nii.gz"
                self.MNI_maskGMCortical_thr0p5 = self.MNI_prefix + "_mask_GMCortical_thr0p5.nii.gz"
                self.MNI_maskGMCortical_thr0p5_ero1mm = self.MNI_prefix + "_mask_GMCortical_thr0p5_ero1mm.nii.gz"
                # WMCortical MNI
                self.MNI_synthsegWMCortical = self.MNI_prefix + "_WMCortical.nii.gz"
                self.MNI_maskWMCortical_thr0p5 = self.MNI_prefix + "_mask_WMCortical_thr0p5.nii.gz"
                self.MNI_maskWMCortical_thr0p5_ero1mm = self.MNI_prefix + "_mask_WMCortical_thr0p5_ero1mm.nii.gz"

        class Iso1p5mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                basename = basename + "_iso1p5mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler, "resample_iso1p5mm"),
                                    isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
                self.baseimage = self.basename + ".nii.gz"
                self.brain = self.basename + "_brain.nii.gz"
                self.brainmask = self.basename + "_brainmask.nii.gz"
                # GM
                self.synthsegGM = self.basename + "_GM.nii.gz"
                self.maskGM_thr0p5 = self.basename + "_mask_GM_thr0p5.nii.gz"
                self.maskGM_thr0p5_ero1mm = self.basename + "_mask_GM_thr0p5_ero1mm.nii.gz"
                self.maskGM_thr0p3 = self.basename + "_mask_GM_thr0p3.nii.gz"
                self.maskGM_thr0p3_ero1mm = self.basename + "_mask_GM_thr0p3_ero1mm.nii.gz"
                # WM
                self.synthsegWM = self.basename + "_WM.nii.gz"
                self.maskWM_thr0p5 = self.basename + "_mask_WM_thr0p5.nii.gz"
                self.maskWM_thr0p5_ero1mm = self.basename + "_mask_WM_thr0p5_ero1mm.nii.gz"
                # CSF
                self.synthsegCSF = self.basename + "_CSF.nii.gz"
                self.maskCSF_thr0p9 = self.basename + "_mask_CSF_thr0p9.nii.gz"
                self.maskCSF_thr0p9_ero1mm = self.basename + "_mask_CSF_thr0p9_ero1mm.nii.gz"
                # GMCortical
                self.synthsegGMCortical = self.basename + "_GMCortical.nii.gz"
                self.maskGMCortical_thr0p3 = self.basename + "_mask_GMCortical_thr0p5.nii.gz"
                self.maskGMCortical_thr0p3_ero1mm = self.basename + "_mask_GMCortical_thr0p5_ero1mm.nii.gz"
                self.maskGMCortical_thr0p5 = self.basename + "_mask_GMCortical_thr0p5.nii.gz"
                self.maskGMCortical_thr0p5_ero1mm = self.basename + "_mask_GMCortical_thr0p5_ero1mm.nii.gz"
                # WMCortical
                self.synthsegWMCortical = self.basename + "_WMCortical.nii.gz"
                self.maskWMCortical_thr0p5 = self.basename + "_mask_WMCortical_thr0p5.nii.gz"
                self.maskWMCortical_thr0p5_ero1mm = self.basename + "_mask_WMCortical_thr0p5_ero1mm.nii.gz"

                # MNI
                self.MNI_prefix = self.basename + "_toMNI"
                self.MNI_toMNI = (self.MNI_prefix + "Warped.nii.gz").setStatic()
                self.MNI_0GenericAffine = (self.MNI_prefix + "0GenericAffine.mat").setStatic()
                self.MNI_1Warp = (self.MNI_prefix + "1Warp.nii.gz").setStatic()
                self.MNI_1InverseWarp = (self.MNI_prefix + "1InverseWarp.nii.gz").setStatic()
                self.MNI_InverseWarped = (self.MNI_prefix + "InverseWarped.nii.gz").setStatic().setCleanup()
                # GM MNI
                self.MNI_synthsegGM = self.MNI_prefix + "_GM.nii.gz"
                self.MNI_maskGM_thr0p5 = self.MNI_prefix + "_mask_GM_thr0p5.nii.gz"
                self.MNI_maskGM_thr0p5_ero1mm = self.MNI_prefix + "_mask_GM_thr0p5_ero1mm.nii.gz"
                self.MNI_maskGM_thr0p3 = self.MNI_prefix + "_mask_GM_thr0p3.nii.gz"
                self.MNI_maskGM_thr0p3_ero1mm = self.MNI_prefix + "_mask_GM_thr0p3_ero1mm.nii.gz"
                # WM MNI
                self.MNI_synthsegWM = self.MNI_prefix + "_WM.nii.gz"
                self.MNI_maskWM_thr0p5 = self.MNI_prefix + "_mask_WM_thr0p5.nii.gz"
                self.MNI_maskWM_thr0p5_ero1mm = self.MNI_prefix + "_mask_WM_thr0p5_ero1mm.nii.gz"
                # CSF MNI
                self.MNI_synthsegCSF = self.MNI_prefix + "_CSF.nii.gz"
                self.MNI_maskCSF_thr0p9 = self.MNI_prefix + "_mask_CSF_thr0p9.nii.gz"
                self.MNI_maskCSF_thr0p9_ero1mm = self.MNI_prefix + "_mask_CSF_thr0p9_ero1mm.nii.gz"
                # GMCortical MNI
                self.MNI_synthsegGMCortical = self.MNI_prefix + "_GMCortical.nii.gz"
                self.MNI_maskGMCortical_thr0p3 = self.MNI_prefix + "_mask_GMCortical_thr0p5.nii.gz"
                self.MNI_maskGMCortical_thr0p3_ero1mm = self.MNI_prefix + "_mask_GMCortical_thr0p5_ero1mm.nii.gz"
                self.MNI_maskGMCortical_thr0p5 = self.MNI_prefix + "_mask_GMCortical_thr0p5.nii.gz"
                self.MNI_maskGMCortical_thr0p5_ero1mm = self.MNI_prefix + "_mask_GMCortical_thr0p5_ero1mm.nii.gz"
                # WMCortical MNI
                self.MNI_synthsegWMCortical = self.MNI_prefix + "_WMCortical.nii.gz"
                self.MNI_maskWMCortical_thr0p5 = self.MNI_prefix + "_mask_WMCortical_thr0p5.nii.gz"
                self.MNI_maskWMCortical_thr0p5_ero1mm = self.MNI_prefix + "_mask_WMCortical_thr0p5_ero1mm.nii.gz"

        class Iso2mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                basename = basename + "_iso2mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler,"resample_iso2mm"),
                                    isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
                self.baseimage = self.basename + ".nii.gz"
                self.brain = self.basename + "_brain.nii.gz"
                self.brainmask = self.basename + "_brainmask.nii.gz"
                # GM
                self.synthsegGM = self.basename + "_GM.nii.gz"
                self.maskGM_thr0p5 = self.basename + "_mask_GM_thr0p5.nii.gz"
                self.maskGM_thr0p5_ero1mm = self.basename + "_mask_GM_thr0p5_ero1mm.nii.gz"
                self.maskGM_thr0p3 = self.basename + "_mask_GM_thr0p3.nii.gz"
                self.maskGM_thr0p3_ero1mm = self.basename + "_mask_GM_thr0p3_ero1mm.nii.gz"
                # WM
                self.synthsegWM = self.basename + "_WM.nii.gz"
                self.maskWM_thr0p5 = self.basename + "_mask_WM_thr0p5.nii.gz"
                self.maskWM_thr0p5_ero1mm = self.basename + "_mask_WM_thr0p5_ero1mm.nii.gz"
                # CSF
                self.synthsegCSF = self.basename + "_CSF.nii.gz"
                self.maskCSF_thr0p9 = self.basename + "_mask_CSF_thr0p9.nii.gz"
                self.maskCSF_thr0p9_ero1mm = self.basename + "_mask_CSF_thr0p9_ero1mm.nii.gz"
                # GMCortical
                self.synthsegGMCortical = self.basename + "_GMCortical.nii.gz"
                self.maskGMCortical_thr0p3 = self.basename + "_mask_GMCortical_thr0p5.nii.gz"
                self.maskGMCortical_thr0p3_ero1mm = self.basename + "_mask_GMCortical_thr0p5_ero1mm.nii.gz"
                self.maskGMCortical_thr0p5 = self.basename + "_mask_GMCortical_thr0p5.nii.gz"
                self.maskGMCortical_thr0p5_ero1mm = self.basename + "_mask_GMCortical_thr0p5_ero1mm.nii.gz"
                # WMCortical
                self.synthsegWMCortical = self.basename + "_WMCortical.nii.gz"
                self.maskWMCortical_thr0p5 = self.basename + "_mask_WMCortical_thr0p5.nii.gz"
                self.maskWMCortical_thr0p5_ero1mm = self.basename + "_mask_WMCortical_thr0p5_ero1mm.nii.gz"

                # MNI
                self.MNI_prefix = self.basename + "_toMNI"
                self.MNI_toMNI = (self.MNI_prefix + "Warped.nii.gz").setStatic()
                self.MNI_0GenericAffine = (self.MNI_prefix + "0GenericAffine.mat").setStatic()
                self.MNI_1Warp = (self.MNI_prefix + "1Warp.nii.gz").setStatic()
                self.MNI_1InverseWarp = (self.MNI_prefix + "1InverseWarp.nii.gz").setStatic()
                self.MNI_InverseWarped = (self.MNI_prefix + "InverseWarped.nii.gz").setStatic().setCleanup()
                # GM MNI
                self.MNI_synthsegGM = self.MNI_prefix + "_GM.nii.gz"
                self.MNI_maskGM_thr0p5 = self.MNI_prefix + "_mask_GM_thr0p5.nii.gz"
                self.MNI_maskGM_thr0p5_ero1mm = self.MNI_prefix + "_mask_GM_thr0p5_ero1mm.nii.gz"
                self.MNI_maskGM_thr0p3 = self.MNI_prefix + "_mask_GM_thr0p3.nii.gz"
                self.MNI_maskGM_thr0p3_ero1mm = self.MNI_prefix + "_mask_GM_thr0p3_ero1mm.nii.gz"
                # WM MNI
                self.MNI_synthsegWM = self.MNI_prefix + "_WM.nii.gz"
                self.MNI_maskWM_thr0p5 = self.MNI_prefix + "_mask_WM_thr0p5.nii.gz"
                self.MNI_maskWM_thr0p5_ero1mm = self.MNI_prefix + "_mask_WM_thr0p5_ero1mm.nii.gz"
                # CSF MNI
                self.MNI_synthsegCSF = self.MNI_prefix + "_CSF.nii.gz"
                self.MNI_maskCSF_thr0p9 = self.MNI_prefix + "_mask_CSF_thr0p9.nii.gz"
                self.MNI_maskCSF_thr0p9_ero1mm = self.MNI_prefix + "_mask_CSF_thr0p9_ero1mm.nii.gz"
                # GMCortical MNI
                self.MNI_synthsegGMCortical = self.MNI_prefix + "_GMCortical.nii.gz"
                self.MNI_maskGMCortical_thr0p3 = self.MNI_prefix + "_mask_GMCortical_thr0p5.nii.gz"
                self.MNI_maskGMCortical_thr0p3_ero1mm = self.MNI_prefix + "_mask_GMCortical_thr0p5_ero1mm.nii.gz"
                self.MNI_maskGMCortical_thr0p5 = self.MNI_prefix + "_mask_GMCortical_thr0p5.nii.gz"
                self.MNI_maskGMCortical_thr0p5_ero1mm = self.MNI_prefix + "_mask_GMCortical_thr0p5_ero1mm.nii.gz"
                # WMCortical MNI
                self.MNI_synthsegWMCortical = self.MNI_prefix + "_WMCortical.nii.gz"
                self.MNI_maskWMCortical_thr0p5 = self.MNI_prefix + "_mask_WMCortical_thr0p5.nii.gz"
                self.MNI_maskWMCortical_thr0p5_ero1mm = self.MNI_prefix + "_mask_WMCortical_thr0p5_ero1mm.nii.gz"

        class Iso3mm(PathCollection):
            def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
                basename = basename + "_iso3mm"
                self.basedir = Path(os.path.join(basepaths.bidsProcessedPath, filler, "resample_iso3mm"),
                                    isDirectory=True)
                self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
                self.baseimage = self.basename + ".nii.gz"
                self.brain = self.basename + "_brain.nii.gz"
                self.brainmask = self.basename + "_brainmask.nii.gz"
                # GM
                self.synthsegGM = self.basename + "_GM.nii.gz"
                self.maskGM_thr0p5 = self.basename + "_mask_GM_thr0p5.nii.gz"
                self.maskGM_thr0p5_ero1mm = self.basename + "_mask_GM_thr0p5_ero1mm.nii.gz"
                self.maskGM_thr0p3 = self.basename + "_mask_GM_thr0p3.nii.gz"
                self.maskGM_thr0p3_ero1mm = self.basename + "_mask_GM_thr0p3_ero1mm.nii.gz"
                # WM
                self.synthsegWM = self.basename + "_WM.nii.gz"
                self.maskWM_thr0p5 = self.basename + "_mask_WM_thr0p5.nii.gz"
                self.maskWM_thr0p5_ero1mm = self.basename + "_mask_WM_thr0p5_ero1mm.nii.gz"
                # CSF
                self.synthsegCSF = self.basename + "_CSF.nii.gz"
                self.maskCSF_thr0p9 = self.basename + "_mask_CSF_thr0p9.nii.gz"
                self.maskCSF_thr0p9_ero1mm = self.basename + "_mask_CSF_thr0p9_ero1mm.nii.gz"
                # GMCortical
                self.synthsegGMCortical = self.basename + "_GMCortical.nii.gz"
                self.maskGMCortical_thr0p3 = self.basename + "_mask_GMCortical_thr0p5.nii.gz"
                self.maskGMCortical_thr0p3_ero1mm = self.basename + "_mask_GMCortical_thr0p5_ero1mm.nii.gz"
                self.maskGMCortical_thr0p5 = self.basename + "_mask_GMCortical_thr0p5.nii.gz"
                self.maskGMCortical_thr0p5_ero1mm = self.basename + "_mask_GMCortical_thr0p5_ero1mm.nii.gz"
                # WMCortical
                self.synthsegWMCortical = self.basename + "_WMCortical.nii.gz"
                self.maskWMCortical_thr0p5 = self.basename + "_mask_WMCortical_thr0p5.nii.gz"
                self.maskWMCortical_thr0p5_ero1mm = self.basename + "_mask_WMCortical_thr0p5_ero1mm.nii.gz"

                # MNI
                self.MNI_prefix = self.basename + "_toMNI"
                self.MNI_toMNI = (self.MNI_prefix + "Warped.nii.gz").setStatic()
                self.MNI_0GenericAffine = (self.MNI_prefix + "0GenericAffine.mat").setStatic()
                self.MNI_1Warp = (self.MNI_prefix + "1Warp.nii.gz").setStatic()
                self.MNI_1InverseWarp = (self.MNI_prefix + "1InverseWarp.nii.gz").setStatic()
                self.MNI_InverseWarped = (self.MNI_prefix + "InverseWarped.nii.gz").setStatic().setCleanup()
                # GM MNI
                self.MNI_synthsegGM = self.MNI_prefix + "_GM.nii.gz"
                self.MNI_maskGM_thr0p5 = self.MNI_prefix + "_mask_GM_thr0p5.nii.gz"
                self.MNI_maskGM_thr0p5_ero1mm = self.MNI_prefix + "_mask_GM_thr0p5_ero1mm.nii.gz"
                self.MNI_maskGM_thr0p3 = self.MNI_prefix + "_mask_GM_thr0p3.nii.gz"
                self.MNI_maskGM_thr0p3_ero1mm = self.MNI_prefix + "_mask_GM_thr0p3_ero1mm.nii.gz"
                # WM MNI
                self.MNI_synthsegWM = self.MNI_prefix + "_WM.nii.gz"
                self.MNI_maskWM_thr0p5 = self.MNI_prefix + "_mask_WM_thr0p5.nii.gz"
                self.MNI_maskWM_thr0p5_ero1mm = self.MNI_prefix + "_mask_WM_thr0p5_ero1mm.nii.gz"
                # CSF MNI
                self.MNI_synthsegCSF = self.MNI_prefix + "_CSF.nii.gz"
                self.MNI_maskCSF_thr0p9 = self.MNI_prefix + "_mask_CSF_thr0p9.nii.gz"
                self.MNI_maskCSF_thr0p9_ero1mm = self.MNI_prefix + "_mask_CSF_thr0p9_ero1mm.nii.gz"
                # GMCortical MNI
                self.MNI_synthsegGMCortical = self.MNI_prefix + "_GMCortical.nii.gz"
                self.MNI_maskGMCortical_thr0p3 = self.MNI_prefix + "_mask_GMCortical_thr0p5.nii.gz"
                self.MNI_maskGMCortical_thr0p3_ero1mm = self.MNI_prefix + "_mask_GMCortical_thr0p5_ero1mm.nii.gz"
                self.MNI_maskGMCortical_thr0p5 = self.MNI_prefix + "_mask_GMCortical_thr0p5.nii.gz"
                self.MNI_maskGMCortical_thr0p5_ero1mm = self.MNI_prefix + "_mask_GMCortical_thr0p5_ero1mm.nii.gz"
                # WMCortical MNI
                self.MNI_synthsegWMCortical = self.MNI_prefix + "_WMCortical.nii.gz"
                self.MNI_maskWMCortical_thr0p5 = self.MNI_prefix + "_mask_WMCortical_thr0p5.nii.gz"
                self.MNI_maskWMCortical_thr0p5_ero1mm = self.MNI_prefix + "_mask_WMCortical_thr0p5_ero1mm.nii.gz"

    class Meta_QC(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            self.basedir = Path(os.path.join(basepaths.qcPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename), isDirectory=False)
            self.synthsegQC = self.basename + "_SynthSegQC_Scores.csv"
            self.hdbet_slices = self.basename + "_hdbet_slices.png"
            self.synthseg_slices = self.basename + "_hdbet_synthseg.png"
            self.GMthr0p3_slices = self.basename + "_GM_thr0p3.png"
            self.GMthr0p5_slices = self.basename + "_GM_thr0p5.png"
            self.WMthr0p5_slices = self.basename + "_WM_thr0p5.png"
            self.CSFthr0p9_slices = self.basename + "_CSF_thr0p9.png"
            self.MNI_1mm_slices = self.basename + "_nativeToMNI_1mm.png"
            self.MNI_1p5mm_slices = self.basename + "_nativeToMNI_1p5mm.png"
            self.MNI_2mm_slices = self.basename + "_nativeToMNI_2mm.png"
            self.MNI_3mm_slices = self.basename + "_nativeToMNI_3mm.png"

    class Bids_statistics(PathCollection):
        def __init__(self, filler, basepaths: PathBase, sub, ses, nameFormatter, basename):
            self.basedir = Path(os.path.join(basepaths.bidsStatisticsPath, filler), isDirectory=True)
            self.basename = self.basedir.join(nameFormatter.format(subj=sub, ses=ses, basename=basename))
            self.synthsegVolumes = self.basename + "_SynthSeg_Volumes.csv"

    def __init__(self, sub, ses, basepaths, basedir="T1w", nameFormatter="{subj}_{ses}_{basename}",
                 modalityBeforeSession=False, basename="T1w"):
        super().__init__(name="T1w")
        if modalityBeforeSession:
            fillerBids = os.path.join(sub, basedir, ses)
            filler = os.path.join(sub, basename, ses)
        else:
            fillerBids = os.path.join(sub, ses, basedir)
            filler = os.path.join(sub, ses, basename)

        self.bids = self.Bids(fillerBids, basepaths, sub, ses, nameFormatter, basename)
        self.bids_processed = self.Bids_processed(filler, basepaths, sub, ses, nameFormatter, basename, t1w=self.bids.T1w)
        self.bids_statistics = self.Bids_statistics(filler, basepaths, sub, ses, nameFormatter, basename)
        self.meta_QC = self.Meta_QC(filler, basepaths, sub, ses, nameFormatter, basename)

