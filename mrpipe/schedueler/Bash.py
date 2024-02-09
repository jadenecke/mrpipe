import os
from mrpipe.meta import loggerModule
from typing import List

logger = loggerModule.Logger()

class Script:

    shebang = "#!/bin/bash"


    def __init__(self, job):
        self.jobLines = []
        self.setupLines = []
        self.postscriptLines = []
        if job:
            self.appendJob(job)

    def appendJob(self, job):
        if job:
            if isinstance(job, list):
                for el in job:
                    logger.debug(el)
                    self.jobLines.append(el)
            elif isinstance(job, str):
                logger.debug(job)
                self.jobLines.append(job)
            else:
                logger.error(f"Could not add job to script, unknown type {type(job)}")
                return

    def addSetup(self, setupLines):
        if self.setupLines:
            logger.error(f"Could not add setup lines to script, setup lines already set:\n{self.setupLines}")
        else:
            if isinstance(setupLines, list):
                for el in setupLines:
                    logger.debug(el)
                    self.setupLines.append(el)
            elif isinstance(setupLines, str):
                logger.debug(setupLines)
                self.setupLines.append(setupLines)
            else:
                logger.error(f"Could not add setup lines to script, unknown type {type(setupLines)}")
                return

    def addPostscript(self, postscriptLines):
        if self.postscriptLines:
            logger.error(f"Could not add postscript lines to script, postscript lines already set:\n{self.postscriptLines}")
        else:
            if isinstance(postscriptLines, list):
                for el in postscriptLines:
                    logger.debug(el)
                    self.postscriptLines.append(el)
            elif isinstance(postscriptLines, str):
                logger.debug(postscriptLines)
                self.postscriptLines.append(postscriptLines)
            else:
                logger.error(f"Could not add postscript lines to script, unknown type {type(postscriptLines)}")
                return

    def write(self, filepath: str, clobber=False):
        if os.path.isfile(filepath) and not clobber:
            raise FileExistsError(filepath)

        logger.debug(f"Writing bash job to file: {filepath}")
        try:
            with open(filepath, 'w') as file:
                file.write([self.shebang, ""])
                file.write(self.setupLines)
                file.write(self.jobLines)
                file.write(self.postscriptLines)
        except Exception as e:
            logger.logExceptionError(f"Could not write to file: {filepath}", e)

    def __str__(self):
        return "; ".join(self.jobLines)

    # def scriptString(self):
    #     return "\n".join([self.shebang, ""] + self.jobLines)

