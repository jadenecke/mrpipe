#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage: $0 <inputImage> <inputBval> <inputBvec> <inputJson> <outputB0> [--threads N] [--force]"
    exit 1
}

# --- Parse positional arguments ---
inputImage="$1"
inputBval="$2"
inputBvec="$3"
inputJson="$4"
outputB0="$5"
shift 5

threads=""
force=""

# --- Parse optional flags ---
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
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# --- Build commands ---
c1="mrconvert \"$inputImage\" -json_import \"$inputJson\" -fslgrad \"$inputBvec\" \"$inputBval\" - $threads $force"
c2="dwiextract - - -bzero $threads $force"
c3="mrconvert - -coord 3 0 -axes 0,1,2 \"$outputB0\" $threads $force"

# --- Execute pipeline ---
eval "$c1" | eval "$c2" | eval "$c3"
