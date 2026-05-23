#!/usr/bin/env bash
set -euo pipefail

usage() {
     echo "Usage: $0 <wmfodNorm> <T1_5TTReg> <nstreamlines> <outputbase> <scratch> [--threads N] [--force] atlasName atlasFile [atlasName atlasFile ...]"
    exit 1
}

# --- Parse positional arguments ---
wmfodNorm="$1"
T1_5TTReg="$2"
nstreamlines="$3"
outputbase="$4"
scratch="$5"
shift 5

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
        -*)
            echo "Unknown option: $1"
            usage
            ;;
        *)
            # first non-option → stop parsing flags
            break
            ;;
    esac
done

# --- Remaining args must be pairs: name + file ---
if (( $# % 2 != 0 )); then
    echo "Error: Atlas arguments must come in pairs: <name> <file>"
    usage
fi

declare -a atlasNames=()
declare -a atlasFiles=()

while [[ $# -gt 0 ]]; do
    name="$1"
    file="$2"
    atlasNames+=("$name")
    atlasFiles+=("$file")
    shift 2
done

# --- Debug printout ---
echo "Detected atlas pairs:"
for i in "${!atlasNames[@]}"; do
    echo " - ${atlasNames[$i]} -> ${atlasFiles[$i]}"
done


# https://stackoverflow.com/questions/4632028/how-to-create-a-temporary-directory
# the temp directory used, within $DIR
# omit the -p parameter to create a temporal directory in the default location
WORK_DIR=`mktemp -d -p "${scratch}" "tckgenSift2connectome_XXXXXXXXXXX"`

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

#wmfodNorm="$1"
 #T1_5TTReg="$2"
 #nstreamlines="$3"
 #nsift="$4"
 #outputbase="$5"
 #scratch="$6"


# --- Build commands ---
echo "Running tckgen..."
tckgen -algorithm iFOD2 -act ${T1_5TTReg} -select ${nstreamlines} -seed_dynamic ${wmfodNorm} ${threads} ${force} ${wmfodNorm} "${WORK_DIR}/tcks.tck"

echo "Running Sift..."
tcksift2 -act ${T1_5TTReg} "${WORK_DIR}/tcks.tck" ${wmfodNorm} "${WORK_DIR}/tcks_siftWeights.txt"

echo "Running tck2connectome..."
for i in "${!atlasNames[@]}"; do
    echo " Running for Atlas: ${atlasNames[$i]} -> ${atlasFiles[$i]}"
    tck2connectome -symmetric -zero_diagonal -scale_invnodevol -assignment_end_voxels -tck_weights_in "${WORK_DIR}/tcks_siftWeights.txt" "${WORK_DIR}/tcks.tck" "${atlasFiles[$i]}" "${outputbase}${atlasNames[$i]}.csv"
done

