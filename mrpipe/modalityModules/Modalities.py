from enum import Enum
import yaml


# class Modalities(Enum):
#     T1w = "T1w"
#     func = 2
#     dwi = 3
#     flair = 4
#     megre = 5
#     T2w = 6
#     swi = 7
#     flash = 8
#     fieldmap = 9
#
#     pet_fdg = 100
#     pet_amyloid = 101
#     pet_tau = 102
#     pet_synaptic = 103

class Modalities:
    def __init__(self):
        self.T1w = 1
        self.func = 2
        self.dwi = 3
        self.flair = 4
        self.megre = 5
        self.T2w = 6
        self.swi = 7
        self.flash = 8
        self.fieldmap = 9
        self.pet_fdg = 100
        self.pet_amyloid = 101
        self.pet_tau = 102
        self.pet_synaptic = 103

    @classmethod
    def load(cls, yaml_file):
        with open(yaml_file, 'r') as file:
            self.modalities = yaml.safe_load(file)
    def write_to_yaml(self, yaml_file):
        with open(yaml_file, 'w') as file:
            yaml.safe_dump(self.modalities, file)

    def available_modalities(self):
        return [Modalities[modality] for modality, path in self.modalities.items() if path]



