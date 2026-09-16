#!/usr/bin/env bash
set -euo pipefail

usage() {
     echo "Usage: $0 <inputNifti> <inputjson> <inputbval> <inputbvec> <outputMif> <scratch> [--threads N] [--force]"
    exit 1
}

# --- Parse positional arguments ---
inputNifti="$1"
inputjson="$2"
inputbval="$3"
inputbvec="$4"
outputMif="$5"
scratch="$6"
shift 6

threads=""
force=""

# --- Parse optional flags until first non-flag ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --threads)
            threads="-nthreads $2"
            shift 2
            ;;
        --force)
            force="-force"
            shift
            ;;
        --)  # explicit end of options
            shift
            break
            ;;
    esac
done


WORK_DIR=`mktemp -d -p "${scratch}" "dwiBiascorrect_XXXXXXXXXXX"`

# check if tmp dir was created
if [[ ! "$WORK_DIR" || ! -d "$WORK_DIR" ]]; then
  echo "Could not create temp dir"
  exit 1
fi

# deletes the temp directory
function cleanup {
  rm -rfv "$WORK_DIR"
  echo "Deleted temp working directory $WORK_DIR"
}

# register the cleanup function to be called on the EXIT signal
trap cleanup EXIT


# --- Execute commands ---
dwibiascorrect ants "${inputNifti}" "${WORK_DIR}/biasCor.mif" -fslgrad "${inputbvec}" "${inputbval}" -scratch "${scratch}" ${threads} ${force}
mrconvert "${WORK_DIR}/biasCor.mif" -json_import "${inputjson}" -fslgrad "${inputbvec}" "${inputbval}" "${outputMif}" ${threads} ${force}

exit 0