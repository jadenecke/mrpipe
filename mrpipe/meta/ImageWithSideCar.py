from mrpipe.meta import LoggerModule
from abc import ABC, abstractmethod
from mrpipe.meta.PathClass import Path
import os
import json

logger = LoggerModule.Logger()

class ImageWithSideCar(ABC):
    def __init__(self, imagePath: Path, jsonPath: Path):
        self.imagePath = imagePath
        self.jsonPath = jsonPath
        self.attributes = {}
        self.attributesLoaded = False
        if os.path.basename(self.imagePath).split(".")[0] != os.path.basename(self.jsonPath).split(".")[0]:
            logger.error("Image name and json name differ, this is an unlikely occursion. Please check whether they truely match. Processing will continue as normal though.")

    def loadAttributesFromJson(self):
        if self.jsonPath is None:
            logger.error(f"No json ath found, returning empty")
            return False
        if not self.jsonPath.exists():
            logger.error(f"Json file does not exist, returning empty")
            return False
        logger.debug("Reading file patterns from json: {}".format(self.jsonPath))
        if len(self.attributes) != 0:
            logger.info(f"Found {len(self.attributes)} file patterns already in class. This will overwrite any existing patterns")
        with open(self.jsonPath, 'r') as file:
            self.attributes.update(json.load(file))
        return True

    def getAttribute(self, name):
        if not self.attributesLoaded:
            self.loadAttributesFromJson()
        if name in self.attributes:
            return self.attributes[name]
        else:
            logger.error(f"Attribute {name} not found in class. Returning None.")
            return None