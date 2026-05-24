#!/usr/bin/env bash
set -euo pipefail

usage() {
     echo "Usage: $0 <inputNifti> <inputjson> <inputbval> <inputbvec> <outputDenoised> <outputjson> <outputBval> <outputBvec> [--threads N] [--force]"
    exit 1
}

# --- Parse positional arguments ---
inputNifti="$1"
inputjson="$2"
inputbval="$3"
inputbvec="$4"
outputDenoised="$5"
outputjson="$6"
outputBval="$7"
outputBvec="$8"
shift 8

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

#
## check if tmp dir was created
#if [[ ! "$WORK_DIR" || ! -d "$WORK_DIR" ]]; then
#  echo "Could not create temp dir"
#  exit 1
#fi
#
## deletes the temp directory
#function cleanup {
#  rm -rfv "$WORK_DIR"
#  echo "Deleted temp working directory $WORK_DIR"
#}
#
## register the cleanup function to be called on the EXIT signal
#trap cleanup EXIT



# --- Build commands ---
c1="mrconvert \"$inputNifti\" -json_import \"$inputjson\" -fslgrad \"$inputbvec\" \"$inputbval\" - $threads $force"
c2="dwidenoise - - $threads $force"
c3="mrdegibbs - - $threads $force"
c4="mrconvert - \"$outputDenoised\" -export_grad_fsl \"$outputBvec\" \"$outputBval\" -json_export \"$outputjson\" $threads $force"

# --- Execute pipeline ---
eval "$c1" | eval "$c2" | eval "$c3" | eval "$c4"
