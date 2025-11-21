import mrpipe.modalityModules.T1w as T1w
import mrpipe.modalityModules.FLAIR as FLAIR
import mrpipe.modalityModules.MEGRE as MEGRE
import mrpipe.modalityModules.PETAV45 as PETAV45
import mrpipe.modalityModules.PETAV1451 as PETAV1451
import mrpipe.modalityModules.PETFBB as PETFBB
import mrpipe.modalityModules.PETMK6240 as PETMK6240
import mrpipe.modalityModules.PETNAV4694 as PETNAV4694
import mrpipe.modalityModules.PETPI2620 as PETPI2620
import mrpipe.modalityModules.PETFMM as PETFMM
import mrpipe.modalityModules.PETFDG as PETFDG
import yaml



class ProcessingModuleConfig:
    def __init__(self):
        self.T1w_base = True
        self.T1w_SynthSeg = True
        self.T1w_PVS = True
        self.T1w_1mm = True
        self.T1w_1p5mm = True
        self.T1w_2mm = True
        self.T1w_3mm = True
        self.FLAIR_base_withT1w = True
        self.FLAIR_ToT1wMNI_1mm = True
        self.FLAIR_ToT1wMNI_1p5mm = True
        self.FLAIR_ToT1wMNI_2mm = True
        self.FLAIR_ToT1wMNI_3mm = True
        self.MEGRE_base = True
        self.MEGRE_ToT1 = True
        self.MEGRE_CMB = True
        self.MEGRE_ChiSep = True
        self.MEGRE_ToT1wNative = True
        self.MEGRE_statsNative = True
        self.MEGRE_statsNative_WMH = True
        self.MEGRE_ToCAT12MNI = True
        self.MEGRE_ToT1wMNI_1mm = True
        self.MEGRE_ToT1wMNI_1p5mm = True
        self.MEGRE_ToT1wMNI_2mm = True
        self.MEGRE_ToT1wMNI_3mm = True
        self.PETAV45_base_withT1w = True
        self.PETFMM_base_withT1w = True
        self.PETAV1451_base_withT1w = True
        self.PETFBB_base_withT1w = True
        self.PETMK6240_base_withT1w = True
        self.PETNAV4694_base_withT1w = True
        self.PETPI2620_base_withT1w = True
        self.PETPI2620_native_CenTauRZ = True
        self.PETMK6240_native_CenTauRZ = True
        self.PETAV1451_native_CenTauRZ = True
        self.PETFDG_base_withT1w = True

    def to_yaml(self, file_path):
        with open(file_path, 'w') as file:
            yaml.dump(self.__dict__, file)

    @classmethod
    def from_yaml(cls, file_path):
        with open(file_path, 'r') as file:
            data = yaml.load(file, Loader=yaml.FullLoader)
            config = cls()
            config.__dict__.update(data)
            return config

    def construct_modules(self):
        moduleList = {}

        #T1w
        if self.T1w_base:
            moduleList["T1w_base"] = T1w.T1w_base
        if self.T1w_SynthSeg:
            moduleList["T1w_SynthSeg"] = T1w.T1w_SynthSeg
        if self.T1w_PVS:
            moduleList["T1w_PVS"] = T1w.T1w_PVS
        if self.T1w_1mm:
            moduleList["T1w_1mm"] = T1w.T1w_1mm
        if self.T1w_1p5mm:
            moduleList["T1w_1p5mm"] = T1w.T1w_1p5mm
        if self.T1w_2mm:
            moduleList["T1w_2mm"] = T1w.T1w_2mm
        if self.T1w_3mm:
            moduleList["T1w_3mm"] = T1w.T1w_3mm

        #FLAIR
        if self.FLAIR_base_withT1w:
            moduleList["FLAIR_base_withT1w"] = FLAIR.FLAIR_base_withT1w
        if self.FLAIR_ToT1wMNI_1mm:
            moduleList["FLAIR_ToT1wMNI_1mm"] = FLAIR.FLAIR_ToT1wMNI_1mm
        if self.FLAIR_ToT1wMNI_1p5mm:
            moduleList["FLAIR_ToT1wMNI_1p5mm"] = FLAIR.FLAIR_ToT1wMNI_1p5mm
        if self.FLAIR_ToT1wMNI_2mm:
            moduleList["FLAIR_ToT1wMNI_2mm"] = FLAIR.FLAIR_ToT1wMNI_2mm
        if self.FLAIR_ToT1wMNI_3mm:
            moduleList["FLAIR_ToT1wMNI_3mm"] = FLAIR.FLAIR_ToT1wMNI_3mm

        #MEGRE
        if self.MEGRE_base:
            moduleList["MEGRE_base"] = MEGRE.MEGRE_base
        if self.MEGRE_ToT1:
            moduleList["MEGRE_ToT1"] = MEGRE.MEGRE_ToT1
        if self.MEGRE_CMB:
            moduleList["MEGRE_CMB"] = MEGRE.MEGRE_CMB
        if self.MEGRE_ChiSep:
            moduleList["MEGRE_ChiSep"] = MEGRE.MEGRE_ChiSep
        if self.MEGRE_ToT1wNative:
            moduleList["MEGRE_ToT1wNative"] = MEGRE.MEGRE_ToT1wNative
        if self.MEGRE_statsNative:
            moduleList["MEGRE_statsNative"] = MEGRE.MEGRE_statsNative
        if self.MEGRE_statsNative_WMH:
            moduleList["MEGRE_statsNative_WMH"] = MEGRE.MEGRE_statsNative_WMH
        if self.MEGRE_ToCAT12MNI:
            moduleList["MEGRE_ToCAT12MNI"] = MEGRE.MEGRE_ToCAT12MNI
        if self.MEGRE_ToT1wMNI_1mm:
            moduleList["MEGRE_ToT1wMNI_1mm"] = MEGRE.MEGRE_ToT1wMNI_1mm
        if self.MEGRE_ToT1wMNI_1p5mm:
            moduleList["MEGRE_ToT1wMNI_1p5mm"] = MEGRE.MEGRE_ToT1wMNI_1p5mm
        if self.MEGRE_ToT1wMNI_2mm:
            moduleList["MEGRE_ToT1wMNI_2mm"] = MEGRE.MEGRE_ToT1wMNI_2mm
        if self.MEGRE_ToT1wMNI_3mm:
            moduleList["MEGRE_ToT1wMNI_3mm"] = MEGRE.MEGRE_ToT1wMNI_3mm


        #PET
        if self.PETAV45_base_withT1w:
            moduleList["PETAV45_base_withT1w"] = PETAV45.PETAV45_base_withT1w
        if self.PETFMM_base_withT1w:
            moduleList["PETFMM_base_withT1w"] = PETFMM.PETFMM_base_withT1w
        if self.PETAV1451_base_withT1w:
            moduleList["PETAV1451_base_withT1w"] = PETAV1451.PETAV1451_base_withT1w
        if self.PETFBB_base_withT1w:
            moduleList["PETFBB_base_withT1w"] = PETFBB.PETFBB_base_withT1w
        if self.PETMK6240_base_withT1w:
            moduleList["PETMK6240_base_withT1w"] = PETMK6240.PETMK6240_base_withT1w
        if self.PETNAV4694_base_withT1w:
            moduleList["PETNAV4694_base_withT1w"] = PETNAV4694.PETNAV4694_base_withT1w
        if self.PETPI2620_base_withT1w:
            moduleList["PETPI2620_base_withT1w"] = PETPI2620.PETPI2620_base_withT1w
        if self.PETFDG_base_withT1w:
            moduleList["PETFDG_base_withT1w"] = PETFDG.PETFDG_base_withT1w

        #Pet CenTauRz
        if self.PETAV1451_native_CenTauRZ:
            moduleList["PETAV1451_native_CenTauRZ"] = PETAV1451.PETAV1451_native_CenTauRZ
        if self.PETPI2620_native_CenTauRZ:
            moduleList["PETPI2620_native_CenTauRZ"] = PETPI2620.PETPI2620_native_CenTauRZ
        if self.PETAV1451_native_CenTauRZ:
            moduleList["PETMK6240_native_CenTauRZ"] = PETMK6240.PETMK6240_native_CenTauRZ

        return moduleList





# processingmoduleList = {
#     # T1w
#     "T1w_base": T1w.T1w_base,
#     "T1w_SynthSeg": T1w.T1w_SynthSeg,
#     "T1w_1mm": T1w.T1w_1mm,
#     "T1w_1p5mm": T1w.T1w_1p5mm,
#     "T1w_2mm": T1w.T1w_2mm,
#     "T1w_3mm": T1w.T1w_3mm,
#
#     # FLAIR
#     "FLAIR_base_withT1w": FLAIR.FLAIR_base_withT1w,
#     "FLAIR_ToT1wMNI_1mm": FLAIR.FLAIR_ToT1wMNI_1mm,
#     "FLAIR_ToT1wMNI_1p5mm": FLAIR.FLAIR_ToT1wMNI_1p5mm,
#     "FLAIR_ToT1wMNI_2mm": FLAIR.FLAIR_ToT1wMNI_2mm,
#     "FLAIR_ToT1wMNI_3mm": FLAIR.FLAIR_ToT1wMNI_3mm,
#
#     # MEGRE
#     "MEGRE_base": MEGRE.MEGRE_base,
#     "MEGRE_ToT1wNative": MEGRE.MEGRE_ToT1wNative,
#     "MEGRE_statsNative": MEGRE.MEGRE_statsNative,
#     "MEGRE_statsNative_WMH": MEGRE.MEGRE_statsNative_WMH,
#     "MEGRE_ToT1wMNI_1mm": MEGRE.MEGRE_ToT1wMNI_1mm,
#     "MEGRE_ToT1wMNI_1p5mm": MEGRE.MEGRE_ToT1wMNI_1p5mm,
#     "MEGRE_ToT1wMNI_2mm": MEGRE.MEGRE_ToT1wMNI_2mm,
#     "MEGRE_ToT1wMNI_3mm": MEGRE.MEGRE_ToT1wMNI_3mm,
#
#     # PET
#     "PETAV45_base_withT1w": PETAV45.PETAV45_base_withT1w
# }
