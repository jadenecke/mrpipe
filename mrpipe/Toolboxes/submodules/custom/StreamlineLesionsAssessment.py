
#!/usr/bin/env python3
"""
StreamlineLesionsAssessment

Implements a CLI pipeline to assess lesion effects along white-matter streamlines
using MRtrix3, ANTs, and FSL utilities.

Assumptions
- TCK files and HCP100 template are provided in HCP space.
- All masks and modality images are initially in subject space and will be
  warped to template space using provided ANTs affine + deformable transforms.

High-level steps
1) Warp masks and modality NIfTIs to template space (antsApplyTransforms).
2) If lesion mask available: split streamlines into affected/unaffected (tckedit).
3) Restrict streamlines to white matter (tckedit -mask), per group.
4) Resample streamlines to 100 points (tckresample).
5) Sample each modality along resampled streamlines (tcksample), getting Nx100.
6) Plot per-modality along-tract line charts (mean ± std), overlay groups if any.
7) Compute per-index statistic (mean|median|min|max) and append to CSV (100 vals).
8) Cleanup resampled/WM-limited TCKs and Nx100 text files (unless --keep-intermediate).
9) Create GM-limited TCKs (overall and/or begin/end) per group (tckedit -mask).
10) Sample with -stat_tck <stat> to get one number per streamline within GM.
11) Boxplots per modality, with affected & unaffected in same axes; optionally begin/end.
12) Compute mean of per-streamline stats; append GM stats to CSV row.
13) Cleanup GM-limited TCKs/text files (unless --keep-intermediate).
14) Stitch images into a per-TCK JPEG: [begin-boxplot or overall] | line-chart | [end-boxplot].

Notes
- This script prints readable step banners and captures stdout/stderr from tools.
- It performs basic input and post-step existence checks and raises errors if needed.
"""

import argparse
import os
import sys
import shutil
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image


# ----------------------------- Utilities ------------------------------------


def log_step(title: str):
    print("\n" + "=" * 80)
    print(f"[STEP] {title}")
    print("=" * 80, flush=True)


def log_info(msg: str):
    print(f"[INFO] {msg}", flush=True)


def run_cmd(cmd: List[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess:
    log_info("Running: " + " ".join(cmd))
    try:
        result = subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result
    except subprocess.CalledProcessError as e:
        print(e.stdout)
        print(e.stderr, file=sys.stderr)
        raise


def ensure_exists(path: str, what: str = "file"):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Expected {what} not found: {path}")


def which_or_die(binary: str):
    p = shutil.which(binary)
    if p is None:
        raise RuntimeError(f"Required binary '{binary}' not found in PATH.")
    return p


def is_mask_path(path: str) -> bool:
    base = os.path.basename(path).lower()
    return any(k in base for k in ["mask", "lesion", "wm", "white", "gm", "gray", "grey"])  # heuristic


def make_dirs(path: str):
    os.makedirs(path, exist_ok=True)


def save_csv_row(csv_path: str, header: List[str], values: List):
    need_header = not os.path.exists(csv_path)
    with open(csv_path, "a") as f:
        if need_header:
            f.write(",".join(header) + "\n")
        line = ",".join(str(v) for v in values)
        f.write(line + "\n")


# ----------------------------- ANTs / MRtrix / FSL wrappers ------------------


def ants_apply_transform(in_img: str, out_img: str, ref_img: str, warp: str, affine: str, is_mask: bool):
    interp = "NearestNeighbor" if is_mask else "BSpline"
    cmd = [
        which_or_die("antsApplyTransforms"),
        "-d", "3",
        "-i", in_img,
        "-r", ref_img,
        "-t", warp,
        "-t", affine,
        "-o", out_img,
        "-n", interp,
    ]
    run_cmd(cmd)
    ensure_exists(out_img, "warped image")


def fslmaths_bin(in_img: str, out_img: str, thr: float = 0.5):
    # Binarize: thr then -bin
    cmd = [
        which_or_die("fslmaths"),
        in_img,
        "-thr", str(thr),
        "-bin",
        out_img,
    ]
    run_cmd(cmd)
    ensure_exists(out_img, "binarized mask")


def fslmaths_mul_bin(in_img_a: str, in_img_b: str, out_img: str):
    # Multiply two masks and binarize
    cmd = [
        which_or_die("fslmaths"),
        in_img_a,
        "-mul", in_img_b,
        "-bin",
        out_img,
    ]
    run_cmd(cmd)
    ensure_exists(out_img, "multiplied binarized mask")


def tckedit_include(in_tck: str, roi_img: str, out_tck: str):
    cmd = [which_or_die("tckedit"), in_tck, out_tck, "-include", roi_img]
    run_cmd(cmd)
    ensure_exists(out_tck, "TCK include output")


def tckedit_exclude(in_tck: str, roi_img: str, out_tck: str):
    cmd = [which_or_die("tckedit"), in_tck, out_tck, "-exclude", roi_img]
    run_cmd(cmd)
    ensure_exists(out_tck, "TCK exclude output")


def tckedit_mask(in_tck: str, mask_img: str, out_tck: str):
    # Restrict streamlines to within mask; MRtrix tckedit -mask crops to non-zero voxels.
    cmd = [which_or_die("tckedit"), in_tck, out_tck, "-mask", mask_img]
    run_cmd(cmd)
    ensure_exists(out_tck, "TCK masked output")


def tckresample_num(in_tck: str, out_tck: str, num: int = 100):
    cmd = [which_or_die("tckresample"), in_tck, out_tck, "-num", str(num)]
    run_cmd(cmd)
    ensure_exists(out_tck, "resampled TCK")


def tcksample_values(in_tck: str, img: str, out_txt: str):
    # Default is per-vertex values; header line starts with '#'
    cmd = [which_or_die("tcksample"), in_tck, img, out_txt]
    run_cmd(cmd)
    ensure_exists(out_txt, "tcksample output")


def tcksample_stat(in_tck: str, img: str, stat: str, out_txt: str):
    # One value per streamline according to stat across all vertices
    cmd = [which_or_die("tcksample"), in_tck, img, out_txt, "-stat_tck", stat]
    run_cmd(cmd)
    ensure_exists(out_txt, "tcksample stat output")


# ----------------------------- Plotting helpers ------------------------------


def load_matrix_from_txt(txt_path: str) -> np.ndarray:
    # tcksample may write a comment line starting with '#'
    data = np.loadtxt(txt_path, comments="#")
    if data.ndim == 1:
        data = data[None, :]
    return data


def plot_linechart(
    mean_vecs: Dict[str, np.ndarray],
    std_vecs: Dict[str, np.ndarray],
    per_streamlines: Dict[str, np.ndarray],
    title: str,
    out_png: str,
    max_streamlines_per_group: int = 2000,
):
    """Plot along-tract curves.

    - Draw each individual streamline curve (slightly transparent) per group.
    - Overlay group mean curve and std band.
    """
    plt.figure(figsize=(8, 3))
    xs = np.arange(1, 101)

    labels = list(mean_vecs.keys())
    color_cycle = []
    prop_cyc = plt.rcParams.get("axes.prop_cycle", None)
    if prop_cyc is not None:
        color_cycle = prop_cyc.by_key().get("color", [])

    for i, label in enumerate(labels):
        color = (color_cycle[i % len(color_cycle)] if color_cycle else None)
        meanv = mean_vecs[label]
        stdv = std_vecs.get(label)

        # 1) Individual streamline curves (transparent)
        mat = per_streamlines.get(label)
        if mat is not None:
            mat = np.asarray(mat)
            if mat.ndim == 1:
                mat = mat[None, :]
            n = mat.shape[0]
            if max_streamlines_per_group and n > max_streamlines_per_group:
                idx = np.linspace(0, n - 1, num=max_streamlines_per_group, dtype=int)
                mat = mat[idx]
            for row in mat:
                plt.plot(xs, row, color=color, alpha=0.08, linewidth=0.6, zorder=1)

        # 2) Std band
        if stdv is not None:
            plt.fill_between(xs, meanv - stdv, meanv + stdv, color=color, alpha=0.2, zorder=2)

        # 3) Mean curve on top
        plt.plot(xs, meanv, label=label, color=color, linewidth=2.0, zorder=3)

    plt.xlabel("Index (1-100)")
    plt.ylabel("Intensity")
    plt.title(title)
    if len(mean_vecs) > 1:
        plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()
    ensure_exists(out_png, "line chart PNG")


def plot_boxplot(values_by_group: Dict[str, np.ndarray], title: str, out_png: str):
    # values_by_group maps group label -> 1D array of per-streamline stats
    labels = list(values_by_group.keys())
    data = [np.asarray(values_by_group[k]).ravel() for k in labels]
    plt.figure(figsize=(4, 3))
    b = plt.boxplot(data, labels=labels, patch_artist=True)
    colors = ["tab:blue", "tab:orange", "tab:green", "tab:red"]
    for patch, color in zip(b['boxes'], colors * ((len(labels) + len(colors) - 1) // len(colors))):
        patch.set_facecolor(color)
    plt.ylabel("Value")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()
    ensure_exists(out_png, "boxplot PNG")


def stitch_images_horiz(images: List[str], out_path: str, bg=(255, 255, 255)):
    imgs = [Image.open(p) for p in images if p and os.path.exists(p)]
    if not imgs:
        return
    heights = [im.height for im in imgs]
    max_h = max(heights)
    widths = [im.width for im in imgs]
    total_w = sum(widths)
    canvas = Image.new("RGB", (total_w, max_h), bg)
    x = 0
    for im in imgs:
        canvas.paste(im, (x, 0))
        x += im.width
    canvas.save(out_path, quality=90)
    ensure_exists(out_path, "stitched image")


def stitch_modalities_rows(rows: List[List[str]], out_path: str):
    # rows: list of lists of image paths (left->right) for each modality
    # Create per-row horizontal, then stack vertically
    row_images = []
    tmp_row_paths = []
    try:
        for i, row in enumerate(rows):
            tmp = out_path.replace(".jpg", f"_row{i}.jpg")
            stitch_images_horiz(row, tmp)
            if os.path.exists(tmp):
                row_images.append(Image.open(tmp))
                tmp_row_paths.append(tmp)
        if not row_images:
            return
        widths = [im.width for im in row_images]
        heights = [im.height for im in row_images]
        max_w = max(widths)
        total_h = sum(heights)
        canvas = Image.new("RGB", (max_w, total_h), (255, 255, 255))
        y = 0
        for im in row_images:
            # left-align each row
            canvas.paste(im, (0, y))
            y += im.height
        canvas.save(out_path, quality=90)
        ensure_exists(out_path, "final stitched image")
    finally:
        # cleanup temporary row images
        for p in tmp_row_paths:
            try:
                os.remove(p)
            except Exception:
                pass


# ----------------------------- Core pipeline ---------------------------------


@dataclass
class Inputs:
    tcks: List[str]
    template: str
    warp: str
    affine: str
    lesion: Optional[str]
    wm_mask: str
    gm_mask: str
    gm_thr: float
    gm_begin: Optional[str]
    gm_end: Optional[str]
    modalities: Dict[str, str]  # name -> path
    out_dir: str
    keep_intermediate: bool
    stat: str
    threads: int
    csv: str


def parse_args() -> Inputs:
    p = argparse.ArgumentParser(description="Streamline Lesions Assessment (MRtrix3/ANTs/FSL)")
    p.add_argument("--tck", nargs="+", required=True, help="Input TCK file(s) in template space")
    p.add_argument("--template", required=True, help="HCP100 template NIfTI in template space")
    p.add_argument("--warp", required=True, help="ANTs deformable transform (subject->template)")
    p.add_argument("--affine", required=True, help="ANTs affine transform (subject->template)")
    p.add_argument("--lesion", default=None, help="Subject-space lesion mask NIfTI (optional)")
    p.add_argument("--wm", required=True, help="Subject-space white matter mask NIfTI")
    p.add_argument("--gm", required=True, help="Subject-space gray matter probability map NIfTI (required). It will be warped and thresholded to a GM mask in template space. If --gm_begin/--gm_end are provided, they will be limited (multiplied) by this GM mask after warping.")
    p.add_argument("--gm_begin", default=None, help="Subject-space begin gray matter mask NIfTI (optional)")
    p.add_argument("--gm_end", default=None, help="Subject-space end gray matter mask NIfTI (optional)")
    p.add_argument("--gm-thr", type=float, default=0.5, help="Threshold for GM probability map after warping (default: 0.5)")
    p.add_argument("--modality", "-m", action="append", default=[], help="Modality image in subject space; optionally name=path. Repeatable.")
    p.add_argument("--out", required=True, help="Output directory")
    p.add_argument("--csv", default=None, help="Path to common CSV (default: <out>/results.csv)")
    p.add_argument("--stat", default="mean", choices=["mean", "median", "min", "max"], help="Statistic for steps 7 & 10-12 (default: mean)")
    p.add_argument("--threads", type=int, default=1, help="Threads to use where applicable")
    p.add_argument("--keep-intermediate", action="store_true", help="Keep intermediate files")

    args = p.parse_args()

    # Parse modalities into dict name->path
    modalities: Dict[str, str] = {}
    for m in args.modality:
        if "=" in m:
            name, path = m.split("=", 1)
            name = name.strip()
            path = path.strip()
        else:
            path = m.strip()
            base = os.path.basename(path)
            # strip .nii or .nii.gz
            name = base
            for suff in [".nii.gz", ".nii", ".mif"]:
                if name.endswith(suff):
                    name = name[: -len(suff)]
                    break
        modalities[name] = path

    out_dir = args.out
    make_dirs(out_dir)
    csv_path = args.csv or os.path.join(out_dir, "results.csv")

    return Inputs(
        tcks=args.tck,
        template=args.template,
        warp=args.warp,
        affine=args.affine,
        lesion=args.lesion,
        wm_mask=args.wm,
        gm_mask=args.gm,
        gm_thr=args.gm_thr,
        gm_begin=args.gm_begin,
        gm_end=args.gm_end,
        modalities=modalities,
        out_dir=out_dir,
        keep_intermediate=args.keep_intermediate,
        stat=args.stat,
        threads=args.threads,
        csv=csv_path,
    )


def warp_all_subject_to_template(inputs: Inputs, work_dir: str) -> Dict[str, str]:
    """Warp masks + modalities from subject to template space.
    Returns mapping name->warped path.
    GM is treated as probability map: warped with image interpolation and thresholded to binary.
    Begin/end GM are true masks: warped with NearestNeighbor, not binarized post-warp; then limited by GM mask.
    """
    log_step("Step 1: Warp masks and modality images to template space (antsApplyTransforms)")
    ref = inputs.template
    out_paths: Dict[str, str] = {}

    # Warp WM mask (required)
    wm_warped = os.path.join(work_dir, "wm_mask_warped.nii.gz")
    ants_apply_transform(inputs.wm_mask, wm_warped, ref, inputs.warp, inputs.affine, is_mask=True)
    wm_warped_bin = os.path.join(work_dir, "wm_mask_warped_bin.nii.gz")
    fslmaths_bin(wm_warped, wm_warped_bin, thr=0.5)
    out_paths["wm_mask"] = wm_warped_bin

    # Lesion mask (optional)
    if inputs.lesion:
        lesion_warped = os.path.join(work_dir, "lesion_warped.nii.gz")
        ants_apply_transform(inputs.lesion, lesion_warped, ref, inputs.warp, inputs.affine, is_mask=True)
        lesion_warped_bin = os.path.join(work_dir, "lesion_warped_bin.nii.gz")
        fslmaths_bin(lesion_warped, lesion_warped_bin, thr=0.5)
        out_paths["lesion"] = lesion_warped_bin

    # GM masks (gm required as probability map; gm_begin/gm_end optional masks limited by gm)
    gm_warped = os.path.join(work_dir, "gm_warped_prob.nii.gz")
    # Use image interpolation for probabilities (not NN)
    ants_apply_transform(inputs.gm_mask, gm_warped, ref, inputs.warp, inputs.affine, is_mask=False)
    gm_warped_bin = os.path.join(work_dir, "gm_warped_bin.nii.gz")
    fslmaths_bin(gm_warped, gm_warped_bin, thr=inputs.gm_thr)
    out_paths["gm"] = gm_warped_bin
    if inputs.gm_begin:
        gmb_warped = os.path.join(work_dir, "gm_begin_warped.nii.gz")
        ants_apply_transform(inputs.gm_begin, gmb_warped, ref, inputs.warp, inputs.affine, is_mask=True)
        gmb_limited = os.path.join(work_dir, "gm_begin_limited.nii.gz")
        # Limit begin mask by the GM mask; no need to binarize gmb_warped beforehand if NN was used
        fslmaths_mul_bin(gmb_warped, gm_warped_bin, gmb_limited)
        out_paths["gm_begin"] = gmb_limited
    if inputs.gm_end:
        gme_warped = os.path.join(work_dir, "gm_end_warped.nii.gz")
        ants_apply_transform(inputs.gm_end, gme_warped, ref, inputs.warp, inputs.affine, is_mask=True)
        gme_limited = os.path.join(work_dir, "gm_end_limited.nii.gz")
        fslmaths_mul_bin(gme_warped, gm_warped_bin, gme_limited)
        out_paths["gm_end"] = gme_limited

    # Warp modalities (linear interp)
    warped_modalities: Dict[str, str] = {}
    for name, path in inputs.modalities.items():
        outp = os.path.join(work_dir, f"{name}_warped.nii.gz")
        ants_apply_transform(path, outp, ref, inputs.warp, inputs.affine, is_mask=False)
        warped_modalities[name] = outp
    out_paths["modalities"] = warped_modalities  # type: ignore
    return out_paths


def split_by_lesion_if_needed(in_tck: str, lesion_mask_tpl: Optional[str], work_dir: str) -> Dict[str, str]:
    log_step("Step 2: Split streamlines by lesion mask (if provided)")
    groups: Dict[str, str] = {}
    if lesion_mask_tpl and os.path.exists(lesion_mask_tpl):
        affected = os.path.join(work_dir, "tracks_affected.tck")
        unaffected = os.path.join(work_dir, "tracks_unaffected.tck")
        tckedit_include(in_tck, lesion_mask_tpl, affected)
        tckedit_exclude(in_tck, lesion_mask_tpl, unaffected)
        groups["affected"] = affected
        groups["unaffected"] = unaffected
    else:
        groups["all"] = in_tck
    return groups


def restrict_to_wm_and_resample(groups: Dict[str, str], wm_mask_tpl: str, work_dir: str) -> Dict[str, Tuple[str, str]]:
    log_step("Step 3 & 4: Restrict to white matter and resample to 100 points")
    out: Dict[str, Tuple[str, str]] = {}
    for label, tck in groups.items():
        wm_tck = os.path.join(work_dir, f"{label}_wm.tck")
        tckedit_mask(tck, wm_mask_tpl, wm_tck)
        res_tck = os.path.join(work_dir, f"{label}_wm_resampled.tck")
        tckresample_num(wm_tck, res_tck, num=100)
        out[label] = (wm_tck, res_tck)
    return out


def sample_modalities_along_tracts(resampled_groups: Dict[str, Tuple[str, str]], modalities_tpl: Dict[str, str], work_dir: str) -> Dict[str, Dict[str, str]]:
    log_step("Step 5: tcksample along resampled tracts for each modality (Nx100)")
    out: Dict[str, Dict[str, str]] = {}
    for label, (_wm_tck, res_tck) in resampled_groups.items():
        out[label] = {}
        for mname, mpath in modalities_tpl.items():
            txt = os.path.join(work_dir, f"{label}_{mname}_samples.txt")
            tcksample_values(res_tck, mpath, txt)
            out[label][mname] = txt
    return out


def compute_stat(vec: np.ndarray, stat: str) -> float:
    if stat == "mean":
        return float(np.mean(vec))
    if stat == "median":
        return float(np.median(vec))
    if stat == "min":
        return float(np.min(vec))
    if stat == "max":
        return float(np.max(vec))
    raise ValueError(f"Unknown stat: {stat}")


def along_tract_stats_and_plot(samples_txt: Dict[str, Dict[str, str]], tck_basename: str, out_dir: str, stat: str) -> Tuple[List[str], Dict[str, Dict[str, np.ndarray]]]:
    log_step("Step 6 & 7: Plot line charts and compute per-index statistics across streamlines")
    # Returns list of created linechart paths per modality row order, and per-group per-modality 100-length arrays
    linecharts: List[str] = []
    per_group_per_mod_100: Dict[str, Dict[str, np.ndarray]] = {}
    for mname in sorted({m for g in samples_txt.values() for m in g.keys()}):
        mean_curves: Dict[str, np.ndarray] = {}
        std_curves: Dict[str, np.ndarray] = {}
        per_streamlines: Dict[str, np.ndarray] = {}
        per_group_per_mod_100[mname] = {}
        for group, md in samples_txt.items():
            if mname not in md:
                continue
            mat = load_matrix_from_txt(md[mname])  # N x 100
            per_streamlines[group] = mat
            # Compute per-index stat across streamlines for CSV
            vals_by_index = []
            for j in range(mat.shape[1]):
                vals = mat[:, j]
                vals_by_index.append(compute_stat(vals, stat))
            per_group_per_mod_100[mname][group] = np.array(vals_by_index)

            mean_curves[group] = np.mean(mat, axis=0)
            std_curves[group] = np.std(mat, axis=0)

        # Plot overlay line chart
        title = f"{tck_basename} | Along-tract: {mname}"
        out_png = os.path.join(out_dir, f"{tck_basename}_{mname}_linechart.png")
        plot_linechart(mean_curves, std_curves, per_streamlines, title, out_png)
        linecharts.append(out_png)
    return linecharts, per_group_per_mod_100


def cleanup_files(paths: List[str]):
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except Exception:
            pass


def gm_limited_stats_and_boxplots(groups: Dict[str, Tuple[str, str]], gm_paths: Dict[str, str], modalities_tpl: Dict[str, str], tck_basename: str, out_dir: str, stat: str) -> Tuple[Dict[str, Dict[str, float]], Dict[str, List[str]]]:
    """Create GM-limited TCKs (overall, begin, end as available), sample with -stat_tck,
    produce boxplots. Return dict: modality -> {group-> gm_mean_overall, gm_begin, gm_end as available},
    and dict of modality -> list of boxplot image paths in order [begin/overall, end (optional)].
    """
    log_step("Step 9-12: GM-limited stats (tckedit -mask) and boxplots")
    gm_keys = [k for k in ["gm_begin", "gm", "gm_end"] if k in gm_paths]
    out_gm_stats: Dict[str, Dict[str, float]] = {}
    boxplot_paths_by_mod: Dict[str, List[str]] = {}

    # Prepare per-modality per-group values arrays for boxplots for begin/overall/end
    per_part_values: Dict[str, Dict[str, Dict[str, np.ndarray]]] = {"gm_begin": {}, "gm": {}, "gm_end": {}}

    # Build TCKs limited to each GM region per group and sample
    temp_files_to_cleanup: List[str] = []
    for part_key in gm_keys:
        mask_img = gm_paths[part_key]
        for group, (wm_tck, _res) in groups.items():
            gm_tck = os.path.join(out_dir, f"{tck_basename}_{group}_{part_key}.tck")
            tckedit_mask(wm_tck, mask_img, gm_tck)
            temp_files_to_cleanup.append(gm_tck)
            for mname, mpath in modalities_tpl.items():
                txt = os.path.join(out_dir, f"{tck_basename}_{group}_{part_key}_{mname}_stat.txt")
                tcksample_stat(gm_tck, mpath, stat, txt)
                temp_files_to_cleanup.append(txt)
                # Load 1D values per streamline
                vals = load_matrix_from_txt(txt).ravel()
                per_part_values.setdefault(part_key, {}).setdefault(mname, {})[group] = vals

    # Boxplots and summary means
    for mname in modalities_tpl.keys():
        out_gm_stats[mname] = {}
        box_imgs: List[str] = []
        # Begin or overall (left)
        if "gm_begin" in per_part_values and mname in per_part_values["gm_begin"] and per_part_values["gm_begin"][mname]:
            title = f"{tck_basename} | {mname} | GM begin ({stat})"
            out_png = os.path.join(out_dir, f"{tck_basename}_{mname}_gm_begin_box.png")
            plot_boxplot(per_part_values["gm_begin"][mname], title, out_png)
            box_imgs.append(out_png)
            # mean of per-streamline stats per group
            for g, arr in per_part_values["gm_begin"][mname].items():
                out_gm_stats[mname][f"{g}_gm_begin"] = float(np.mean(arr))
        elif "gm" in per_part_values and mname in per_part_values["gm"] and per_part_values["gm"][mname]:
            title = f"{tck_basename} | {mname} | GM overall ({stat})"
            out_png = os.path.join(out_dir, f"{tck_basename}_{mname}_gm_box.png")
            plot_boxplot(per_part_values["gm"][mname], title, out_png)
            box_imgs.append(out_png)
            for g, arr in per_part_values["gm"][mname].items():
                out_gm_stats[mname][f"{g}_gm"] = float(np.mean(arr))

        # End (right, optional)
        if "gm_end" in per_part_values and mname in per_part_values["gm_end"] and per_part_values["gm_end"][mname]:
            title = f"{tck_basename} | {mname} | GM end ({stat})"
            out_png = os.path.join(out_dir, f"{tck_basename}_{mname}_gm_end_box.png")
            plot_boxplot(per_part_values["gm_end"][mname], title, out_png)
            box_imgs.append(out_png)
            for g, arr in per_part_values["gm_end"][mname].items():
                out_gm_stats[mname][f"{g}_gm_end"] = float(np.mean(arr))

        boxplot_paths_by_mod[mname] = box_imgs

    # Step 13: cleanup of intermediate GM files
    if temp_files_to_cleanup:
        log_step("Step 13: Cleanup GM-limited intermediate files")
        # Keep or remove based on flag handled by caller
    return out_gm_stats, boxplot_paths_by_mod


def write_csv_rows_for_tck(csv_path: str, tck_path: str, stat: str, per_group_per_mod_100: Dict[str, Dict[str, np.ndarray]], gm_stats: Dict[str, Dict[str, float]]):
    # Construct header: tck, modality, group, stat, idx_1..idx_100, optional gm, gm_begin, gm_end (per group)
    idx_cols = [f"idx_{i}" for i in range(1, 101)]
    header = ["tck", "modality", "group", "stat"] + idx_cols + ["gm", "gm_begin", "gm_end"]
    tck_base = os.path.basename(tck_path)

    # For each modality and group, write row
    groups = set()
    for mname, per_group in per_group_per_mod_100.items():
        for g in per_group.keys():
            groups.add(g)

    for mname, per_group in per_group_per_mod_100.items():
        for g, arr100 in per_group.items():
            gm = gm_stats.get(mname, {}).get(f"{g}_gm")
            gmb = gm_stats.get(mname, {}).get(f"{g}_gm_begin")
            gme = gm_stats.get(mname, {}).get(f"{g}_gm_end")
            values = [tck_base, mname, g, stat] + [f"{v:.6g}" for v in arr100] + [
                (f"{gm:.6g}" if gm is not None else ""),
                (f"{gmb:.6g}" if gmb is not None else ""),
                (f"{gme:.6g}" if gme is not None else ""),
            ]
            save_csv_row(csv_path, header, values)


def stitch_final_figure(tck_path: str, modalities: List[str], linecharts_by_mod: Dict[str, str], boxplots_by_mod: Dict[str, List[str]], out_dir: str) -> str:
    log_step("Step 14: Stitch figures into final JPEG")
    tck_base = os.path.splitext(os.path.basename(tck_path))[0]
    rows: List[List[str]] = []
    for mname in modalities:
        left = None
        right = None
        if mname in boxplots_by_mod:
            imgs = boxplots_by_mod[mname]
            if imgs:
                left = imgs[0]
            if len(imgs) > 1:
                right = imgs[1]
        center = linecharts_by_mod.get(mname)
        row = [p for p in [left, center, right] if p]
        if row:
            rows.append(row)
    out_jpg = os.path.join(out_dir, f"{tck_base}_summary.jpg")
    stitch_modalities_rows(rows, out_jpg)
    return out_jpg


def main():
    inputs = parse_args()

    # Basic tool availability checks
    for b in ["antsApplyTransforms", "tckedit", "tckresample", "tcksample", "fslmaths"]:
        which_or_die(b)

    # Global output dirs
    make_dirs(inputs.out_dir)
    common_csv = inputs.csv
    log_info(f"Common CSV: {common_csv}")

    for tck_path in inputs.tcks:
        ensure_exists(tck_path, "TCK file")
        tck_base = os.path.splitext(os.path.basename(tck_path))[0]
        tck_out_dir = os.path.join(inputs.out_dir, tck_base)
        inter_dir = os.path.join(tck_out_dir, "intermediate")
        make_dirs(tck_out_dir)
        make_dirs(inter_dir)

        # Step 1: warp
        warped = warp_all_subject_to_template(inputs, inter_dir)
        wm_tpl = warped["wm_mask"]
        lesion_tpl = warped.get("lesion")
        gm_paths = {k: v for k, v in warped.items() if k in ("gm", "gm_begin", "gm_end")}
        modalities_tpl = warped["modalities"]  # type: ignore

        # Step 2: lesion split
        groups = split_by_lesion_if_needed(tck_path, lesion_tpl, inter_dir)

        # Step 3 & 4
        groups_wm_res = restrict_to_wm_and_resample(groups, wm_tpl, inter_dir)

        # Step 5
        samples_txt = sample_modalities_along_tracts(groups_wm_res, modalities_tpl, inter_dir)

        # Step 6 & 7
        linecharts, per_group_per_mod_100 = along_tract_stats_and_plot(samples_txt, tck_base, tck_out_dir, inputs.stat)

        # Step 8: cleanup resampled, wm-limited, and Nx100 text files if not keeping
        if not inputs.keep_intermediate:
            log_step("Step 8: Cleanup WM-limited/resampled TCKs and along-tract samples")
            cleanup = []
            for label, (wm_tck, res_tck) in groups_wm_res.items():
                cleanup.extend([wm_tck, res_tck])
            for g, md in samples_txt.items():
                for _m, txt in md.items():
                    cleanup.append(txt)
            cleanup_files(cleanup)

        # Step 9-12: GM-limited stats and boxplots
        gm_stats: Dict[str, Dict[str, float]] = {}
        boxplots_by_mod: Dict[str, List[str]] = {}
        if gm_paths:
            gm_stats, boxplots_by_mod = gm_limited_stats_and_boxplots(groups_wm_res, gm_paths, modalities_tpl, tck_base, tck_out_dir, inputs.stat)
            # Step 13 cleanup of GM-limited artifacts
            if not inputs.keep_intermediate:
                log_step("Step 13: Cleanup GM-limited TCKs and text files")
                to_del = [os.path.join(tck_out_dir, f) for f in os.listdir(tck_out_dir) if any(s in f for s in ["_gm_", "_gm_begin_", "_gm_end_"]) and (f.endswith('.tck') or f.endswith('.txt'))]
                cleanup_files(to_del)

        # Write CSV rows per modality/group
        write_csv_rows_for_tck(common_csv, tck_path, inputs.stat, per_group_per_mod_100, gm_stats)

        # Step 14: stitch final figure per TCK
        linecharts_by_mod = {}
        for p in linecharts:
            # map back by modality name from filename
            bn = os.path.basename(p)
            # expects format: <tckbase>_<modname>_linechart.png
            modname = bn.replace(f"{tck_base}_", "").replace("_linechart.png", "")
            linecharts_by_mod[modname] = p
        final_jpg = stitch_final_figure(tck_path, sorted(modalities_tpl.keys()), linecharts_by_mod, boxplots_by_mod, tck_out_dir)
        log_info(f"Final figure: {final_jpg}")

    log_info("All done.")


if __name__ == "__main__":
    main()
