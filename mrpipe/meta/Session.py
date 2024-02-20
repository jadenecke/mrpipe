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
        if (not self.modalities) or clobber:
            logger.info(f"Adding modalities {str(kwargs)} to {self.name}")
            self.modalities = Modalities.Modalities(**kwargs)


    # TODO: The paths need to go somewhere, idealy in such a way that the IDE parser can identify them.
    #  They also need to be able to change after the pipe reconfigures. As they vary per session I think it is best to add them to the Session.
    #  I think (at the moment) the best approach would be to have a Session path collection with all the modality path collections.
    #  They maybe should get an attribute that states wether they are available and a function which initializes them. Then it might be possible that the path dicts are known to the IDE, but are only fixed at runtime. Dunno, sound wierd.


    def __str__(self):
        return self.name
