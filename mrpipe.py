#!/usr/bin/env python
import sys
from mrpipe.meta import inputParser
from mrpipe.meta import loggerModule
from mrpipe.schedueler import Slurm



#logger = logging.Lo

if __name__ == '__main__':
    print("Running main.")

    # setting up event logger
    logger = loggerModule.createLogger()

    #setting up input arg handeling
    args = inputParser.inputParser()
    logger.debug(args)

    loggerModule.setLoggerVerbosity(args)
    logger.log(99, f'Logging level: {logger.level}')
    x = Slurm.Scheduler("python3 scripts/subprocessSpawnerTest.py", SLURM_ntasks=6, SLURM_nnodes=3)
    x.salloc(attach=True)
    x.sbatch()
    #final exit
    sys.exit()  # next section explains the use of sys.exit
