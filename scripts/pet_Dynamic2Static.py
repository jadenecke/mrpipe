"""
Generate a static preprocessed PET scan from a dynamic 4D PET image and
a JSON metadata file produced by pet_dcm_parser.

Pipeline:
    1. Determine tracer from JSON.
    2. Select frames based on tracer-specific reference window (minutes post injection).
    3. Extract those frames from the 4D PET.
    4. Motion-correct the subset using mcflirt.
    5. Apply Gaussian smoothing (sigma in mm).
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



# -------------------------------------------------------------------------
# Tracer reference windows (modifiable)
# Minutes post injection
# -------------------------------------------------------------------------
TRACER_WINDOWS = {
    "PIB": {
        "preferred": (50, 70),
        "allowed": [
            (40, 70),
            (40, 60),
        ],
    },
    "FDG": {
        "preferred": (30, 60),
        "allowed": [
            (30, 45),
        ],
    },
    "FBB": {
        "preferred": (90, 110),
        "allowed": [

        ],
    },
    "AV45": {
        "preferred": (50, 70),
        "allowed": [

        ],
    },
    "FMM": {
        "preferred": (90, 110),
        "allowed": [

        ],
    },
    "NAV4694": {
        "preferred": (50, 70),
        "allowed": [

        ],
    },
    "AV1451": {
        "preferred": (80, 100),
        "allowed": [

        ],
    },
    "PI2620": {
        "preferred": (45, 75),
        "allowed": [

        ],
    },
    "MK6240": {
        "preferred": (90, 110),
        "allowed": [

        ],
    },
    "GTP1": {
        "preferred": (60, 90),
        "allowed": [

        ],
    },
    "RO948": {
        "preferred": (70, 90),
        "allowed": [

        ],
    },
}



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
):
    """
    Write preprocessing parameters to a JSON file next to the output NIfTI.
    Example: output.nii.gz → output.json
    """
    sidecar_path = os.path.splitext(output_nifti)[0] + ".json"

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
            "output_file": output_nifti,
        }
    }

    with open(sidecar_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Sidecar JSON written to: {sidecar_path}")




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

def get_windows_for_tracer(tracer: str) -> Dict[str, Any]:
    if tracer not in TRACER_WINDOWS:
        raise ValueError(f"Tracer {tracer!r} not in allowed list.")
    return TRACER_WINDOWS[tracer]


def try_select_frames(scan: Dict[str, Any], window: Tuple[float, float]) -> List[int]:
    start_min, end_min = window
    selected = []

    for idx, frame in enumerate(scan.get("frames", [])):
        mid = frame.get("mid_frame_minutes_withCorrection")
        if mid is None:
            continue
        try:
            mid_val = float(mid)
        except Exception:
            continue
        if start_min <= mid_val <= end_min:
            selected.append(idx)

    return selected


def select_frames_with_fallback(scan: Dict[str, Any], tracer: str) -> Tuple[List[int], Tuple[float, float], bool]:
    """
    Returns:
        frame_indices: list of selected frames
        window_used: (start_min, end_min)
        used_fallback: bool
    """

    windows = get_windows_for_tracer(tracer)

    # 1. Try preferred window
    preferred = windows["preferred"]
    frames = try_select_frames(scan, preferred)
    if frames:
        return frames, preferred, False

    # 2. Try allowed fallback windows
    for w in windows["allowed"]:
        frames = try_select_frames(scan, w)
        if frames:
            return frames, w, True

    raise ValueError(
        f"No frames found for tracer {tracer} in preferred or allowed windows."
    )


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



def motion_correct(input_4d: str, output_4d: str) -> None:
    run([
        "mcflirt",
        "-in", input_4d,
        "-out", output_4d,
        "-refvol", "0",
        "-plots",
        "-report",
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
    parser.add_argument("--pet4d", required=True, help="Dynamic 4D PET NIfTI.")
    parser.add_argument("--json", required=True, help="Metadata JSON from pet_dcm_parser.")
    parser.add_argument("--kernel-sigma-mm", type=float, default=4.0,
                        help="Gaussian smoothing sigma (mm).")
    parser.add_argument("--out-static", required=True,
                        help="Output static PET NIfTI.")
    parser.add_argument(
        "--scratch",
        required=True,
        help="Path to an existing scratch directory. A temporary subdirectory will be created inside it."
    )
    parser.add_argument(
        "--tracer",
        required=False, default=None,
        help="Path to an existing scratch directory. A temporary subdirectory will be created inside it."
    )

    args = parser.parse_args()

    # Load JSON
    data = load_json(args.json)
    scan = select_single_scan(data)

    # Determine tracer
    if not args.tracer:
        tracer = get_tracer_name(scan)
    else:
        tracer = args.tracer
    frame_indices, window_used, used_fallback = select_frames_with_fallback(scan, tracer)

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

        # Extract frames
        extract_frames(args.pet4d, frame_indices, subset_4d, tmpdir=tmpdir)

        # Motion correction
        motion_correct(subset_4d, mc_4d)

        # Smoothing
        #smooth(mc_4d, smooth_4d, sigma_mm=args.kernel_sigma_mm)

        # Temporal averaging
        temporal_average(mc_4d, args.out_static)

        print(f"Static PET written to: {args.out_static}")
        print(f"Tracer: {tracer}")
        print(f"Window used (min post injection): {window_used}")
        print(f"Used fallback window: {used_fallback}")
        print(f"Frames used (0-based): {frame_indices}")

        write_sidecar_json(
            output_nifti=args.out_static,
            tracer=tracer,
            window_used=window_used,
            used_fallback=used_fallback,
            frame_indices=frame_indices,
            kernel_sigma_mm=args.kernel_sigma_mm,
            input_pet4d=args.pet4d,
            input_json=args.json,
        )

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)



if __name__ == "__main__":
    main()
