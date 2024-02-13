# Parsing Input arguments
import argparse
from mrpipe.meta import loggerModule
from argparse import RawTextHelpFormatter


def inputParser():
    logger = loggerModule.Logger()
    logger.process("Processing Input arguments.")

    parser = argparse.ArgumentParser(
        description='Fully automated multimodal integrative MRI pre- and postprocessing pipeline.',
    formatter_class=RawTextHelpFormatter)

    parser.add_argument(dest="mode", type=str, choices=['config', 'process', 'step'],
                        help="Mode of operation: \nconfig creates a data config for a dataset. Be aware, that config sets up everything at the same level as the input directory.\nprocess takes a configured data set and processes it.\nstep is an internal method to run a processing step. May be used for debugging if given a PipeJop directory to run a single job. Be aware that it will also run all followup steps if specified.")
    parser.add_argument(dest="input", type=str,
                        metavar="/path/to/input",
                        help="Input: Either path to data bids directory if in config or process mode or path to to PipeJop directory if in step mode.")
    parser.add_argument('-n', '--ncores', dest='ncores', type=int, nargs=1, default=1,
                        help='Number of cores to use. In the case of the SLURM scheduler these can be distributed over multiple nodes.')
    parser.add_argument('--mem', dest='mem', type=int, nargs=1, default=None,
                        help='Amount of memory in GB to use. This should not be specified unless you run into memory issues. mrpipe asks for an appropriate amount of memory based on the numbers of cores given and the particular job step.')
    parser.add_argument('-v', '--verbose', action="count", help="verbose level... repeat up to three times.")

    args = parser.parse_args()
    return args
