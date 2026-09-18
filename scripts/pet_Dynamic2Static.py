"""
Generate a static preprocessed PET scan from a dynamic 4D PET image and
a JSON metadata file produced by pet_dcm_parser.

Pipeline:
    1. Determine tracer from JSON.
    2. Read frame durations.
    3. Extract those frames from the 4D PET.
    4. Motion-correct the subset using mcflirt.
    5. No smoothing.
    6. Temporal averaging → static PET.

Assumptions:
    - mid_frame_minutes_withCorrection is minutes post injection.
    - FSL binaries are available in PATH.
    - JSON structure matches export_to_json() from pet_dcm_parser.
"""

import json
import argparse
import subprocess
import os
import tempfile
import shutil
from typing import Dict, Tuple, List, Any
import json
import csv
import nibabel as nib


# tracers info -> FBB: 4x5min , PI2620: 6x5min
# expected frame numbers and durations 
EXPECTED_PROTOCOL = {
    "FBB": {
        "n_frames": 4,
        "duration_min": 5.0,
    },
    "PI2620": {
        "n_frames": 6,
        "duration_min": 5.0,
    },
}

def validate_pet4d_vs_json(pet4d_path: str, scan: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate that the NIfTI file is actually 4D and that its number of
    volumes matches the number of frames described in the JSON metadata.

    Returns
    -------
    passed : bool
    reason : str
    """
    try:
        nii = nib.load(pet4d_path)
    except Exception as e:
        return False, f"Could not load NIfTI file: {e}"

    shape = nii.shape

    if len(shape) < 4 or shape[3] < 2:
        return False, (
            f"NIfTI is not 4D (shape: {shape}). "
            "Expected a 4D image with at least 2 volumes."
        )

    n_volumes = shape[3]
    n_frames_json = len(scan.get("frames", []))

    if n_frames_json == 0:
        return False, "JSON metadata contains no frame entries."

    if n_volumes != n_frames_json:
        return False, (
            f"NIfTI volume count ({n_volumes}) does not match "
            f"number of frames in JSON ({n_frames_json})."
        )

    return True, "PASS"

# validate the subjects 
def validate_protocol(scan, tracer, tolerance=0.25):
    """
    Returns
    -------
    passed : bool
    frame_indices : list[int]
    reason : str
    """

    if tracer not in EXPECTED_PROTOCOL:
        return False, [], f"Unsupported tracer: {tracer}"

    expected = EXPECTED_PROTOCOL[tracer]
    frames = scan.get("frames", [])

    # Check number of frames
    if len(frames) != expected["n_frames"]:
        return (
            False,
            [],
            f"Expected {expected['n_frames']} frames, found {len(frames)}",
        )

    durations = []

    for frame in frames:

        dur_sec = frame.get("duration_seconds") 

        if dur_sec is None:
            return False, [], "Missing frame duration"

        dur = float(dur_sec) / 60 # getting the minutes 
        durations.append(dur)

        if abs(dur - expected["duration_min"]) > tolerance:
            return (
                False,
                [],
                f"Frame duration {dur:.2f} min != {expected['duration_min']} min",
            )

    return True, list(range(len(frames))), "PASS"


# log the failed scans into a csv 
def log_failed_scan(csv_file,
                    subject,
                    session,
                    image_id,
                    tracer,
                    reason):

    header = [
        "subject",
        "session",
        "image_id",
        "tracer",
        "reason",
    ]

    write_header = not os.path.exists(csv_file)

    with open(csv_file, "a", newline="") as f:
        writer = csv.writer(f)

        if write_header:
            writer.writerow(header)

        writer.writerow([
            subject,
            session,
            image_id,
            tracer,
            reason,
        ])

# -------------------------------------------------------------------------
# Utility
# -------------------------------------------------------------------------
def run(cmd: List[str]) -> None:
    subprocess.run(cmd, check=True)


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)

def write_sidecar_json(
    output_nifti: str,
    tracer: str,
    window_used: tuple,
    used_fallback: bool,
    frame_indices: list,
    kernel_sigma_mm: float,
    input_pet4d: str,
    input_json: str,
    voxel_resolution_mm: list,
):
    """
    Write preprocessing parameters to a JSON file next to the output NIfTI.
    Example: output.nii.gz → output.json
    """
    sidecar_path = os.path.splitext(output_nifti.removesuffix(".gz"))[0] + "_staticTransform.json"

    data = {
        "static_pet_preprocessing": {
            "tracer": tracer,
            "window_used_minutes": {
                "start": window_used[0],
                "end": window_used[1],
            },
            "used_fallback_window": used_fallback,
            "selected_frame_indices_0_based": frame_indices,
            "smoothing_kernel_sigma_mm": kernel_sigma_mm,
            "input_files": {
                "dynamic_pet_4d": input_pet4d,
                "metadata_json": input_json,
            },
            "input_voxel_resolution_mm": voxel_resolution_mm,
            "output_file": output_nifti,
        }
    }

    with open(sidecar_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Sidecar JSON written to: {sidecar_path}")
    return sidecar_path




# -------------------------------------------------------------------------
# JSON extraction
# -------------------------------------------------------------------------
def select_single_scan(data: Dict[str, Any]) -> Dict[str, Any]:
    scans = data.get("scans", [])
    if len(scans) != 1:
        raise ValueError("JSON contains multiple scans; this script expects exactly one.")
    return scans[0]


def get_tracer_name(scan: Dict[str, Any]) -> str:
    modality = scan.get("modality_guess", {})
    tracer = modality.get("bids_tracer")
    if tracer:
        return tracer
    raise ValueError("Tracer name missing in JSON.")



# def try_select_frames(scan: Dict[str, Any], window: Tuple[float, float]) -> List[int]:
#     start_min, end_min = window
#     selected = []

#     for idx, frame in enumerate(scan.get("frames", [])):
#         mid = frame.get("mid_frame_minutes_withCorrection")
#         if mid is None:
#             continue
#         try:
#             mid_val = float(mid)
#         except Exception:
#             continue
#         if start_min <= mid_val <= end_min:
#             selected.append(idx)

#     return selected


# def select_frames_with_fallback(scan: Dict[str, Any], tracer: str) -> Tuple[List[int], Tuple[float, float], bool]:
#     """
#     Returns:
#         frame_indices: list of selected frames
#         window_used: (start_min, end_min)
#         used_fallback: bool
#     """

#     windows = get_windows_for_tracer(tracer)

#     # 1. Try preferred window
#     preferred = windows["preferred"]
#     frames = try_select_frames(scan, preferred)
#     if frames:
#         return frames, preferred, False

#     # 2. Try allowed fallback windows
#     for w in windows["allowed"]:
#         frames = try_select_frames(scan, w)
#         if frames:
#             return frames, w, True

#     raise ValueError(
#         f"No frames found for tracer {tracer} in preferred or allowed windows."
#     )


# -------------------------------------------------------------------------
# FSL operations
# -------------------------------------------------------------------------
def extract_frames(input_4d: str, frame_indices: List[int], out_4d: str, tmpdir: str) -> None:

    split_dir = os.path.join(tmpdir, "split")
    os.makedirs(split_dir, exist_ok=True)

    # Split once
    run(["fslsplit", input_4d, os.path.join(split_dir, "vol_"), "-t"])

    # Collect selected frames
    selected_paths = []
    for idx in frame_indices:
        vol = os.path.join(split_dir, f"vol_{idx:04d}.nii.gz")
        if not os.path.exists(vol):
            raise RuntimeError(f"Missing expected volume {vol}")
        selected_paths.append(vol)

    # Merge back
    run(["fslmerge", "-t", out_4d] + selected_paths)

def reorient_4d(input_4d: str, output_4d: str) -> None:
    run(["fslreorient2std", input_4d, output_4d])

def motion_correct(input_4d: str, output_4d: str) -> None:
    run([
        "mcflirt",
        "-in", input_4d,
        "-out", output_4d,
        "-refvol", "0",
        "-plots",
        "-report",
    ])

def resample_4d(input_4d: str, output_4d: str, resolution_mm: float) -> None:
    run([
        "flirt",
        "-nosearch",
        "-applyisoxfm", str(resolution_mm),
        "-in", input_4d,
        "-out", output_4d,
        "-ref", input_4d,
        "-interp", "spline",
        "-datatype", "float"
    ])

def smooth(input_img: str, output_img: str, sigma_mm: float) -> None:
    run(["fslmaths", input_img, "-s", str(sigma_mm), output_img])


def temporal_average(input_4d: str, output_3d: str) -> None:
    run(["fslmaths", input_4d, "-Tmean", output_3d])


# -------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Create static preprocessed PET from dynamic 4D PET + JSON."
    )
    parser.add_argument("-i", "--pet4d", required=True, help="Dynamic 4D PET NIfTI.")
    parser.add_argument("-j", "--json_parser", required=True, help="NOT REGULAR BIDS SIDECAR! Metadata JSON from pet_dcm_parser! If this is not specified, all frames will be used.")
    parser.add_argument("-o", "--out-static", required=True,
                        help="Output static PET NIfTI.")
    parser.add_argument("--resample_resolution", required=False, default=None, type=float,
                        help="If specified, the PET will be resampled to this isotropic resolution (mm) after temporal averaging.")
    parser.add_argument("--smooth_sigma", required=False, default=None, type=float,
                        help="If specified, the PET will be smoothed with a Gaussian kernel (mm).")
    parser.add_argument("-s", "--scratch", required=True,
                        help="Path to an existing scratch directory. A temporary subdirectory will be created inside it.")
    parser.add_argument("--failed-csv", required=True,
                        help="CSV collecting scans that failed QC")
    parser.add_argument("--delete_dynamic", required=False, default=False,
                        action="store_true",
                        help="Remove dynamic 4D PET NIfTI after successful preprocessing.")
    parser.add_argument("--tracer", required=False, default=None,
                        help="Tracer")

    args = parser.parse_args()

    # Load JSON
    data = load_json(args.json_parser)
    scan = select_single_scan(data)

    # Validate NIfTI against JSON metadata
    pet_valid, pet_reason = validate_pet4d_vs_json(args.pet4d, scan)
    if not pet_valid:
        print(f"FAILED NIfTI validation: {pet_reason}")
        log_failed_scan(
            csv_file=args.failed_csv,
            subject=scan.get("subject", "UNKNOWN"),
            session=scan.get("session", "UNKNOWN"),
            image_id=scan.get("image_id", "UNKNOWN"),
            tracer=args.tracer or scan.get("modality_guess", {}).get("bids_tracer", "UNKNOWN"),
            reason=pet_reason,
        )
        return

    # Determine tracer
    if not args.tracer:
        tracer = get_tracer_name(scan)
    else:
        tracer = args.tracer

    # validate protocol for frames 
    passed, frame_indices, reason = validate_protocol(scan, tracer)
    if not passed:

        print(f"FAILED QC: {reason}")

        log_failed_scan(
            csv_file=args.failed_csv,
            subject=scan.get("subject", "UNKNOWN"),
            session=scan.get("session", "UNKNOWN"),
            image_id=scan.get("image_id", "UNKNOWN"),
            tracer=tracer,
            reason=reason,
        )

        return

    window_used = (scan.get("frames", [])[frame_indices[0]].get('start_minutes_withCorrection', None),
                    scan.get("frames", [])[frame_indices[-1]].get('end_minutes_withCorrection', None))
    used_fallback = False

    print("Protocol validation passed.")
    print(f"Using frames: {frame_indices}")
    print(f"Tracer: {tracer}")
    print(f"Window used: {window_used} (minutes)")

    # Temporary workspace
    tmpdir = tempfile.mkdtemp(
        prefix="pet_preproc_",
        dir=args.scratch
    )
    print(f"Temporary workspace: {tmpdir}")
    if not os.path.exists(tmpdir):
        raise RuntimeError(f"Temporary workspace {tmpdir} does not exist.")
    try:
        subset_4d = os.path.join(tmpdir, "subset_4d.nii.gz")
        mc_4d = os.path.join(tmpdir, "subset_4d_mc.nii.gz")
        smooth_4d = os.path.join(tmpdir, "subset_4d_mc_smooth.nii.gz")
        image_3d = os.path.join(tmpdir, "subset_3d.nii.gz")
        resampled_3d = os.path.join(tmpdir, "subset_3d_resampled.nii.gz")

        # Extract frames
        extract_frames(args.pet4d, frame_indices, subset_4d, tmpdir=tmpdir)

        # Motion correction
        motion_correct(subset_4d, mc_4d)

        # Smoothing
        if args.smooth_sigma:
            smooth(mc_4d, smooth_4d, sigma_mm=args.smooth_sigma)
        else:
            smooth_4d = mc_4d

        # Temporal averaging
        temporal_average(smooth_4d, image_3d)

        if args.resample_resolution:
            resample_4d(image_3d, resampled_3d, args.resample_resolution)
        else:
            resampled_3d = image_3d

        shutil.copy(resampled_3d, args.out_static)

        nii_header = nib.load(args.pet4d)
        voxel_resolution_mm = [float(v) for v in nii_header.header.get_zooms()[:3]]

        sidecar_path = write_sidecar_json(
            output_nifti=args.out_static,
            tracer=tracer,
            window_used=window_used,
            used_fallback=used_fallback,
            frame_indices=frame_indices,
            kernel_sigma_mm=args.smooth_sigma,
            input_pet4d=args.pet4d,
            input_json=args.json_parser,
            voxel_resolution_mm=voxel_resolution_mm,
        )

        print(f"Static PET written to: {args.out_static}")
        print(f"Tracer: {tracer}")

        if args.delete_dynamic:
            if os.path.exists(args.out_static) and os.path.getsize(args.out_static) > 0:
                if os.path.exists(sidecar_path) and os.path.getsize(sidecar_path) > 0:
                    os.remove(args.pet4d)
                    print(f"Deleted dynamic 4D PET: {args.pet4d}")
                else:
                    print(f"WARNING: Output static PET json meta not found or empty — dynamic file NOT deleted: {args.pet4d}")
            else:
                print(f"WARNING: Output static PET not found or empty — dynamic file NOT deleted: {args.pet4d}")

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)



if __name__ == "__main__":
    main()
