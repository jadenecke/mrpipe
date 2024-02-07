import logging
import logging.handlers
import traceback
import inspect

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
        self._consoleLogger.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s](%(name)s:%(lineno)d): %(message)s'))
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
        self.logger.error(f'({inspect.stack()[1].function}): {message}')
        self.logger.error(str(e))
        # self.error('Stacktrace: ')
        # self.error(str(e.with_traceback(None)))
        for m in traceback.format_exc().split("\n"):
            self.logger.error(m)

    def logExceptionCritical(self, message, e):
        self.logger.critical(f'({inspect.stack()[1].function}): {message}')
        self.logger.critical(str(e))
        for m in traceback.format_exc().split("\n"):
            self.logger.critical(m)

    def info(self, message):
        for line in "\n".join(message).split("\n"):
            self.logger.info(f'({inspect.stack()[1].function}): {line}')


    def debug(self, message):
        for line in "\n".join(message).split("\n"):
            self.logger.debug(f'({inspect.stack()[1].function}): {line}')

    def warning(self, message):
        for line in "\n".join(message).split("\n"):
            self.logger.warning(f'({inspect.stack()[1].function}): {line}')

    def error(self, message):
        for line in "\n".join(message).split("\n"):
            self.logger.error(f'({inspect.stack()[1].function}): {line}')

    def critical(self, message):
        for line in "\n".join(message).split("\n"):
            self.logger.critical(f'({inspect.stack()[1].function}): {line}')

    def process(self, message):
        for line in "\n".join(message).split("\n"):
            self.logger.log(level=99, msg=f'({inspect.stack()[1].function}): {line}')


