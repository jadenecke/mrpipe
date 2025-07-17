# Parsing Input arguments
import argparse
from mrpipe.meta import LoggerModule
from argparse import RawTextHelpFormatter


def inputParser():
    logger = LoggerModule.Logger()
    logger.process("Processing Input arguments.")

    parser = argparse.ArgumentParser(
        description='Fully automated multimodal integrative MRI pre- and postprocessing pipeline.',
        formatter_class=RawTextHelpFormatter)

    parser.add_argument(dest="mode", type=str, choices=['config', 'process', 'step', 'flowchart'],
                        help="Mode of operation: \nconfig creates a data config for a dataset. Be aware, that config sets up everything at the same level as the input directory.\nprocess takes a configured data set and processes it.\nstep is an internal method to run a processing step. May be used for debugging if given a PipeJop directory to run a single job. Be aware that it will also run all followup steps if specified.\nflowchart generates flow charts for processing modules showing tasks, input/output files, and dependencies.")
    parser.add_argument(dest="input", type=str,
                        metavar="/path/to/input",
                        help="Input: Either path to data bids directory if in config or process mode or path to to PipeJop directory if in step mode.")
    parser.add_argument('-n', '--name', dest="name", type=str,
                        metavar="mrpipe", default=None,
                        help="Name of the pipeline, if not specified, will use the name of the parent directory of input. Only regarded in config mode.")
    parser.add_argument('-c', '--ncores', dest='ncores', type=int, default=1,
                        help='Number of cores to use. In the case of the SLURM scheduler these can be distributed over multiple nodes.')
    parser.add_argument('-g', '--ngpus', dest='ngpus', type=int, default=0,
                        help='Number of GPUs to use. In the case of the SLURM scheduler these can be distributed over multiple nodes. Default is 0, even though some steps may benefit/require GPU processing, so please specifiy if GPUs are available, even if you are unsure whether the program will use them. They will only be reserved if they are required.')
    parser.add_argument('--mem', dest='mem', type=int, default=None,
                        help='Amount of memory per Node in GB to use. This should not be specified unless you run into memory issues. mrpipe asks for an appropriate amount of memory based on the numbers of cores given and the particular job step.')
    parser.add_argument('-s', '--scratch', dest="scratch", type=str, metavar=None, default=None,
                        help="Scratch directory, must exist on every compute node")
    parser.add_argument('--subjectDescriptor', dest="subjectDescriptor", type=str, metavar="sub-*", default="sub-*",
                        help="Subject matching pattern. Used to identify subjects in input directory.")
    parser.add_argument('--sessionDescriptor', dest="sessionDescriptor", type=str, metavar="ses-*", default="ses-*",
                        help="Session matching pattern. Used to identify sessions in subject directories.")
    parser.add_argument('--dataStructure', dest="dataStructure", type=str, metavar="sub/ses/modality", default="sub/ses/mod",
                        help="data structure matching pattern. Defines in which order subject, session, and modality are stored. Must be a combination of (sub,ses,mod) seperated by / and must not contain anything else. If no data structure is specified, the default is sub/ses/modality.")
    parser.add_argument('-v', '--verbose', action="count", help="verbose level... repeat up to three times.", default=0, dest="verbose")
    parser.add_argument('--modalityBeforeSession', dest="modalityBeforeSession", action="store_true", help="Whether Modality comes before session or not. Defaults to Subject/Session/Modality.")
    parser.add_argument('--writeSubjectPaths', dest="writeSubjectPaths", action="store_true",
                        help="Writes all subject paths as a json file to disk, including Path properties, e.g. file sorting for echo numbers etc. Useful for debugging. ")
    parser.add_argument('--module', dest="module_name", type=str, default=None,
                        help="Name of the specific processing module to generate a flow chart for. If not specified, flow charts will be generated for all modules. Only used in flowchart mode.")
    args = parser.parse_args()
    return args
