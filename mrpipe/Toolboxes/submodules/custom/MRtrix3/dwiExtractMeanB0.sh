#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage: $0 <inputImage> <outputB0> [--threads N] [--force]"
    exit 1
}

# --- Positional arguments ---
inputImage="$1"
outputB0="$2"
shift 2

threads=""
force=""

# --- Optional flags ---
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
c1="dwiextract \"$inputImage\" - -bzero $threads $force"
c2="mrmath - mean \"$outputB0\" -axis 3 $threads $force"

# --- Execute pipeline ---
eval "$c1" | eval "$c2"
