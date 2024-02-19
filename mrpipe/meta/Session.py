from typing import List
from mrpipe.modalityModules import Modalities
from mrpipe.meta import loggerModule
from mrpipe.meta.PathClass import Path

logger = loggerModule.Logger()
class Session:
    def __init__(self, name, path: Path):
        self.name = name
        self.path = path
        self.modalities: Modalities.Modalities = None

    def addModality(self, clobber=False, **kwargs):
        if self.modalities and not clobber:
            logger.info(f"Adding modalities {str(kwargs)} to {self.name}")
            self.modalities = Modalities.Modalities(kwargs)

