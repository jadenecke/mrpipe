from typing import List

from mrpipe.modalityModules.PathDicts.SubjectPaths import SubjectPaths
from mrpipe.meta import loggerModule
from mrpipe.meta.PathClass import Path
from mrpipe.modalityModules.Modalities import Modalities
import os

logger = loggerModule.Logger()
class Session:
    def __init__(self, name, path: Path):
        self.name = name
        self.path = path
        self.modalities: Modalities = None
        self.subjectPaths = SubjectPaths()
        self.pathsConfigured = False


    def addModality(self, clobber=False, **kwargs):
        if (not self.modalities) or clobber:
            logger.info(f"Adding modalities {str(kwargs)} to {self.name}")
            self.modalities = Modalities(**kwargs)

    def identifyModalities(self, suggestedModalities: dict = {}):
        dummyModality = Modalities()
        potential = os.listdir(self.path + "/unprocessed")
        matches = {}
        for name in potential:
            if name in suggestedModalities.keys():
                suggestedModality = suggestedModalities[name]
            else:
                suggestedModality = dummyModality.fuzzy_match(name)
            if not suggestedModality:
                continue
            matches[suggestedModality] = name
        logger.info(f'Identified the following modalities for {self.path}: {str(matches)}')
        self.addModality(**matches)
        if not matches:
            logger.warning(f"No modalities found for session: {self.path}")
            return None
        return matches

    def __str__(self):
        return self.name
