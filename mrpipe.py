#!/usr/bin/env python
import sys
from mrpipe.meta import inputParser
from mrpipe.meta import loggerModule
from mrpipe.schedueler import Slurm
from mrpipe.schedueler import Bash
from mrpipe.schedueler import Pipe
from mrpipe.schedueler import PipeJob


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
        # logger.info("############## Processing Mode #################")
        # x = Slurm.Scheduler("python3 scripts/subprocessSpawnerTest.py", cpusPerTask=1, cpusTotal=6, memPerCPU=2.5, minimumMemPerNode=8)
        # # x.salloc(attach=True)
        # x.sbatch()
        #
        # bashjob = Bash.Script(["python3 scripts/subprocessSpawnerTest.py", "python3 scripts/subprocessSpawnerTest.py"])
        # logger.info(str(bashjob))
        # bashjob.write("/test.txt")
        #
        # pipeJob = PipeJob.PipeJob(name="TestJob", job=x)
        # # logger.info(str(pipeJob))
        # pipeJob.pickleJob()
        #
        # pipeJobLoaded = PipeJob.PipeJob.fromPickled("TestJob/PipeJob.pkl")
        # logger.info(str(pipeJobLoaded))
        #final exit

        jobTasks = ["scripts/sleep.sh"] * 10
        p1 = PipeJob.PipeJob(name="firstSleep", job=Slurm.Scheduler(job=jobTasks, cpusTotal=6, memPerCPU=2, minimumMemPerNode=4, cpusPerTask=1, clobber=True), jobDir=args.input)
        p2 = PipeJob.PipeJob(name="secondSleep", job=Slurm.Scheduler(job=jobTasks, cpusTotal=10, memPerCPU=2, minimumMemPerNode=4, cpusPerTask=1, clobber=True), jobDir=args.input)
        p1.setNextJob(p2)
        p2.setDependencies(p1)
        p2.setNextJob(p1)
        p2.pickleJob()
        p1.pickleJob()
        p1.runJob()

    elif args.mode == "config":
        logger.info("############## Config Mode #################")
    sys.exit()
