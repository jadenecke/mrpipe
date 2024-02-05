import logging
import logging.handlers

#mostly from https://gist.github.com/olooney/8155400
loggerName = "mrpipe"

def createLogger():
    logger = logging.getLogger(loggerName)
    logging.addLevelName(level=99, levelName="Process Info")
    consoleLogger = logging.StreamHandler()
    consoleLogger.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s](%(name)s:%(funcName)s:%(lineno)d): %(message)s'))
    logger.addHandler(consoleLogger)

    logger = _decorateLogger()
    return logger

def GetLogger():
    logger = logging.getLogger(loggerName)
    logger = _decorateLogger()
    return logger

def _decorateLogger(logger):
    logger.LogExceptionError = LogExceptionError
    logger.LogExceptionCritical = LogExceptionCritical
    logger.DEBUG = logging.DEBUG
    logger.ERROR = logging.ERROR
    logger.WARNING = logging.WARNING
    logger.CRITICAL = logging.CRITICAL
    logger.INFO = logging.INFO
    return logger

def setLoggerVerbosity(args):
    logger = logging.getLogger(loggerName)
    # set verbosity
    if not args.verbose:
        logger.setLevel('ERROR')
    elif args.verbose == 1:
        logger.setLevel('WARNING')
    elif args.verbose == 2:
        logger.setLevel('INFO')
    elif args.verbose >= 3:
        logger.setLevel('DEBUG')
    else:
        logger.critical("UNEXPLAINED NEGATIVE COUNT!")

def LogExceptionError(self, message, e):
    self.error(message)
    self.error(str(e))
    self.error('Stacktrace: ')
    self.error(str(e.with_traceback()))

def LogExceptionCritical(self, message, e):
    self.critical(message)
    self.critical(str(e))
    self.critical('Stacktrace: ')
    self.critical(str(e.with_traceback()))