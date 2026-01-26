# Parsing Input arguments
import argparse
from mrpipe.meta import LoggerModule
from argparse import RawTextHelpFormatter
import sys
import os


def inputParser():
    logger = LoggerModule.Logger()
    logger.process("Processing Input arguments.")

    parser = argparse.ArgumentParser(
        description='Fully automated multimodal integrative MRI pre- and postprocessing pipeline.',
        formatter_class=RawTextHelpFormatter)

    parser.add_argument(dest="mode", type=str, choices=['config', 'process', 'step', 'flowchart', 'scriptexport'],
                        help="Mode of operation: \nconfig creates a data config for a dataset. Be aware, that config sets up everything at the same level as the input directory.\nprocess takes a configured data set and processes it.\nstep is an internal method to run a processing step. May be used for debugging if given a PipeJop directory to run a single job. Be aware that it will also run all followup steps if specified.\nflowchart generates flow charts for processing modules showing tasks, input/output files, and dependencies.\nscriptexport creates a processing script (shell script) for each configured modul which must be then edited for paths and commands. This can be used to export the pipeline logic to different computers/clusters where implementing mrpipe is not an option.")
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
    parser.add_argument('-p', '--partition', dest="partition", type=str, metavar=None, default=None,
                        help="Submit jobs to a specific SLURM partition. If not specified, mrpipe will use the default partition.")
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
    parser.add_argument('--flowchartMode', dest="flowchartMode", type=str, default="per_module", choices=['per_module', 'all_modules', 'minimal'],
                        help="""mode (str): Visualization mode:\n\t- "per_module": One flow chart per module (default)\n\t- "all_modules": Single comprehensive flow chart with all modules\n\t- "minimal": Single flow chart with minimal design (task names only, file nodes as dots)""")
    # Optional export of per-modality scan inventory during process mode
    parser.add_argument('--noScanInventory', dest='noScanInventory', action='store_true',
                        help='Disable exporting per-modality scan inventory CSVs during process mode (default is to export).')
    parser.add_argument('--bval_tol', dest='bval_tol', type=check_positive, default=20,
                        help='Tolerance to determine shells and b0 values for DWI data. Sometimes the b-values are slightly varying e.g. 995/1000/1005 or 0/5, and this is to capture this range and assign it to the same shell. The difference in b-values between shells is usually > 100')
    parser.add_argument('--non_gaussian_cutoff', dest='non_gaussian_cutoff', type=check_positive, default=1500,
                        help='b-value cutoff for shells to remove to limit the DWI protocol to gaussian diffusion, i.e. remove high b-value shells. The reduced protocol is used for DTI based models.')

    args = parser.parse_args()
    #perform some cleanup to match arugment structure
    args.input = args.input.rstrip("/")

    return args

@staticmethodr
def check_positive(value):
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError("%s is an invalid positive int value" % value)
    return ivalue


@staticmethod
def validate_args(args, logger):
    errors = []

    # Helper predicates
    def is_nonempty_str(v):
        return isinstance(v, str) and len(v.strip()) > 0

    def is_int_like(v):
        try:
            int(v)
            return True
        except Exception:
            return False

    def as_int(v, default=None):
        try:
            return int(v)
        except Exception:
            return default

    # Mode specific validations
    if args.mode == "step":
        if not hasattr(args, "input") or not is_nonempty_str(args.input):
            errors.append("Missing required argument for step mode: --input PATH_TO_PICKLED_JOB_DIR")
        else:
            if not os.path.exists(args.input):
                errors.append(f"--input points to a non-existing path: {args.input}")
            elif not os.path.isdir(args.input):
                errors.append(f"--input must be a directory: {args.input}")


    # Generic argument sanity checks
    path_like_keys_dir = ("path", "dir", "directory", "folder")
    path_like_keys_file = ("file",)
    numeric_like_keys = ("jobs", "threads", "n_jobs", "nthreads", "njobs", "timeout", "limit", "retries")

    for key, value in vars(args).items():
        if value is None:
            continue

        k = key.lower()

        # Skip known non-path, non-numeric args
        if k in {"mode", "verbosity", "loglevel", "flowchartmode"}:
            continue

        # Validate files
        if any(tok in k for tok in path_like_keys_file) or k in {"config"}:
            if is_nonempty_str(value):
                if not os.path.exists(value):
                    errors.append(f"Argument --{key} points to a non-existing path: {value}")
                elif not os.path.isfile(value):
                    errors.append(f"Argument --{key} must be a file, but is a directory: {value}")
            continue

        # Validate directories
        if any(tok in k for tok in path_like_keys_dir) or k in {"input"}:
            if is_nonempty_str(value):
                if not os.path.exists(value):
                    errors.append(f"Argument --{key} points to a non-existing path: {value}")
                elif not os.path.isdir(value):
                    errors.append(f"Argument --{key} must be a directory, but is a file: {value}")
            continue

        # Validate simple numeric constraints (positive integers)
        if any(tok == k or k.endswith(tok) for tok in numeric_like_keys):
            if is_int_like(value):
                iv = as_int(value, None)
                if iv is None or iv <= 0:
                    errors.append(f"Argument --{key} should be a positive integer. Got: {value}")
            else:
                errors.append(f"Argument --{key} should be an integer. Got: {value!r}")

    # Finalize
    if errors:
        logger.critical("Invalid input arguments detected:")
        for e in errors:
            logger.critical(f" - {e}")
        logger.critical("Please fix the above issues and re-run.")
        sys.exit(2)
