import mrpipe.modalityModules.T1w as T1w
import mrpipe.modalityModules.FLAIR as FLAIR



moduleList = {
    "T1w_base": T1w.T1w_base,
    "T1w_SynthSeg": T1w.T1w_SynthSeg,
    "T1w_1mm": T1w.T1w_1mm,
    "T1w_1p5mm": T1w.T1w_1p5mm,
    "T1w_2mm": T1w.T1w_2mm,
    "T1w_3mm": T1w.T1w_3mm,

    "FLAIR_base": FLAIR.FLAIR_base
}
