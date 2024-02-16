from typing import List
from mrpipe.modalityModules import Modalities
from mrpipe.meta import loggerModule

logger = loggerModule.Logger()
class Session:
    def __init__(self, name, subject):
        self.name = name
        self.modalities: List[Modalities.Modalities] = []

    def addModality(self, modality : Modalities.Modalities):
        if modality not in self.modalities:
            logger.debug(f"Adding modality {modality} to {self.name}")
            self.modalities.append(modality)

