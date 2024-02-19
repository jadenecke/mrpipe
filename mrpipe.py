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
        taskList = [Sleep.Sleep(10)] * 10
        basePaths = PathBase(os.path.abspath(os.path.join(args.input, "..")),
                                                     os.path.basename(args.input))

        basePaths.createDirs()
        pipe = Pipe.Pipe(args=args)
        p1 = PipeJob.PipeJob(name="firstSleep",
                             job=Slurm.Scheduler(taskList=taskList, cpusTotal=6, memPerCPU=2, minimumMemPerNode=4,
                                                 cpusPerTask=1, clobber=True), jobDir=basePaths.pipeJobPath,
                             verbose=args.verbose)
        p2 = PipeJob.PipeJob(name="secondSleep",
                             job=Slurm.Scheduler(taskList=taskList, cpusTotal=10, memPerCPU=2, minimumMemPerNode=4,
                                                 cpusPerTask=1, clobber=True), jobDir=basePaths.pipeJobPath,
                             verbose=args.verbose)
        p3 = PipeJob.PipeJob(name="thirdSleep",
                             job=Slurm.Scheduler(taskList=taskList, cpusTotal=10, memPerCPU=2, minimumMemPerNode=4,
                                                 cpusPerTask=1, clobber=True), jobDir=basePaths.pipeJobPath,
                             verbose=args.verbose)
        p4 = PipeJob.PipeJob(name="fourthSleep",
                             job=Slurm.Scheduler(taskList=taskList, cpusTotal=10, memPerCPU=2, minimumMemPerNode=4,
                                                 cpusPerTask=1, clobber=True), jobDir=basePaths.pipeJobPath,
                             verbose=args.verbose)
        p5 = PipeJob.PipeJob(name="fifthSleep",
                             job=Slurm.Scheduler(taskList=taskList, cpusTotal=10, memPerCPU=2, minimumMemPerNode=4,
                                                 cpusPerTask=1, clobber=True), jobDir=basePaths.pipeJobPath,
                             verbose=args.verbose)
        p2.setDependencies(p1)
        p3.setDependencies(p1)
        p5.setDependencies(p4)
        pipe.appendJob([p5, p4, p1, p3, p2])
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
