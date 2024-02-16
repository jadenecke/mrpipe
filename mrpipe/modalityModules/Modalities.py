from enum import Enum
import yaml

class Modalities:
    def __init__(self, T1w=None, func=None, dwi=None, flair=None, megre=None, T2w=None, swi=None, flash=None, fieldmap=None, pet_fdg=None, pet_tau=None,
                 pet_amyloid=None, pet_synaptic=None):
        self.T1w = T1w
        self.func = func
        self.dwi = dwi
        self.flair = flair
        self.megre = megre
        self.T2w = T2w
        self.swi = swi
        self.flash = flash
        self.fieldmap = fieldmap
        self.pet_fdg = pet_fdg
        self.pet_amyloid = pet_amyloid
        self.pet_tau = pet_tau
        self.pet_synaptic = pet_synaptic

    def to_yaml(self, filepath):
        with open(filepath, 'w') as file:
            yaml.dump(self.__dict__, file)

    @classmethod
    def from_yaml(cls, filepath):
        with open(filepath, 'r') as file:
            data = yaml.safe_load(file)
        return cls(**data)

    def available_modalities(self):
        return [key for key, value in self.__dict__.items() if value]




