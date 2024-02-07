import logging
import logging.handlers
import traceback
import inspect
from itertools import chain

# mostly from https://gist.github.com/olooney/8155400
# and https://stackoverflow.com/questions/6760685/what-is-the-best-way-of-implementing-singleton-in-python
class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


#Python3
class Logger(metaclass=Singleton):

    loggerName = "mrpipe"

    def __init__(self):
        self.logger = logging.getLogger(self.loggerName)
        logging.addLevelName(level=99, levelName="Process Info")
        self._consoleLogger = logging.StreamHandler()
        self._consoleLogger.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s](%(name)s:%(lineno)d:%(message)s'))
        self.logger.addHandler(self._consoleLogger)

        self._decorateLogger()

    def _decorateLogger(self):
        # self.logger.LogExceptionError = LogExceptionError
        # self.logger.LogExceptionCritical = LogExceptionCritical
        self.DEBUG = logging.DEBUG
        self.ERROR = logging.ERROR
        self.WARNING = logging.WARNING
        self.CRITICAL = logging.CRITICAL
        self.INFO = logging.INFO
        self.level = self.logger.level


    def setLoggerVerbosity(self, args):
        # set verbosity
        if not args.verbose:
            self.logger.setLevel('ERROR')
        elif args.verbose == 1:
            self.logger.setLevel('WARNING')
        elif args.verbose == 2:
            self.logger.setLevel('INFO')
        elif args.verbose >= 3:
            self.logger.setLevel('DEBUG')
        else:
            self.logger.critical("UNEXPLAINED NEGATIVE COUNT!")
        self.level = self.logger.level

    def logExceptionError(self, message, e):
        self._processMessage(message, self.logger.error)
        self._processMessage(str(e), self.logger.error)
        self._processMessage(traceback.format_exc(), self.logger.error)

    def logExceptionCritical(self, message, e):
        self._processMessage(message, self.logger.critical)
        self._processMessage(str(e), self.logger.critical)
        self._processMessage(traceback.format_exc(), self.logger.critical)

    def info(self, message):
        self._processMessage(message, self.logger.info)


    def debug(self, message):
        self._processMessage(message, self.logger.debug)

    def warning(self, message):
        self._processMessage(message, self.logger.warning)

    def error(self, message):
        self._processMessage(message, self.logger.error)

    def critical(self, message):
        self._processMessage(message, self.logger.critical)

    def process(self, message):
        self._processMessage(message, self.logger.log, level=99)

    def _processMessage(self, input, logFun, **kwargs):
        if isinstance(input, list):
            sl = [s.split("\n") for s in input]
            sl = list(chain.from_iterable(sl))
        elif isinstance(input, str):
            sl = input.split("\n")
        else:
            self.logger.error("Invalid input! Please provide a string or a list of strings.")
            return
        for s in sl:
            logFun(msg=f'{inspect.stack()[2].function}): {s}', **kwargs)
