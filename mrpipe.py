#!/usr/bin/env python
import sys
import os
from mrpipe.meta import InputParser
from mrpipe.meta import LoggerModule
from mrpipe.schedueler import Pipe
from mrpipe.schedueler import PipeJob
from mrpipe.Toolboxes.submodules.setup import setup_submodules

if __name__ == '__main__':

    # setting up event logger
    logger = LoggerModule.Logger()
    logger.process("Welcome to MrPipe.")

    #setting up input arg handeling
    args = InputParser.inputParser()
    logger.setLoggerVerbosity(args)
    logger.info(str(args))

    logger.process(f'Logging level: {logger.level}')

    setup_submodules()

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
        pipe = Pipe.Pipe(args=args)
        logger.process(f'running pipe:\n{pipe}')
        pipe.run()

    elif args.mode == "config":
        logger.process("############## Config Mode #################")
        logger.info("Creating Pipe:")

        pipe = Pipe.Pipe(args=args)
        pipe.configure()

    elif args.mode == "flowchart":
        logger.process("############## Flow Chart Mode #################")
        logger.info("Creating flow charts for processing modules")

        pipe = Pipe.Pipe(args=args)
        pipe.configure(reconfigure=False, filterJobs=False)

        # Create output directory for flow charts
        flow_charts_dir = os.path.join(pipe.pathBase.pipePath, "flow_charts")
        if not os.path.exists(flow_charts_dir):
            os.makedirs(flow_charts_dir)

        pipe.create_flow_charts()
        logger.process(f"All flow charts saved to: {flow_charts_dir}")

    sys.exit()
