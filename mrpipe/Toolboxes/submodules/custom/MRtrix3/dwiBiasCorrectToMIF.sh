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

# --- Build commands ---
c1="dwibiascorrect ants \"$inputNifti\" - -fslgrad \"$inputbvec\" \"$inputbval\" -scratch \"$scratch\" $threads $force"
c2="mrconvert - -json_import \"$inputjson\" -fslgrad \"$inputbvec\" \"$inputbval\" \"$outputMif\" $threads $force"

# --- Execute pipeline ---
eval "$c1" | eval "$c2"
