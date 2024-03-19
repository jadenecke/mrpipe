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
    parser.add_argument('-n', '--name', dest="name", type=str,
                        metavar="mrpipe", default=None,
                        help="Name of the pipeline, if not specified, will use the name of the parent directory of input. Only regarded in config mode.")
    parser.add_argument('-c', '--ncores', dest='ncores', type=int, default=1,
                        help='Number of cores to use. In the case of the SLURM scheduler these can be distributed over multiple nodes.')
    parser.add_argument('--mem', dest='mem', type=int, default=None,
                        help='Amount of memory per Node in GB to use. This should not be specified unless you run into memory issues. mrpipe asks for an appropriate amount of memory based on the numbers of cores given and the particular job step.')
    parser.add_argument('--subjectDescriptor', dest="subjectDescriptor", type=str, metavar="sub-*", default="sub-*",
                        help="Subject matching pattern. Used to identify subjects in input directory.")
    parser.add_argument('--sessionDescriptor', dest="sessionDescriptor", type=str, metavar="ses-*", default="ses-*",
                        help="Session matching pattern. Used to identify sessions in subject directories.")
    parser.add_argument('--dataStructure', dest="dataStructure", type=str, metavar="sub/ses/modality", default="sub/ses/mod",
                        help="data structure matching pattern. Defines in which order subject, session, and modality are stored. Must be a combination of (sub,ses,mod) seperated by / and must not contain anything else. If no data structure is specified, the default is sub/ses/modality.")
    parser.add_argument('-v', '--verbose', action="count", help="verbose level... repeat up to three times.")
    parser.add_argument('--modalityBeforeSession', dest="modalityBeforeSession", action="store_true", help="Whether Modality comes before session or not. Defaults to Subject/Session/Modality.")
    args = parser.parse_args()
    return args
