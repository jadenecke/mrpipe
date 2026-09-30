# Parsing Input arguments
import argparse
from mrpipe.meta import LoggerModule
from argparse import RawTextHelpFormatter
from argparse import ArgumentDefaultsHelpFormatter
import sys
import os


import sys


class Ansi:
    """ANSI color/style codes. Auto-disables (becomes empty strings) when
    stdout isn't a terminal, e.g. when output is piped or redirected to a log file."""
    _enabled = sys.stdout.isatty()

    RESET = "\033[0m" if _enabled else ""
    BOLD = "\033[1m" if _enabled else ""
    DIM = "\033[2m" if _enabled else ""
    ITALIC = "\033[3m" if _enabled else ""
    CYAN = "\033[36m" if _enabled else ""
    MAGENTA = "\033[35m" if _enabled else ""
    YELLOW = "\033[33m" if _enabled else ""
    GREEN = "\033[32m" if _enabled else ""
    RED = "\033[31m" if _enabled else ""
    BLUE = "\033[34m" if _enabled else ""


class HelpFormatter(ArgumentDefaultsHelpFormatter):
    """ArgumentDefaultsHelpFormatter with unnecessary but delightful ANSI flair."""

    # cycle through a color per group so the help page doesn't look flat
    _palette = [Ansi.MAGENTA] #[Ansi.CYAN, Ansi.MAGENTA, Ansi.YELLOW, Ansi.BLUE, Ansi.RED]
    _color_i = 0

    def start_section(self, heading):
        if heading:
            color = self._palette[HelpFormatter._color_i % len(self._palette)]
            HelpFormatter._color_i += 1
            heading = f"{Ansi.BOLD}{color}{heading.upper()}{Ansi.RESET}"
        super().start_section(heading)

    def _format_usage(self, usage, actions, groups, prefix):
        result = super()._format_usage(usage, actions, groups, prefix)
        return f"{Ansi.BOLD}{Ansi.MAGENTA}{result}{Ansi.RESET}"

    def _get_help_string(self, action):
        help_str = super()._get_help_string(action)
        return help_str

    def _format_action_invocation(self, action):
        result = super()._format_action_invocation(action)
        return f"{Ansi.BOLD}{Ansi.GREEN}{result}{Ansi.RESET}"


def inputParser():
    logger = LoggerModule.Logger()
    logger.process("Processing Input arguments.")

    parser = argparse.ArgumentParser(
        description=(
            f"{Ansi.BOLD}{Ansi.YELLOW}mrpipe{Ansi.RESET} — a fully automated, "
            f"graph-based multimodal integrative MRI pre- and postprocessing pipeline. "
        ),
        formatter_class=HelpFormatter)

    # ------------------------------------------------------------------
    # Mode & input (positional arguments)
    # ------------------------------------------------------------------
    g_main = parser.add_argument_group("Mode and input")
    g_main.add_argument(dest="mode", type=str, choices=['config', 'process', 'step', 'flowchart', 'scriptexport'],
                        help="Mode of operation: \nconfig creates a data config for a dataset. Be aware, that config sets up everything at the same level as the input directory.\nprocess takes a configured data set and processes it.\nstep is an internal method to run a processing step. May be used for debugging if given a PipeJop directory to run a single job. Be aware that it will also run all followup steps if specified.\nflowchart generates flow charts for processing modules showing tasks, input/output files, and dependencies.\nscriptexport creates a processing script (shell script) for each configured modul which must be then edited for paths and commands. This can be used to export the pipeline logic to different computers/clusters where implementing mrpipe is not an option.")
    g_main.add_argument(dest="input", type=str,
                        metavar="/path/to/input",
                        help="Input: Either path to data bids directory if in config or process mode or path to to PipeJop directory if in step mode.")
    g_main.add_argument('-n', '--name', dest="name", type=str,
                        metavar="mrpipe", default=None,
                        help="Name of the pipeline, if not specified, will use the name of the parent directory of input. Only regarded in config mode.")

    # ------------------------------------------------------------------
    # Input data structure & subject selection
    # ------------------------------------------------------------------
    g_data = parser.add_argument_group("Input data",
                                       "Tell mrpipe where your data lives and who's invited.")
    g_data.add_argument('--select_subjects', dest="select_subjects", type=str,
                        metavar="*", default=None,
                        help="Select a sub-sample of subjects to process. Accepts single subject string, a comma-seperated list or for larger lists, it also accepts a filepath to a .txt file with one subject name per line. ")
    g_data.add_argument('--subjectDescriptor', dest="subjectDescriptor", type=str, metavar="sub-*", default="sub-*",
                        help="Subject matching pattern. Used to identify subjects in input directory.")
    g_data.add_argument('--sessionDescriptor', dest="sessionDescriptor", type=str, metavar="ses-*", default="ses-*",
                        help="Session matching pattern. Used to identify sessions in subject directories.")
    g_data.add_argument('--dataStructure', dest="dataStructure", type=str, metavar="sub/ses/modality", default="sub/ses/mod",
                        help="data structure matching pattern. Defines in which order subject, session, and modality are stored. Must be a combination of (sub,ses,mod) seperated by / and must not contain anything else. If no data structure is specified, the default is sub/ses/modality.")
    g_data.add_argument('--modalityBeforeSession', dest="modalityBeforeSession", action="store_true",
                        help="Whether Modality comes before session or not. Defaults to Subject/Session/Modality.")

    # ------------------------------------------------------------------
    # Scheduler / SLURM
    # ------------------------------------------------------------------
    g_slurm = parser.add_argument_group("Scheduler and SLURM",
                                        "Feed the cluster. It's hungry.")
    g_slurm.add_argument('--schedulerType', dest="schedulerType", type=str, default="Slurm", choices=['Slurm', 'Local'],
                         help="""Scheduler mode: How to run the pipeline: "Slurm" submits a self submitting pipeline of jobs using sbatch. "Local" runs as continuous job locally in the terminal.""")
    g_slurm.add_argument('-c', '--ncores', dest='ncores', type=int, default=1,
                         help='SLURM: Number of cores to use. In the case of the SLURM scheduler these can be distributed over multiple nodes.')
    g_slurm.add_argument('-g', '--ngpus', dest='ngpus', type=int, default=0,
                         help='SLURM: Number of GPUs to use. In the case of the SLURM scheduler these can be distributed over multiple nodes. Default is 0, even though some steps may benefit/require GPU processing, so please specifiy if GPUs are available, even if you are unsure whether the program will use them. They will only be reserved if they are required.')
    g_slurm.add_argument('--mem', dest='mem', type=int, default=None,
                         help='SLURM: Amount of memory per Node in GB to use. This should not be specified unless you run into memory issues. mrpipe asks for an appropriate amount of memory based on the numbers of cores given and the particular job step.')
    g_slurm.add_argument('-p', '--partition', dest="partition", type=str, metavar=None, default=None,
                         help="SLURM: Submit jobs to a specific SLURM partition. If not specified, mrpipe will use the default partition.")
    g_slurm.add_argument('--excludeNodes', dest="excludeNodes", type=str, metavar=None, default=None,
                         help="SLURM: Exclude certain nodes from the pipeline. Comma seperated list of node names.")
    g_slurm.add_argument('-s', '--scratch', dest="scratch", type=str, metavar=None, default=None,
                         help="Scratch directory, must exist on every compute node")

    # ------------------------------------------------------------------
    # DWI
    # ------------------------------------------------------------------
    g_dwi = parser.add_argument_group("DWI options",
                                      "Shells, gaussians, and other diffusion drama.")
    g_dwi.add_argument('--bval_tol', dest='bval_tol', type=check_positive, default=50,  # fsl and mrtrix set this at 100 i think.
                       help='Tolerance to determine shells and b0 values for DWI data. Sometimes the b-values are slightly varying e.g. 995/1000/1005 or 0/5, and this is to capture this range and assign it to the same shell. The difference in b-values between shells is usually > 100')
    g_dwi.add_argument('--non_gaussian_cutoff', dest='non_gaussian_cutoff', type=check_positive, default=1500,
                       help='b-value cutoff for shells to remove to limit the DWI protocol to gaussian diffusion, i.e. remove high b-value shells. The reduced protocol is used for DTI based models.')
    g_dwi.add_argument('--onlyWithReversePhaseEncoding', dest="onlyWithReversePhaseEncoding", action="store_true",
                       help="Only include diffusion data if it has a reverse phase encoding scan.")
    g_dwi.add_argument('--onlyMultiShell', dest="onlyMultiShell", action="store_true",
                       help="Only include diffusion data if it has multiple shells with one shell being >= 2000.")
    g_dwi.add_argument('--minDirections', dest='minDirections', type=check_positive, default=18,  # was dest='non_gaussian_cutoff' (see note)
                       help='Minimum number of directions for DWI images to be processed. This can be used to exclude very old diffusion protocols, but also it assures that wrongly configured sessions (in bids directory) with only the reverse phase encoding scan is not identified as main image. Therefore, never set this to a lower number than the number of directions recorded for reverse phase encoding (anything above 12 should be save, currently)')

    # ------------------------------------------------------------------
    # Output / processing
    # ------------------------------------------------------------------
    g_out = parser.add_argument_group("Output and processing")
    g_out.add_argument('--noScanInventory', dest='noScanInventory', action='store_true',
                       help='Disable exporting per-modality scan inventory CSVs during process mode (default is to export).')
    g_out.add_argument('--writeSubjectPaths', dest="writeSubjectPaths", action="store_true",
                       help="Writes all subject paths as a json file to disk, including Path properties, e.g. file sorting for echo numbers etc. Useful for debugging. ")

    # ------------------------------------------------------------------
    # Flowchart mode
    # ------------------------------------------------------------------
    g_flow = parser.add_argument_group("Flowchart options",
                                       "For when you want pretty pictures instead of results. Flowchart mode only.")
    g_flow.add_argument('--module', dest="module_name", type=str, default=None,
                        help="Name of the specific processing module to generate a flow chart for. If not specified, flow charts will be generated for all modules. Only used in flowchart mode.")
    g_flow.add_argument('--flowchartMode', dest="flowchartMode", type=str, default="per_module", choices=['per_module', 'all_modules', 'minimal'],
                        help="""Visualization mode:\n\t- "per_module": One flow chart per module (default)\n\t- "all_modules": Single comprehensive flow chart with all modules\n\t- "minimal": Single flow chart with minimal design (task names only, file nodes as dots)""")

    # ------------------------------------------------------------------
    # Debugging
    # ------------------------------------------------------------------
    g_debug = parser.add_argument_group("Debugging")
    g_debug.add_argument('-v', '--verbose', action="count", help="verbose level... repeat up to three times.", default=0, dest="verbose")
    g_debug.add_argument('--skipDerivativeRegeneration', dest="skipDerivativeRegeneration", action="store_true",
                         help="DEBUGGING: This option disables the regeneration of derivative files if the underlying source changes. Use only if you deleted some intermediary steps and want to recreate them without re-processing any data that depends on these intermediary steps. ONLY USE IF YOU KNOW WHAT YOU ARE DOING, and if the processing steps are deterministic, otherwise this may introduce inconsistencies between the results.")

    args = parser.parse_args()
    # perform some cleanup to match arugment structure
    args.input = args.input.rstrip("/")

    return args

@staticmethod
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

@staticmethod
def parseSubjectInput(select_subjects):
    if select_subjects is None:
        return None
    elif os.path.isfile(select_subjects):
        with open(select_subjects, "r") as f:
            subjects = [line.strip() for line in f.readlines()]
    else:
        subjects = [s.strip() for s in select_subjects.split(",")]
    return subjects