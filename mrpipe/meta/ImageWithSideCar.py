from mrpipe.meta import LoggerModule
from abc import ABC, abstractmethod
from mrpipe.meta.PathClass import Path
import os
import json

logger = LoggerModule.Logger()

class ImageWithSideCar():
    def __init__(self, imagePath: Path, jsonPath: Path):
        self.imagePath = imagePath
        self.jsonPath = jsonPath
        self.attributes = {}
        self.attributesLoaded = False
        self.jsonCorrupted = False
        if os.path.basename(self.imagePath).split(".")[0] != os.path.basename(self.jsonPath).split(".")[0]:
            logger.error("Image name and json name differ, this is an unlikely occursion. Please check whether they truely match. Processing will continue as normal though.")

    def _loadAttributesFromJson(self):
        if self.jsonPath is None:
            logger.error(f"No json ath found, returning empty")
            return False
        if not self.jsonPath.exists():
            logger.error(f"Json file does not exist, returning empty")
            return False
        logger.debug("Reading file patterns from json: {}".format(self.jsonPath))
        if len(self.attributes) != 0:
            logger.info(f"Found {len(self.attributes)} file patterns already in class. This will overwrite any existing patterns")
        try:
            with open(self.jsonPath, 'r') as file:
                self.attributes.update(json.load(file))
        except Exception as e:
            logger.error(f"Error while trying to read json file: {e}")
            self.jsonCorrupted = True
            return False
        self.attributesLoaded = True
        return True

    def getAttribute(self, name, suppressWarning=False):
        if not self.attributesLoaded:
            loadingResult = self._loadAttributesFromJson()
            if not loadingResult:
                logger.error(f"Error while trying to read json file. Maybe it does not exist or is not valid json: {self.jsonPath}; Returning None.")
                return None
        if self.jsonCorrupted:
            logger.info(f"Json file is corrupted, returning None.")
            return None
        if name in self.attributes:
            return self.attributes[name]
        else:
            if not suppressWarning:
                logger.warning(f"Attribute {name} not found in class. Returning None.")
            return None

    def __str__(self):
        return "\n".join([str(self.imagePath), str(self.jsonPath)])