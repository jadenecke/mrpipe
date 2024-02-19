from typing import List
from mrpipe.modalityModules import Modalities
from mrpipe.meta import loggerModule
from mrpipe.meta.PathClass import Path

logger = loggerModule.Logger()
class Session:
    def __init__(self, name, path: Path):
        self.name = name
        self.path = path
        self.modalities: List[Modalities.Modalities] = []

    def addModality(self, modality : Modalities.Modalities):
        if modality not in self.modalities:
            logger.info(f"Adding modality {modality} to {self.name}")
            self.modalities.append(modality)

