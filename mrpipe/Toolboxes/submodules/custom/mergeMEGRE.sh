#!/usr/bin/env bash
#
# merge_megre.sh
#
# Merges per-echo ME-GRE magnitude and phase images into one 4D magnitude and one 4D phase
# image with `fslmerge -t`. If only real/imaginary images are available, they are first converted
# to magnitude/phase (echo by echo) with the real/imaginary R script.
#
# All lists are merged IN THE ORDER GIVEN, so pass them sorted by echo time. For real/imaginary,
# the i-th --real file and the i-th --imag file must belong to the same echo.

set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  Magnitude/phase available:
    merge_megre.sh --mag M1 M2 ... --pha P1 P2 ... --out-mag OUT_MAG.nii.gz --out-pha OUT_PHA.nii.gz

  Only real/imaginary available:
    merge_megre.sh --real R1 R2 ... --imag I1 I2 ... --tmp-dir DIR --r-script SCRIPT.R \
                   --out-mag OUT_MAG.nii.gz --out-pha OUT_PHA.nii.gz

Options:
  --mag FILES...     per-echo magnitude images (echo order)
  --pha FILES...     per-echo phase images (echo order)
  --real FILES...    per-echo real images (echo order)
  --imag FILES...    per-echo imaginary images (same echo order as --real)
  --out-mag FILE     output 4D magnitude image (must end in .nii.gz)
  --out-pha FILE     output 4D phase image (must end in .nii.gz)
  --tmp-dir DIR      real/imaginary only: directory for the intermediate per-echo conversions.
                     A unique sub-directory is created inside and removed at the end.
  --r-script FILE    real/imaginary only: the R conversion script
                     (default: $REAL_IMAG_R_SCRIPT)
  -h, --help         show this help

Give either --mag/--pha or --real/--imag, not both.
EOF
}

die() { echo "ERROR: $*" >&2; exit 1; }
log() { echo "[merge_megre] $*" >&2; }

MAG=(); PHA=(); REAL=(); IMAG=()
OUT_MAG=""; OUT_PHA=""; TMP_DIR=""; R_SCRIPT="${REAL_IMAG_R_SCRIPT:-}"

# ---------------------------------------------------------------- argument parsing
current=""   # list option that is currently collecting values
while [[ $# -gt 0 ]]; do
    case "$1" in
        --mag|--pha|--real|--imag)
            current="$1"; shift ;;
        --out-mag|--out-pha|--tmp-dir|--r-script)
            [[ $# -ge 2 ]] || die "Missing value for $1"
            case "$1" in
                --out-mag)  OUT_MAG="$2" ;;
                --out-pha)  OUT_PHA="$2" ;;
                --tmp-dir)  TMP_DIR="$2" ;;
                --r-script) R_SCRIPT="$2" ;;
            esac
            current=""; shift 2 ;;
        -h|--help)       usage; exit 0 ;;
        -*)              die "Unknown option: $1 (see --help)" ;;
        *)
            case "$current" in
                --mag)  MAG+=("$1") ;;
                --pha)  PHA+=("$1") ;;
                --real) REAL+=("$1") ;;
                --imag) IMAG+=("$1") ;;
                *)      die "Unexpected argument: $1 (see --help)" ;;
            esac
            shift ;;
    esac
done

# ---------------------------------------------------------------- validation
[[ -n "$OUT_MAG" && -n "$OUT_PHA" ]] || die "--out-mag and --out-pha are required"
[[ "$OUT_MAG" == *.nii.gz && "$OUT_PHA" == *.nii.gz ]] || die "Output files must end in .nii.gz"
[[ "$OUT_MAG" != "$OUT_PHA" ]] || die "--out-mag and --out-pha must be different files"

have_magpha=$(( ${#MAG[@]} > 0 || ${#PHA[@]} > 0 ))
have_realimag=$(( ${#REAL[@]} > 0 || ${#IMAG[@]} > 0 ))

if (( have_magpha && have_realimag )); then
    die "Give either --mag/--pha or --real/--imag, not both"
elif (( ! have_magpha && ! have_realimag )); then
    die "Give either --mag/--pha or --real/--imag (see --help)"
fi

command -v fslmerge >/dev/null 2>&1 || die "fslmerge not found. Is FSL installed and on the PATH?"
# make sure fslmerge writes .nii.gz, regardless of the user's FSL configuration
export FSLOUTPUTTYPE=NIFTI_GZ

if (( have_magpha )); then
    (( ${#MAG[@]} > 0 && ${#PHA[@]} > 0 )) || die "--mag and --pha must both be given"
    (( ${#MAG[@]} == ${#PHA[@]} )) || die "Number of magnitude (${#MAG[@]}) and phase (${#PHA[@]}) files differ"
    for f in "${MAG[@]}" "${PHA[@]}"; do [[ -f "$f" ]] || die "File not found: $f"; done
else
    (( ${#REAL[@]} > 0 && ${#IMAG[@]} > 0 )) || die "--real and --imag must both be given"
    (( ${#REAL[@]} == ${#IMAG[@]} )) || die "Number of real (${#REAL[@]}) and imaginary (${#IMAG[@]}) files differ"
    [[ -n "$TMP_DIR" ]]  || die "--tmp-dir is required with --real/--imag"
    [[ -n "$R_SCRIPT" ]] || die "--r-script (or \$REAL_IMAG_R_SCRIPT) is required with --real/--imag"
    [[ -f "$R_SCRIPT" ]] || die "R script not found: $R_SCRIPT"
    command -v Rscript >/dev/null 2>&1 || die "Rscript not found. Is R installed and on the PATH?"
    for f in "${REAL[@]}" "${IMAG[@]}"; do [[ -f "$f" ]] || die "File not found: $f"; done
fi

# ---------------------------------------------------------------- real/imaginary -> magnitude/phase
if (( have_realimag )); then
    mkdir -p "$TMP_DIR"
    WORK_DIR="$(mktemp -d "${TMP_DIR%/}/megre_convert.XXXXXX")"
    trap 'rm -rf "$WORK_DIR"' EXIT

    for i in "${!REAL[@]}"; do
        n="$(printf '%03d' $((i + 1)))"
        conv_mag="$WORK_DIR/echo-${n}_magnitude.nii.gz"
        conv_pha="$WORK_DIR/echo-${n}_phase.nii.gz"

        log "Converting echo $((i + 1))/${#REAL[@]}: ${REAL[$i]} + ${IMAG[$i]}"
        Rscript "$R_SCRIPT" \
            --real "${REAL[$i]}" --imaginary "${IMAG[$i]}" \
            --magnitude "$conv_mag" --phase "$conv_pha" --checkBipolar --scale 4096 \
            || die "R conversion failed for echo $((i + 1))"
        [[ -f "$conv_mag" && -f "$conv_pha" ]] || die "R script did not create $conv_mag / $conv_pha"

        MAG+=("$conv_mag")
        PHA+=("$conv_pha")
    done
fi

# ---------------------------------------------------------------- 4D merge
mkdir -p "$(dirname "$OUT_MAG")" "$(dirname "$OUT_PHA")"

log "Merging ${#MAG[@]} magnitude images -> $OUT_MAG"
fslmerge -t "$OUT_MAG" "${MAG[@]}" || die "fslmerge failed for magnitude"
log "Merging ${#PHA[@]} phase images -> $OUT_PHA"
fslmerge -t "$OUT_PHA" "${PHA[@]}" || die "fslmerge failed for phase"

log "Done."