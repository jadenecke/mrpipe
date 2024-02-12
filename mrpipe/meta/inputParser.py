# Parsing Input arguments
import argparse
from mrpipe.meta import loggerModule
from enum import Enum

# class MRPipeMode(Enum):
#     config = 'config'
#     process = 'process'
#     step = 'step'
#
#     def __str__(self):
#         return self.value

def inputParser():
    logger = loggerModule.Logger()
    logger.process("Processing Input arguments.")

    parser = argparse.ArgumentParser(
        description='Fully automated multimodal integrative MRI pre- and postprocessing pipeline.')

    parser.add_argument(dest="mode", type=str, choices=['config', 'process', 'step'],
                        help="Mode of operation: config creates a data config for a dataset, process takes a dataconfig and processes it. Step is an internal method to run a processing step. May be used for debugging if given a pickle file.")
    parser.add_argument(dest="input", type=str,
                        metavar="/path/to/input",
                        help="Input: Either path to data bids folder if in config mode or path to config yml file if in process mode.")
    parser.add_argument('-n', '--ncores', dest='ncores', type=int, nargs=1, default=1,
                        help='Number of cores to use. In the case of the SLURM scheduler these can be distributed over multiple nodes.')
    parser.add_argument('--mem', dest='mem', type=int, nargs=1, default=None,
                        help='Amount of memory in GB to use. This should not be specified unless you run into memory issues. mrpipe asks for an appropriate amount of memory based on the numbers of cores given and the particular job step.')
    parser.add_argument('-v', '--verbose', action="count", help="verbose level... repeat up to three times.")

    args = parser.parse_args()
    return args
