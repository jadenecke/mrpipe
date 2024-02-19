from enum import Enum
import yaml
from mrpipe.meta.PathCollection import PathCollection
from fuzzywuzzy import process



class Modalities(PathCollection):
    previous_inputs = {}
    def __init__(self, T1w=None, t1map=None, rsfmri=None, taskfmri=None, dwi=None, flair=None, megre=None, T2w=None, t2map=None, swi=None, flash=None, fieldmap=None, pet_fdg=None, pet_tau=None,
                 pet_amyloid=None, pet_synaptic=None, protonDensity=None, localizer=None):
        self.T1w = T1w
        self.t1map = t1map
        self.rsfmri = rsfmri
        self.taskfmri = taskfmri
        self.dwi = dwi
        self.flair = flair
        self.megre = megre
        self.T2w = T2w
        self.t2map = t2map
        self.swi = swi
        self.flash = flash
        self.fieldmap = fieldmap
        self.localizer = localizer
        self.protonDensity = protonDensity
        self.pet_fdg = pet_fdg
        self.pet_amyloid = pet_amyloid
        self.pet_tau = pet_tau
        self.pet_synaptic = pet_synaptic


    def available_modalities(self):
        return [key for key, value in self.__dict__.items() if value]

    def modalityNames(self):
        return [key for key, value in self.__dict__.items()]

    def fuzzy_match(self, input_string):
        # If the input has been seen before, return the stored match
        if input_string in Modalities.previous_inputs:
            return Modalities.previous_inputs[input_string]

        # Get the list of modalities
        modalities = self.modalityNames()

        # Fuzzy match the input string to the modalities
        match, score = process.extractOne(input_string, modalities)

        # Interactively query the user whether the match is correct
        print(f"Is '{match}' the correct match for '{input_string}'? (y/n)")
        response = input().lower()

        # If the match is not correct, offer the list of modalities as a numbered list
        if response != 'y':
            while True:
                try:
                    print(f"Please select the correct match for '{input_string}' from the following list:")
                    for i, modality in enumerate(modalities, 1):
                        print(f"{i}: {modality}")
                    print("0: DONT USE THIS MODALITY")
                    # Wait for the user to enter a number to specify the correct match
                    correct_match_index = int(input()) - 1
                    if correct_match_index == -1:
                        break
                    if 0 <= correct_match_index < len(modalities):
                        match = modalities[correct_match_index]
                        break
                    else:
                        print("Invalid Input, please try again:")
                except Exception as e:
                    print("Invalid Input, please try again:")



        # Remember the answer the user gave
        Modalities.previous_inputs[input_string] = match

        return match



