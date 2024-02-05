# Parsing Input arguments
import argparse
from mrpipe.meta import loggerModule


def inputParser():
    logger = loggerModule.GetLogger()
    logger.log(99, "Processing Input arguments.")

    parser = argparse.ArgumentParser(
        description='Fully automated multimodal integrative MRI pre- and postprocessing pipeline.')

    parser.add_argument("mode", type=str, nargs=1,
                        metavar="[config|process]",
                        help="Mode of operation: config creates a data config for a dataset, process takes a dataconfig and processes it.")
    parser.add_argument("input", type=str, nargs=1,
                        metavar="/path/to/input",
                        help="Input: Either path to data bids folder if in config mode or path to config yml file if in process mode.")
    parser.add_argument('-n', '--ncores', dest='ncores', type=int, nargs=1, default=1,
                        help='Number of cores to use. In the case of the SLURM scheduler these can be distributed over multiple nodes.')
    parser.add_argument('--mem', dest='mem', type=int, nargs=1, default=None,
                        help='Amount of memory in GB to use. This should not be specified unless you run into memory issues. mrpipe asks for an appropriate amount of memory based on the numbers of cores given and the particular job step.')
    parser.add_argument('-v', '--verbose', action="count", help="verbose level... repeat up to three times.")

    args = parser.parse_args()

    return args
