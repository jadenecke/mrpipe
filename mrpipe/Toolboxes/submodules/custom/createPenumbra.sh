#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage:"
    echo "  $0 <WMHMaskMNI> <WMMask> <output_basename> <scratch_dir> <dilation_sizes...>"
    echo
    echo "Example:"
    echo "  $0 WMH.nii.gz WM.nii.gz out/sub-01_ses-01 /scratch 2 4 6 8 10"
    exit 1
}

if [[ $# -lt 5 ]]; then
    usage
fi

WMHMaskMNI="$(readlink -f "$1")"
WMMask="$(readlink -f "$2")"
BASENAME="$3"     # may include directory path
SCRATCH="$(readlink -f "$4")"
shift 4
DILATIONS=("$@")

if [[ ${#DILATIONS[@]} -eq 0 ]]; then
    echo "ERROR: At least one dilation size must be provided."
    exit 1
fi

if [[ ! -d "$SCRATCH" ]]; then
    echo "ERROR: Scratch directory does not exist: $SCRATCH"
    exit 1
fi

TMPDIR="$(mktemp -d "${SCRATCH}/wmh_rings_XXXXXX")"
echo ">>> Using temporary scratch directory: $TMPDIR"

mkdir -p "$(dirname "$BASENAME")"

cp "$WMHMaskMNI" "${TMPDIR}/wmh.nii.gz"
cp "$WMMask"     "${TMPDIR}/wm.nii.gz"

echo ">>> Computing NAWM = WM - WMH"
fslmaths "${TMPDIR}/wm.nii.gz" -sub "${TMPDIR}/wmh.nii.gz" "${TMPDIR}/nawm.nii.gz"

echo ">>> Creating dilation masks…"
for d in "${DILATIONS[@]}"; do
    echo "------> dilating ${d}mm"
    fslmaths "${TMPDIR}/wmh.nii.gz" \
        -kernel sphere "$d" -dilM \
        "${TMPDIR}/dil_${d}.nii.gz"
done

echo ">>> Creating ring masks…"
prev=""
for d in "${DILATIONS[@]}"; do
    curr="${TMPDIR}/dil_${d}.nii.gz"
    ring="${BASENAME}_WMH_ring${d}.nii.gz"

    if [[ -z "$prev" ]]; then
        fslmaths "$curr" -sub "${TMPDIR}/wmh.nii.gz" -mul "${TMPDIR}/wm.nii.gz" "$ring"
    else
        fslmaths "$curr" -sub "$prev" -mul "${TMPDIR}/wm.nii.gz" "$ring"
    fi

    prev="$curr"
done

# safe last element
last_idx=$(( ${#DILATIONS[@]} - 1 ))
last_d="${DILATIONS[$last_idx]}"
last="${TMPDIR}/dil_${last_d}.nii.gz"
final="${BASENAME}_WMH_ring${last_d}plus.nii.gz"

echo ">>> Creating final ring (NAWM minus last dilation)…"
fslmaths "${TMPDIR}/nawm.nii.gz" -sub "$last" -mul "${TMPDIR}/wm.nii.gz" "$final"

echo ">>> Removing temporary directory: $TMPDIR"
rm -rf "$TMPDIR"

echo ">>> Done."
