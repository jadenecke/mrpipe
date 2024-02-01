import logging
import logging.handlers

#mostly from https://gist.github.com/olooney/8155400

def createLogger():
    logger = logging.getLogger('mrpipe')
    logging.addLevelName(level=99, levelName="Process Info")
    consoleLogger = logging.StreamHandler()
    consoleLogger.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s](%(name)s:%(funcName)s:%(lineno)d): %(message)s'))
    logger.addHandler(consoleLogger)

    return logger


def setLoggerVerbosity(args):
    logger = logging.getLogger('mrpipe')
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