import os
from mrpipe.meta import loggerModule

logger = loggerModule.Logger()

class Script:

    shebang = "#!/bin/bash"

    def __init__(self, job):
        self.scriptLines = [self.shebang, ""]
        if job:
            self.appendJob(job)

    def appendJob(self, job):
        if job:
            if type(job) is str:
                self.scriptLines.append(job)
                logger.debug(job)
            elif all(isinstance(elem, str) for elem in job):
                [(self.scriptLines.append(el), logger.debug(el)) for el in job]

    def write(self, filepath: str, clobber=False):
        if os.path.isfile(filepath) and not clobber:
            raise FileExistsError(filepath)

        logger.debug(f"Writing bash job to file: {filepath}")
        try:
            with open(filepath, 'w') as the_file:
                the_file.write(self.__str__())
        except Exception as e:
            logger.logExceptionError(f"Could not write to file: {filepath}", e)

    def __str__(self):
        return "\n".join(self.scriptLines)

