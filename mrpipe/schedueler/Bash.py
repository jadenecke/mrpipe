import os
from mrpipe.meta import loggerModule

logger = loggerModule.Logger()

class Script:

    shebang = "#!/bin/bash"


    def __init__(self, job):
        if job:
            self.appendJob(job)

    def appendJob(self, job):
        self.scriptLines = []
        if job:
            if isinstance(job, list):
                for el in job:
                    logger.debug(el)
                    self.scriptLines.append(el)
            elif isinstance(job, str):
                logger.debug(job)
                self.scriptLines.append(job)
            else:
                logger.error(f"Could not add job to script, unknown type {job}")
                return

    def write(self, filepath: str, clobber=False):
        if os.path.isfile(filepath) and not clobber:
            raise FileExistsError(filepath)

        logger.debug(f"Writing bash job to file: {filepath}")
        try:
            with open(filepath, 'w') as the_file:
                the_file.write(self.scriptLines)
        except Exception as e:
            logger.logExceptionError(f"Could not write to file: {filepath}", e)

    def __str__(self):
        return "; ".join(self.scriptLines)

    def scriptString(self):
        return "\n".join([self.shebang, ""] + self.scriptLines)

