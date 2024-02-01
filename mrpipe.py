#!/usr/bin/env python
import sys
from mrpipe.meta import inputParser
from mrpipe.meta import loggerModule



#logger = logging.Lo

if __name__ == '__main__':
    print("Running main.")

    # setting up event logger
    logger = loggerModule.createLogger()

    #setting up input arg handeling
    args = inputParser.inputParser()
    print(args)

    loggerModule.setLoggerVerbosity(args)

    #final exit
    sys.exit()  # next section explains the use of sys.exit
