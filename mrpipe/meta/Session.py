from typing import List

from mrpipe.modalityModules.PathDicts.SubjectPaths import SubjectPaths
from mrpipe.meta import LoggerModule
from mrpipe.meta.PathClass import Path
from mrpipe.modalityModules.Modalities import Modalities
import os

logger = LoggerModule.Logger()
class Session:
    def __init__(self, name, path: Path):
        self.name = name
        self.path = path
        self.modalities: Modalities = None
        self.subjectPaths = SubjectPaths()
        self.pathsConfigured = False


    def addModality(self, clobber=False, **kwargs):
        if (not self.modalities) or clobber:
            if 'DontUse' in kwargs:
                kwargs.pop('DontUse')
            logger.info(f"Adding modalities {str(kwargs)} to {self.name}")
            self.modalities = Modalities(**kwargs)

    def identifyModalities(self, suggestedModalities: dict = {}):
        dummyModality = Modalities()
        # potential = os.listdir(self.path + "/unprocessed")
        potential = os.listdir(self.path)
        matches = {}
        for name in potential:
            if name in suggestedModalities.keys():
                suggestedModality = suggestedModalities[name]
            else:
                suggestedModality = dummyModality.fuzzy_match(name)

            if not suggestedModality: #if nothing was found
                continue

            if suggestedModality in matches.keys(): #check if modality is already present for that session
                logger.error(f'Modality already present in this session: {matches[suggestedModality]}. Ignoring your input.')
                #TODO implement that one can choose which modality is used for that specific subject.
            elif suggestedModality == "DontUse":
                if suggestedModality in matches.keys():
                    matches[suggestedModality].append("DontUse")
                else:
                    matches[suggestedModality] = [name]
            else:
                matches[suggestedModality] = name
        logger.info(f'Identified the following modalities for {self.path}: {str(matches)}')
        self.addModality(**matches)
        if not matches:
            logger.warning(f"No modalities found for session: {self.path}")
            return None
        return matches

    def __str__(self):
        return self.name
