#!/usr/bin/env python
import sys
import os
from mrpipe.meta import inputParser
from mrpipe.meta import loggerModule
from mrpipe.schedueler import Slurm
from mrpipe.schedueler import Pipe
from mrpipe.schedueler import PipeJob
from mrpipe.modalityModules.PathDicts import BasePaths
from mrpipe.modalityModules.PathDicts import T1Paths

from mrpipe.Toolboxes.tester import Sleep

if __name__ == '__main__':
    print("Running main.")

    # setting up event logger
    logger = loggerModule.Logger()

    #setting up input arg handeling
    args = inputParser.inputParser()
    logger.setLoggerVerbosity(args)
    logger.debug(str(args))

    logger.process(f'Logging level: {logger.level}')
    logger.process(str(args.mode))

    if args.mode == "step":
        logger.info("############## Step Mode #################")
        job = PipeJob.PipeJob.fromPickled(args.input)
        if job:
            job.runJob()
        else:
            logger.critical(f"Job Step could not be loaded, please check error above.")
            logger.critical(f"Probably the .pkl file does not exist under the following path: {args.input}")

    elif args.mode == "process":
        logger.info("############## Processing Mode #################")
        taskList = [Sleep.Sleep(10)] * 10
        basePaths = BasePaths.PathBase(os.path.abspath(os.path.join(args.input, "..")),
                                                     os.path.basename(args.input))

        basePaths.createDirs()
        pipe = Pipe.Pipe("sleepPipe", pathDictBase=basePaths)
        p1 = PipeJob.PipeJob(name="firstSleep",
                             job=Slurm.Scheduler(taskList=taskList, cpusTotal=6, memPerCPU=2, minimumMemPerNode=4,
                                                 cpusPerTask=1, clobber=True), jobDir=basePaths["PipeJobPath"],
                             verbose=args.verbose)
        p2 = PipeJob.PipeJob(name="secondSleep",
                             job=Slurm.Scheduler(taskList=taskList, cpusTotal=10, memPerCPU=2, minimumMemPerNode=4,
                                                 cpusPerTask=1, clobber=True), jobDir=basePaths["PipeJobPath"],
                             verbose=args.verbose)
        p3 = PipeJob.PipeJob(name="thirdSleep",
                             job=Slurm.Scheduler(taskList=taskList, cpusTotal=10, memPerCPU=2, minimumMemPerNode=4,
                                                 cpusPerTask=1, clobber=True), jobDir=basePaths["PipeJobPath"],
                             verbose=args.verbose)
        p4 = PipeJob.PipeJob(name="fourthSleep",
                             job=Slurm.Scheduler(taskList=taskList, cpusTotal=10, memPerCPU=2, minimumMemPerNode=4,
                                                 cpusPerTask=1, clobber=True), jobDir=basePaths["PipeJobPath"],
                             verbose=args.verbose)
        p5 = PipeJob.PipeJob(name="fifthSleep",
                             job=Slurm.Scheduler(taskList=taskList, cpusTotal=10, memPerCPU=2, minimumMemPerNode=4,
                                                 cpusPerTask=1, clobber=True), jobDir=basePaths["PipeJobPath"],
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
        logger.info("############## Config Mode #################")
        basePaths = BasePaths.PathBase(os.path.abspath(os.path.join(args.input, "..")),
                                           os.path.basename(args.input))
        t1Paths = T1Paths.PathDictT1("sub-001", ses="ses-01", basepaths=basePaths)

        logger.info(str(basePaths))
        logger.info(str(t1Paths))

        logger.critical(str(t1Paths.bids_processed.T1w))

        t1Paths.bids_processed.to_yaml(filepath=basePaths.PipePath + "t1_bids_process.yaml")
        basePaths.to_yaml(filepath=basePaths.PipePath + "basepaths.yaml")




    sys.exit()
