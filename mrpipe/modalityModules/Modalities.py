from mrpipe.meta.PathCollection import PathCollection
from fuzzywuzzy import process
from mrpipe.meta import LoggerModule

logger = LoggerModule.Logger()


class Modalities(PathCollection):
    """
        The Modalities class is a subclass of PathCollection. It represents a collection of different imaging modalities.

        Attributes:
            previous_inputs (dict): A dictionary to store previously seen inputs and their matches.
            T1w, t1map, rsfmri, taskfmri, dwi, flair, megre, T2w, t2map, swi, flash, fieldmap, pet_fdg, pet_tau, pet_amyloid, pet_synaptic, protonDensity, localizer (str): Name in paths of the respective imaging modalities.

        Methods:
            available_modalities(): Returns a list of modalities that have been set (i.e., are not None).
            modalityNames(): Returns a list of all modality names.
            adjustModalities(modalitySet): Adjusts the modality names based on a provided mapping (modalitySet), e.g. after the modalities have been changed on disk by the user in a yaml file.
            fuzzy_match(input_string): Performs a fuzzy match of an input string to the available modalities. If the input string has been seen before, it returns the stored match. Otherwise, it interactively queries the user to confirm the match or select the correct match from a list.
        """
    previous_inputs = {}

    def __init__(self, T1w=None, t1map=None, rsfmri=None, taskfmri=None, dwi=None, flair=None, megre=None, T2w=None,
                 t2map=None, swi=None, flash=None, fieldmap=None, protonDensity=None, localizer=None, pet_av45=None, pet_nav4694=None,
                 pet_fbb=None, pet_fmm=None, pet_pib=None, pet_av1451=None, pet_ro948=None, pet_pi2620=None, pet_mk6240=None,
                 pet_fmm_early=None, pet_pi2620_early=None, pet_fbb_early=None, pet_av45_early=None,  hippocampus=None, pet_fdg=None,
                 asl=None):
        # IMPORTANT: must have the same names as subjectPath corresponding Elements
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
        self.pet_av45 = pet_av45
        self.pet_nav4694 = pet_nav4694
        self.pet_fbb = pet_fbb
        self.pet_fmm = pet_fmm
        self.pet_pib = pet_pib
        self.pet_av1451 = pet_av1451
        self.pet_ro948 = pet_ro948
        self.pet_pi2620 = pet_pi2620
        self.pet_mk6240 = pet_mk6240
        self.hippocampus = hippocampus
        self.pet_fmm_early = pet_fmm_early
        self.pet_pi2620_early = pet_pi2620_early
        self.pet_fbb_early = pet_fbb_early
        self.pet_av45_early = pet_av45_early
        self.pet_fdg = pet_fdg
        self.asl = asl

        #ignore DontUse input

    def available_modalities(self):
        return [key for key, value in self.__dict__.items() if value]

    def _available_modalities_dict(self):
        return dict([(key, value) for key, value in self.__dict__.items() if value])

    def modalityNames(self):
        return [key for key, value in self.__dict__.items()]

    def removeModality(self, modalityName):
        if hasattr(self, modalityName):
            self.__setattr__(modalityName, None)
        else:
            logger.error("You tried to remove a modality which is not a modality: {}".format(modalityName))

    def adjustModalities(self, modalitySet):
        items = list(self.__dict__.items())  # Create a copy of the items
        for key, value in items:
            if value:
                # logger.critical(str(type(value)) + "  //  " + key + ": " + str(value))
                new_key = modalitySet.get(value)
                if new_key and new_key != key:
                    self.__dict__[modalitySet[value]] = value
                    self.__dict__[key] = None
                    logger.debug(f"Adjusted modality for {value} from {key} to {new_key}")

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
                        match = "DontUse"
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


    def __str__(self):
        return str(self._available_modalities_dict())




