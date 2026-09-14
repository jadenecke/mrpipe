#!/usr/bin/env bash
set -euo pipefail

usage() {
     echo "Usage: $0 <inputMif> <inputMask> <outputBasename> <scratch> [--threads N] [--force]"
    exit 1
}

# --- Parse positional arguments ---
inputMif="$1"
inputMask="$2"
outputBasename="$3"
scratch="$4"
shift 4

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

WORK_DIR=`mktemp -d -p "${scratch}" "dwiDTIFIT_XXXXXXXXXXX"`

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

# --- commands ---
dwiextract "${inputMif}" "${WORK_DIR}/dwi.nii.gz" -shells 0,1000 -export_grad_fsl "${WORK_DIR}/dwi.bvec" "${WORK_DIR}/dwi.bval" ${threads} ${force}
dtifit -k "${WORK_DIR}/dwi.nii.gz" -o "${outputBasename}" -m "${inputMask}" -r "${WORK_DIR}/dwi.bvec" -b "${WORK_DIR}/dwi.bval" ${threads} ${force}

