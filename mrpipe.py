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
    logger.debug(str(args))

    logger.setLoggerVerbosity(args)
    logger.process(f'Logging level: {logger.level}')
    x = Slurm.Scheduler("python3 scripts/subprocessSpawnerTest.py", SLURM_ntasks=6, SLURM_nnodes=3)
    x.salloc(attach=True)
<<<<<<< HEAD
    # x.sbatch()
=======
    x.sbatch()
>>>>>>> f414ccc5664e0a783a62c564f9b2a33132d14f9b

    bashjob = Bash.Script(["python3 scripts/subprocessSpawnerTest.py", "python3 scripts/subprocessSpawnerTest.py"])
    logger.info(str(bashjob))
    bashjob.write("/test.txt")

    pipeJob = Pipe.PipeJob(name="Test Job", job=x, picklePath="test.pkl")
    # logger.info(str(pipeJob))
    pipeJob.pickleJob()
    logger.info("############## Loading Pickle #################")
    pipeJobLoaded = Pipe.PipeJob.fromPickled("test.pkl")
    # logger.info(str(pipeJobLoaded))
    #final exit
    sys.exit()  # next section explains the use of sys.exit
