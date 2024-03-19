#!/usr/bin/env python
import sys
import os
from mrpipe.meta import inputParser
from mrpipe.meta import loggerModule
from mrpipe.schedueler import Slurm
from mrpipe.schedueler import Pipe
from mrpipe.schedueler import PipeJob
from mrpipe.modalityModules.PathDicts.BasePaths import PathBase

from mrpipe.Toolboxes.tester import Sleep

if __name__ == '__main__':
    print("Welcome to MrPipe.")

    # setting up event logger
    logger = loggerModule.Logger()

    #setting up input arg handeling
    args = inputParser.inputParser()
    logger.setLoggerVerbosity(args)
    logger.info(str(args))

    logger.process(f'Logging level: {logger.level}')

    if args.mode == "step":
        logger.debug("############## Step Mode #################")
        job = PipeJob.PipeJob.fromPickled(args.input)
        if job:
            job.runJob()
        else:
            logger.critical(f"Job Step could not be loaded, please check error above.")
            logger.critical(f"Probably the .pkl file does not exist under the following path: {args.input}")

    elif args.mode == "process":
        logger.debug("############## Processing Mode #################")

        # basePaths = PathBase(os.path.abspath(os.path.join(args.input, "..")),
        #                                              os.path.basename(args.input))
        #
        # basePaths.createDirs()
        pipe = Pipe.Pipe(args=args)

        logger.process(f'Pipe before configure:\n{pipe}')
        logger.process("############ configuring ##############")
        pipe.configure()
        logger.process(f'Pipe after configure:\n{pipe}')
        logger.process(f'running pipe:\n{pipe}')
        pipe.run()

    elif args.mode == "config":
        logger.process("############## Config Mode #################")
        logger.info("Creating Pipe:")

        pipe = Pipe.Pipe(args=args)
        pipe.configure()

    sys.exit()
