import os

import mrpipe.Helper as helper
from mrpipe.meta import loggerModule
from typing import List

logger = loggerModule.Logger()

def _add_element(mode, target, element, **kwargs):
    if mode == list.append:
        mode(target, element)
    elif mode == list.insert:
        mode(target, kwargs.get('index', 0), element)
    else:
        mode(target, element, **kwargs)

class Script:

    shebang = "#!/bin/bash"

    def __init__(self, job=None):
        self.jobLines = []
        self.setupLines = []
        self.postscriptLines = []
        if job:
            self.appendJob(job)

        #non settable
        self.path = ""

    def appendJob(self, job):
        if job:
            job = Helper.ensure_list(job)
            for el in job:
                if not isinstance(el, str):
                    logger.error(f"Could not add job to script, unknown type (not str or [str]): {type(el)}")
                logger.info(el)
                self.jobLines.append(el)

    def addSetup(self, setupLines, add=False, mode=List.append, **kwargs):
        if self.setupLines and not add:
            logger.error(f"Could not add setup lines to script, setup lines already set:\n{self.setupLines}")
        else:
            setupLines = Helper.ensure_list(setupLines)
            for el in setupLines:
                if not isinstance(el, str):
                    logger.error(f"Could not add job to script, unknown type (not str or [str]): {type(el)}")
                logger.info(el)
                _add_element(mode, self.setupLines, el, **kwargs)



    def addPostscript(self, postscriptLines, add=False, mode=List.append, *args, **kwargs):
        if self.postscriptLines and not add:
            logger.error(f"Could not add postscript lines to script, postscript lines already set:\n{self.postscriptLines}")
        else:
            postscriptLines = Helper.ensure_list(postscriptLines)
            for el in postscriptLines:
                if not isinstance(el, str):
                    logger.error(f"Could not add postscript Lines, unknown type (not str or [str]): {type(el)} in {type()}")
                logger.info(el)
                _add_element(mode, self.postscriptLines, el, **kwargs)

    def write(self, filepath: str, clobber=False):
        if os.path.isfile(filepath) and not clobber:
            raise FileExistsError(filepath)

        logger.info(f"Writing bash job to file: {filepath}")
        try:
            with open(filepath, 'w') as file:
                for line in [self.shebang, ""] + self.setupLines + [""] + self.jobLines + [""] + self.postscriptLines:
                    file.write("%s\n" % line)
            self.path = filepath
        except Exception as e:
            logger.logExceptionError(f"Could not write to file: {filepath}", e)

    def __str__(self):
        return "\n".join(self.jobLines)



