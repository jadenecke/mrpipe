import mrpipe.modalityModules.T1w as T1w
import mrpipe.modalityModules.FLAIR as FLAIR
import mrpipe.modalityModules.MEGRE as MEGRE



moduleList = {
    "T1w_base": T1w.T1w_base,
    "T1w_SynthSeg": T1w.T1w_SynthSeg,
    "T1w_1mm": T1w.T1w_1mm,
    "T1w_1p5mm": T1w.T1w_1p5mm,
    "T1w_2mm": T1w.T1w_2mm,
    "T1w_3mm": T1w.T1w_3mm,

    "FLAIR_base": FLAIR.FLAIR_base,
    "FLAIR_ToT1wNative": FLAIR.FLAIR_ToT1wNative,
    "FLAIR_ToT1wMNI_1mm": FLAIR.FLAIR_ToT1wMNI_1mm,
    "FLAIR_ToT1wMNI_1p5mm": FLAIR.FLAIR_ToT1wMNI_1p5mm,
    "FLAIR_ToT1wMNI_2mm": FLAIR.FLAIR_ToT1wMNI_2mm,
    "FLAIR_ToT1wMNI_3mm": FLAIR.FLAIR_ToT1wMNI_3mm,

    "MEGRE_base": MEGRE.MEGRE_base,
    "MEGRE_ToT1wNative": MEGRE.MEGRE_ToT1wNative,
    "MEGRE_ToT1wMNI_1mm": MEGRE.MEGRE_ToT1wMNI_1mm

}
