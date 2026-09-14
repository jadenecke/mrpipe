#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   suvr_to_centiloid.sh <suvr_image.nii.gz> <tracer> <output_centiloid.nii.gz>
#
# Tracers supported:
#   FBB, AV45, NAV4694, PIB, FMM

infile="$1"
tracer="$2"
outfile="$3"

tmp=$(mktemp)

case "$tracer" in
    FBB)
        # Centiloid = 153.4 * SUVR - 154.9
        fslmaths "$infile" -mul 153.4 -sub 154.9 "$outfile"
        ;;

    AV45)
        # Centiloid = 183 * SUVR - 177
        fslmaths "$infile" -mul 183 -sub 177 "$outfile"
        ;;

    NAV4694)
        # Centiloid = 100 * (SUVR - 1.028) / 1.174
        fslmaths "$infile" -sub 1.028 -div 1.174 -mul 100 "$outfile"
        ;;

    PIB)
        # Centiloid = 100 * (SUVR - 1.009) / 1.067
        fslmaths "$infile" -sub 1.009 -div 1.067 -mul 100 "$outfile"
        ;;

    FMM)
        # Centiloid = 148.52 * SUVR - 137.09
        fslmaths "$infile" -mul 148.52 -sub 137.09 "$outfile"
        ;;

    *)
        echo "Error: tracer '$tracer' is not valid. Valid tracers: FBB, AV45, NAV4694, PIB, FMM" >&2
        exit 1
        ;;
esac
