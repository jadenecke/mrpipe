# mrpipe
multimodal fully automatic modular neuroimaging processing pipeline 


# About Cat12 MNI space

The template of the CAT12 toolbox is in mni_icbm152_nlin_asym_2009c space, however it is a skull-stripped image with a smaller resolution (e.g. the 1mm isotropic scan is 169x205x169 and not 182x218x182). Therefore the transformation of the skull is not estimated. This is no problem if we want to warp anything from MNI space to T1 space (as long as it is part of the brain) and we end up with the original resolution of whatever the T1w scan was taken in. This has the benefit that any matrix operation relying on matrix indices correspondence (like many of my custom scripts) work. However when we warp anything from T1w to MNI space, the resulting outcome is in MNI space (as any viewer which respects s/q-form will show you in an overlay) but will have the CAT12 template resolution of 169x205x169. Anything that is outside this FOV will not be warped to MNI and will be missing. It is possible to zero pad the image to the original 182x218x182 resolution to achieve matrix indices correspondance but if any processing relies on the entierty of the head beeing present (i.e. not only brain) it is not possible with this pipeline to do this in MNI space, only in native space.

## Container:

 - SHiVAi: `singularity pull docker://jdenecke/shivai:latest`
 - ClearSWI: `singularity pull docker://jdenecke/clearswi-v133:latest`
 - AntsPyNet: `singularity pull docker://cookpa/antspynet:latest-with-data`
 - MARS-WMH: `singularity pull docker://ghcr.io/miac-research/wmh-nnunet:latest` (https://github.com/miac-research/MARS-WMH)
 - MARS-Brainstem: `singularity pull docker://ghcr.io/miac-research/brainstem-nnunet:latest` ([https://github.com/miac-research/MARS-WMH](https://github.com/miac-research/MARS-brainstem))
