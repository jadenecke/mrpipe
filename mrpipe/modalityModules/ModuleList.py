import mrpipe.modalityModules.T1w as T1w
import mrpipe.modalityModules.FLAIR as FLAIR
import mrpipe.modalityModules.MEGRE as MEGRE
import mrpipe.modalityModules.PETAV45 as PETAV45

moduleList = {

    # T1w
    "T1w_base": T1w.T1w_base,
    "T1w_SynthSeg": T1w.T1w_SynthSeg,
    "T1w_1mm": T1w.T1w_1mm,
    "T1w_1p5mm": T1w.T1w_1p5mm,
    "T1w_2mm": T1w.T1w_2mm,
    "T1w_3mm": T1w.T1w_3mm,

    # FLAIR
    "FLAIR_base_withT1w": FLAIR.FLAIR_base_withT1w,
    "FLAIR_ToT1wMNI_1mm": FLAIR.FLAIR_ToT1wMNI_1mm,
    "FLAIR_ToT1wMNI_1p5mm": FLAIR.FLAIR_ToT1wMNI_1p5mm,
    "FLAIR_ToT1wMNI_2mm": FLAIR.FLAIR_ToT1wMNI_2mm,
    "FLAIR_ToT1wMNI_3mm": FLAIR.FLAIR_ToT1wMNI_3mm,

    # MEGRE
    "MEGRE_base": MEGRE.MEGRE_base,
    "MEGRE_ToT1wNative": MEGRE.MEGRE_ToT1wNative,
    "MEGRE_statsNative": MEGRE.MEGRE_statsNative,
    "MEGRE_statsNative_WMH": MEGRE.MEGRE_statsNative_WMH,
    "MEGRE_ToT1wMNI_1mm": MEGRE.MEGRE_ToT1wMNI_1mm,
    "MEGRE_ToT1wMNI_1p5mm": MEGRE.MEGRE_ToT1wMNI_1p5mm,
    "MEGRE_ToT1wMNI_2mm": MEGRE.MEGRE_ToT1wMNI_2mm,
    "MEGRE_ToT1wMNI_3mm": MEGRE.MEGRE_ToT1wMNI_3mm,

    # PET
    "PETAV45_base_withT1w": PETAV45.PETAV45_base_withT1w
}
