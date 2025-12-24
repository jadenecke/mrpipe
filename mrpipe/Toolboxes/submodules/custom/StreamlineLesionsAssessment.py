
#!/usr/bin/env python3
"""
StreamlineLesionsAssessment

Implements a CLI pipeline to assess lesion effects along white-matter streamlines
using MRtrix3, ANTs, and FSL utilities.

Assumptions
- TCK files and the reference template are in template (HCP) space.
- Subject-space inputs: WM mask, lesion mask (optional), GM probability map, and all modality images. These are warped to template space.
- Per-TCK GM begin/end masks are optional and provided already in template space. They are NOT warped; they are limited by the (warped+thresholded) GM mask.

Pipeline pseudocode (end-to-end)
- Parse CLI args and set defaults (e.g., --stat, --gm-thr, --min-wm-length-mm).
- Check required binaries in PATH: antsApplyTransforms, tckedit, tckresample, tcksample, tckstats, fslmaths, fslstats.
- For each input TCK (template space):
  1) Resolve per-TCK GM-begin/GM-end (template space) if provided.
  2) Prepare an output directory and an intermediate working directory.
  3) Prepare template-space data (warp subject-space to template; keep begin/end in template):
     - WM (mask): antsApplyTransforms (NN) -> threshold/bin (fslmaths -thr -- -bin).
     - GM (probability): antsApplyTransforms (image interp) -> threshold to binary via --gm-thr.
     - Lesion (mask, optional): antsApplyTransforms (NN) -> threshold/bin.
     - GM_begin / GM_end (template-space inputs): limit by GM mask (fslmaths -mul -bin).
     - Modalities (images): antsApplyTransforms (image interp) for each.
     - Optionally expose masks (GM, WM, Lesion) as additional modalities if --include-masks-as-modalities.
  4) Split the original TCK by lesion mask (if provided):
     - groups = {"affected": tck_include(lesion), "unaffected": tck_exclude(lesion), "all": original_tck};
       if no lesion is provided: groups = {"all": original_tck}.
  5) For each group:
     - WM-masked with optional min length filter: tckedit -mask WM [ -minlength min_wm_length_mm ] -> group_wm.tck
     - Resample to 100 points: tckresample -> group_wm_resampled.tck
  6) For each modality and each group:
     - Along-tract sampling: tcksample group_wm_resampled vs modality -> samples.txt (N_streamlines x 100)
  7) Compute per-index statistic across streamlines for each modality/group (100 values):
     - stat in {mean, median, min, max}; also compute mean and std for line plots.
     - Plot line charts per modality with individual curves, group means, and ±std.
  8) Derive core counts and lengths per group:
     - n_wm_len_filtered_group = tckstats(group_wm.tck, count)
     - mean_length (group_wm.tck, mean)
  9) Derive additional count metrics:
     - Full (non-WM) counts: per group from split tracts, plus total from original TCK.
     - WM masked (no length restriction) counts: tckedit -mask WM on split tracts; count per group.
 10) GM-limited statistics and counts (non-WM tracts limited by GM masks):
     - For each of {gm_begin, gm, gm_end} that exists:
       * Limit each original group tract by the mask (tckedit -mask).
       * Count streamlines per group and sum to a total for that GM-part.
       * For each modality, run tcksample -stat_tck <stat> to get one value per streamline; store arrays per group.
       * Plot boxplots per modality for available GM-parts.
     - Compute per-group means of the per-streamline stats for CSV: {g}_gm, {g}_gm_begin, {g}_gm_end.
 11) Compute additional per-modality group stats for CSV:
     - group_all_stats: tcksample -stat_tck on original group tracts (non-WM).
     - group_wm_stats: tcksample -stat_tck on WM-limited group tracts.
     - roi means: fslstats -k for GMmask/WMmask (per modality; same across groups).
 12) Write one CSV row per (TCK, modality, group) with all metrics listed in the data dictionary below.
 13) Optionally clean up intermediates unless --keep-intermediate.
 14) Stitch a per-TCK summary JPEG per modality row: [GM-begin or GM overall box] | [line chart] | [GM-end box].

Outputs overview
- <out>/<tck_basename>/summary.jpg: stitched summary per TCK.
- <out>/<tck_basename>/intermediate/: line charts, boxplots, temporary TCKs and text files (removed by default).
- <csv>: one row per (TCK, modality, group).

CSV data dictionary (column-by-column)
- tck: Basename of the input TCK file.
- modality: Name of the modality image used for sampling (or mask name if --include-masks-as-modalities).
- group: One of {"affected", "unaffected", "all"}. The 'all' group represents the original (unsplit) TCK and is included even when a lesion mask is provided.
- stat: The statistic used for per-index and per-streamline calculations: one of {mean, median, min, max}.
- mean_length: Mean streamline length (mm) computed on the WM-limited after-length-restriction tract for this group.
- count_original_total: Total number of streamlines in the input (original) TCK.
- count_lesion_split_total: Total number of streamlines in the unsplit, non-WM tract (after ROI filtering if applied).
- count_lesion_split_group: Number of streamlines in the current group (non-WM), i.e., from lesion-based split or "all".
- count_roi_filtered_total: Total number of streamlines that passed ROI filtering (sum over groups).
- count_roi_filtered_group: Number of streamlines that passed ROI filtering for this group.
- count_gm_intersect_total: Total number of streamlines intersecting the GM mask (sum of per-group counts limited by GM).
- count_gm_intersect_group: Number of streamlines intersecting the GM mask for this group (non-WM tract limited by GM).
- count_gm_begin_intersect_total: Total number of streamlines intersecting the GM-begin mask (sum over groups). Blank if GM-begin not provided.
- count_gm_begin_intersect_group: Group count within GM-begin. Blank if GM-begin not provided.
- count_gm_end_intersect_total: Total number of streamlines intersecting the GM-end mask (sum over groups). Blank if GM-end not provided.
- count_gm_end_intersect_group: Group count within GM-end. Blank if GM-end not provided.
- count_wm_masked_group: Number of streamlines after WM masking without any length restriction (per group).
- count_wm_masked_minlength_filtered_group: Number of streamlines after WM masking and length restriction (per group).
- stat_full_tract_<stat>: Value of tcksample -stat_tck <stat> computed on the non-WM tract for this group.
- stat_wm_limited_<stat>: Value of tcksample -stat_tck <stat> computed on the WM-limited tract for this group.
- roi_GMmask_mean: Mean intensity of the modality within the GM mask (fslstats -k) in template space; blank if GM not available.
- roi_WMmask_mean: Mean intensity of the modality within the WM mask (fslstats -k) in template space; blank if WM not available.
- idx_1 .. idx_100: Per-index statistic across streamlines (according to "stat") along the resampled 100-point streamline trajectory for this group and modality. idx_1 corresponds to the first resampled point; idx_100 to the last.
- stat_gm_intersect_mean: Mean of per-streamline values computed within the GM-limited tract (overall GM) for this group and modality; blank if GM not available.
- stat_gm_begin_intersect_mean: Mean of per-streamline values within the GM-begin-limited tract for this group and modality; blank if GM-begin not provided.
- stat_gm_end_intersect_mean: Mean of per-streamline values within the GM-end-limited tract for this group and modality; blank if GM-end not provided.

Notes
- Empty cells are written as blank strings when the metric is not applicable or could not be computed.
- All counts are derived from MRtrix3 `tckstats -output count` on the corresponding tract definition described above.
- The CSV schema is additive; previous columns are preserved for backward compatibility.
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

# Optional heavy dependencies for panel and streamline rendering
try:
    import nibabel as nib
    from nibabel.streamlines import load as load_tck
except Exception:  # nibabel optional
    nib = None
    load_tck = None
try:
    from scipy import ndimage as ndi
except Exception:
    ndi = None
try:
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  # needed for 3D projection
except Exception:
    Axes3D = None

try:
    import graphviz
except ImportError:
    graphviz = None


# ----------------------------- Utilities ------------------------------------


# Global flag for command logging
LOG_COMMANDS_TO_TEXT: Optional[str] = None


class GraphTracker:
    def __init__(self, enabled: bool = False):
        self.enabled = enabled and graphviz is not None
        self.nodes = set()
        self.edges = []  # List of (src_id, dst_id, label)
        self.cmd_count = 0
        self.last_cmd_id = None

    def add_command(self, cmd_name: str, inputs: List[str], outputs: List[str]) -> Optional[str]:
        if not self.enabled:
            return None
        cmd_id = f"cmd_{self.cmd_count}_{cmd_name}"
        self.cmd_count += 1
        self.last_cmd_id = cmd_id
        # Nodes: (id, label, color, shape)
        self.nodes.add((cmd_id, cmd_name, "lightblue", "box"))
        for inp in inputs:
            if inp:
                inp_id = f"file_{inp}"
                self.nodes.add((inp_id, os.path.basename(inp), "lightgreen", "ellipse"))
                self.edges.append((inp_id, cmd_id, None))
        for outp in outputs:
            if outp:
                outp_id = f"file_{outp}"
                self.nodes.add((outp_id, os.path.basename(outp), "lightcoral", "ellipse"))
                self.edges.append((cmd_id, outp_id, None))
        return cmd_id

    def add_csv_variable(self, var_name: str, source_node: Optional[str] = None, label: Optional[str] = None):
        """Add a CSV variable node and link it to a source node.
        
        source_node should be the ID of a file or command node.
        """
        if not self.enabled:
            return
        var_id = f"var_{var_name}"
        self.nodes.add((var_id, var_name, "lightyellow", "note"))
        if source_node:
            self.edges.append((source_node, var_id, label))

    def export(self, out_path: str):
        if not self.enabled:
            return
        dot = graphviz.Digraph(comment="Pipeline Flow Chart")
        dot.attr(rankdir="LR")
        for node_id, label, color, shape in self.nodes:
            dot.node(node_id, label, style="filled", fillcolor=color, shape=shape)
        for src, dst, label in self.edges:
            if label:
                dot.edge(src, dst, label=label)
            else:
                dot.edge(src, dst)

        fmt = "jpeg"
        if out_path.lower().endswith((".pdf", ".svg", ".eps")):
            fmt = out_path.lower().split(".")[-1]
            out_base = out_path[:-(len(fmt)+1)]
        else:
            out_base = out_path
            if out_path.lower().endswith(".jpg") or out_path.lower().endswith(".jpeg"):
                 out_base = out_path.rsplit(".", 1)[0]
                 fmt = "jpeg"

        dot.render(out_base, format=fmt, cleanup=True)
        print(f"[INFO] Flow chart exported to {out_path} (actual: {out_base}.{fmt})")


# Global tracker
TRACKER = GraphTracker()


def log_step(title: str):
    msg = f"[STEP] {title}"
    print("\n" + "=" * 80)
    print(msg)
    print("=" * 80, flush=True)
    if LOG_COMMANDS_TO_TEXT:
        with open(LOG_COMMANDS_TO_TEXT, "a") as f:
            f.write("\n" + "=" * 80 + "\n")
            f.write(msg + "\n")
            f.write("=" * 80 + "\n")


def log_info(msg: str, to_text_file: Optional[str] = None):
    if to_text_file is None:
        to_text_file = LOG_COMMANDS_TO_TEXT
    print(f"[INFO] {msg}", flush=True)
    if to_text_file:
        with open(to_text_file, "a") as f:
            f.write(f"[INFO] {msg}\n")


def run_cmd(cmd: List[str], cwd: Optional[str] = None, inputs: Optional[List[str]] = None, outputs: Optional[List[str]] = None) -> subprocess.CompletedProcess:
    log_info("Running: " + " ".join(cmd))
    if inputs or outputs:
        TRACKER.add_command(os.path.basename(cmd[0]), inputs or [], outputs or [])
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

def make_dirs(path: str):
    os.makedirs(path, exist_ok=True)


def save_csv_row(csv_path: str, header: List[str], values: List):
    need_header = not os.path.exists(csv_path)
    with open(csv_path, "a") as f:
        if need_header:
            f.write(",".join(header) + "\n")
        line = ",".join(str(v) for v in values)
        f.write(line + "\n")
    # Mark CSV as an output of the process if tracking
    TRACKER.add_command("write_csv", [], [csv_path])


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
    run_cmd(cmd, inputs=[in_img, ref_img, warp, affine], outputs=[out_img])
    ensure_exists(out_img, "warped image")


def fslmaths_bin(in_img: str, out_img: str, thr: float = 0.5):
    cmd = [
        which_or_die("fslmaths"),
        in_img,
        "-thr", str(thr),
        "-bin",
        out_img,
    ]
    run_cmd(cmd, inputs=[in_img], outputs=[out_img])
    ensure_exists(out_img, "binarized mask")


def fslmaths_dil_bin(in_img: str, out_img: str, mm: float):
    """Dilate and binarize."""
    cmd = [
        which_or_die("fslmaths"),
        in_img,
        "-kernel", "sphere", str(mm),
        "-dilM",
        "-bin",
        out_img,
    ]
    run_cmd(cmd, inputs=[in_img], outputs=[out_img])
    ensure_exists(out_img, "dilated binary mask")


def fslmaths_mul_bin(in_img_a: str, in_img_b: str, out_img: str):
    # Multiply two masks and binarize
    cmd = [
        which_or_die("fslmaths"),
        in_img_a,
        "-mul", in_img_b,
        "-bin",
        out_img,
    ]
    run_cmd(cmd, inputs=[in_img_a, in_img_b], outputs=[out_img])
    ensure_exists(out_img, "multiplied binarized mask")


def fslstats_masked_mean(in_img: str, mask_img: str) -> Tuple[Optional[float], Optional[str]]:
    """Return mean of image within mask using FSL fslstats -k <mask> -m.

    Returns None on failure.
    """
    try:
        cmd = [which_or_die("fslstats"), in_img, "-k", mask_img, "-m"]
        log_info("Running: " + " ".join(cmd))
        cmd_id = TRACKER.add_command("fslstats", [in_img, mask_img], [])
        res = subprocess.run(cmd, check=True, capture_output=True, text=True)
        out = (res.stdout or "").strip()
        if not out:
            return None, cmd_id
        return float(out.split()[0]), cmd_id
    except Exception:
        return None, None


def fslstats_is_empty(mask_img: str) -> bool:
    """Check if mask is empty (all zeros) using fslstats -V."""
    try:
        cmd = [which_or_die("fslstats"), mask_img, "-V"]
        res = subprocess.run(cmd, check=True, capture_output=True, text=True)
        out = (res.stdout or "").strip()
        if not out:
            return True
        # fslstats -V returns <voxels> <volume>
        voxels = int(out.split()[0])
        return voxels == 0
    except Exception:
        # If fslstats fails, assume it might be empty or invalid
        return True


def tckedit_include(in_tck: str, roi_img: str, out_tck: str):
    cmd = [which_or_die("tckedit"), in_tck, out_tck, "-include", roi_img]
    run_cmd(cmd, inputs=[in_tck, roi_img], outputs=[out_tck])
    ensure_exists(out_tck, "TCK include output")


def tckedit_exclude(in_tck: str, roi_img: str, out_tck: str):
    cmd = [which_or_die("tckedit"), in_tck, out_tck, "-exclude", roi_img]
    run_cmd(cmd, inputs=[in_tck, roi_img], outputs=[out_tck])
    ensure_exists(out_tck, "TCK exclude output")


def tckedit_mask(in_tck: str, mask_img: str, out_tck: str):
    # Restrict streamlines to within mask; MRtrix tckedit -mask crops to non-zero voxels.
    cmd = [which_or_die("tckedit"), in_tck, out_tck, "-mask", mask_img]
    run_cmd(cmd, inputs=[in_tck, mask_img], outputs=[out_tck])
    ensure_exists(out_tck, "TCK masked output")


def tckedit_mask_minlen(in_tck: str, mask_img: str, out_tck: str, min_len_mm: Optional[float] = None):
    """Like tckedit_mask, but optionally enforces a minimum streamline length in mm."""
    cmd = [which_or_die("tckedit"), in_tck, out_tck, "-mask", mask_img]
    if min_len_mm is not None and float(min_len_mm) > 0:
        cmd += ["-minlength", f"{float(min_len_mm):.6g}"]
    run_cmd(cmd, inputs=[in_tck, mask_img], outputs=[out_tck])
    ensure_exists(out_tck, "TCK masked/filtered output")


def tckedit_double_include(in_tck: str, roi1: str, roi2: str, out_tck: str):
    """Include only streamlines that intersect both roi1 and roi2."""
    cmd = [which_or_die("tckedit"), in_tck, out_tck, "-include", roi1, "-include", roi2]
    run_cmd(cmd, inputs=[in_tck, roi1, roi2], outputs=[out_tck])
    ensure_exists(out_tck, "TCK double-include output")


def tckresample_num(in_tck: str, out_tck: str, num: int = 100):
    cmd = [which_or_die("tckresample"), in_tck, out_tck, "-num", str(num)]
    run_cmd(cmd, inputs=[in_tck], outputs=[out_tck])
    ensure_exists(out_tck, "resampled TCK")


# Note: We intentionally do not support merging multiple group TCKs into a single
# "overall" tract anymore, as per latest requirements. The previous helper
# `tckedit_union` has been removed.


def tcksample_values(in_tck: str, img: str, out_txt: str):
    # Default is per-vertex values; header line starts with '#'
    cmd = [which_or_die("tcksample"), in_tck, img, out_txt]
    run_cmd(cmd, inputs=[in_tck, img], outputs=[out_txt])
    ensure_exists(out_txt, "tcksample output")


def tcksample_stat(in_tck: str, img: str, stat: str, out_txt: str):
    # One value per streamline according to stat across all vertices
    cmd = [which_or_die("tcksample"), in_tck, img, out_txt, "-stat_tck", stat]
    run_cmd(cmd, inputs=[in_tck, img], outputs=[out_txt])
    ensure_exists(out_txt, "tcksample stat output")


def tcksample_stat_mean(in_tck: str, img: str, stat: str, out_txt: str) -> Tuple[Optional[float], Optional[str]]:
    """Run tcksample -stat_tck and return the mean across streamlines.

    Writes per-streamline values into out_txt and computes their mean.
    Returns (None, source_id) on failure or empty results.
    """
    try:
        tcksample_stat(in_tck, img, stat, out_txt)
        source_id = f"file_{out_txt}"
        arr = load_matrix_from_txt(out_txt)
        if arr.size == 0:
            return None, source_id
        return float(np.mean(arr)), source_id
    except Exception:
        return None, None


# MRtrix3: tckstats -output <field>
def tckstats_output(in_tck: str, field: str) -> Tuple[Optional[float], Optional[str]]:
    """Return numeric output from `tckstats -output <field>`.

    Common fields: count, mean, min, max, median, length_mean, etc.
    Returns (None, source_id) if the tract is empty or parsing fails.
    """
    try:
        cmd = [which_or_die("tckstats"), in_tck, "-output", field]
        log_info("Running: " + " ".join(cmd))
        cmd_id = TRACKER.add_command("tckstats", [in_tck], [])
        res = subprocess.run(cmd, check=True, capture_output=True, text=True)
        out = (res.stdout or "").strip()
        if not out:
            return None, cmd_id
        # In case multiple lines, take last non-empty
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        if not lines:
            return None, cmd_id
        val_str = lines[-1].split()[-1]
        return float(val_str), cmd_id
    except Exception:
        return None, None


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
    - Overlay group mean curve and std as two dashed lines (no fill).
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
                plt.plot(xs, row, color=color, alpha=0.01, linewidth=0.3, zorder=1)

        # 2) Std as dashed lines (mean ± std)
        if stdv is not None:
            plt.plot(xs, meanv - stdv, color=color, linestyle="--", linewidth=1.0, alpha=0.7, zorder=2)
            plt.plot(xs, meanv + stdv, color=color, linestyle="--", linewidth=1.0, alpha=0.7, zorder=2)

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
    # Prefer specific colors for standard groups
    prefer_colors = {"unaffected": "tab:blue", "affected": "tab:orange"}
    default_cycle = ["tab:green", "tab:red", "tab:purple", "tab:brown", "tab:pink", "tab:gray", "tab:olive", "tab:cyan"]
    colors = []
    for i, lab in enumerate(labels):
        colors.append(prefer_colors.get(lab, default_cycle[i % len(default_cycle)]))
    for patch, color in zip(b['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_edgecolor('black')
    plt.ylabel("Value")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()
    ensure_exists(out_png, "boxplot PNG")


# ------------- Parallel worker tasks for per‑modality subplot rendering ---------
from typing import Any

def worker_linechart_task(args: Tuple[str, str, str, str, Dict[str, str]]) -> Tuple[str, str, Dict[str, List[float]]]:
    """Process-safe worker to render a single modality line chart.

    Args tuple: (mname, tck_basename, out_dir, stat, samples_for_modality)
    Returns: (mname, out_png, per100_dict)
    """
    mname, tck_basename, out_dir, stat, samples_for_modality = args
    mean_curves: Dict[str, np.ndarray] = {}
    std_curves: Dict[str, np.ndarray] = {}
    per_streamlines: Dict[str, np.ndarray] = {}
    per100: Dict[str, List[float]] = {}
    for group, txt_path in samples_for_modality.items():
        mat = load_matrix_from_txt(txt_path)
        per_streamlines[group] = mat
        mean_curves[group] = np.mean(mat, axis=0)
        std_curves[group] = np.std(mat, axis=0)
        vals_by_index = []
        for j in range(mat.shape[1]):
            vals = mat[:, j]
            vals_by_index.append(compute_stat(vals, stat))
        per100[group] = [float(x) for x in vals_by_index]
    title = f"{tck_basename} | Along-tract: {mname}"
    out_png = os.path.join(out_dir, f"{tck_basename}_{mname}_linechart.png")
    plot_linechart(mean_curves, std_curves, per_streamlines, title, out_png)
    return mname, out_png, per100


def worker_gm_boxplots_task(args: Tuple[str, str, str, str, Dict[str, Dict[str, np.ndarray]]]) -> Tuple[str, List[str], Dict[str, float]]:
    """Process-safe worker to render GM boxplots for one modality.

    Args tuple: (mname, tck_basename, out_dir, stat, gm_values_for_mname)
      gm_values_for_mname: dict with optional keys 'gm', 'gm_begin', 'gm_end', each mapping to {group->1D array}
    Returns: (mname, box_img_paths, gm_means_dict)
    gm_means_dict keys mirror the caller's expectations (e.g., 'affected_gm', 'unaffected_gm_begin', ...)
    """
    mname, tck_basename, out_dir, stat, gm_values_for_mname = args
    box_imgs: List[str] = []
    gm_means: Dict[str, float] = {}
    # Overall GM first
    if "gm" in gm_values_for_mname and gm_values_for_mname["gm"]:
        title = f"{tck_basename} | {mname} | GM overall ({stat})"
        out_png = os.path.join(out_dir, f"{tck_basename}_{mname}_gm_box.png")
        plot_boxplot(gm_values_for_mname["gm"], title, out_png)
        box_imgs.append(out_png)
        for g, arr in gm_values_for_mname["gm"].items():
            gm_means[f"{g}_gm"] = float(np.mean(arr))
    # GM begin
    if "gm_begin" in gm_values_for_mname and gm_values_for_mname["gm_begin"]:
        title = f"{tck_basename} | {mname} | GM begin ({stat})"
        out_png = os.path.join(out_dir, f"{tck_basename}_{mname}_gm_begin_box.png")
        plot_boxplot(gm_values_for_mname["gm_begin"], title, out_png)
        box_imgs.append(out_png)
        for g, arr in gm_values_for_mname["gm_begin"].items():
            gm_means[f"{g}_gm_begin"] = float(np.mean(arr))
    # GM end
    if "gm_end" in gm_values_for_mname and gm_values_for_mname["gm_end"]:
        title = f"{tck_basename} | {mname} | GM end ({stat})"
        out_png = os.path.join(out_dir, f"{tck_basename}_{mname}_gm_end_box.png")
        plot_boxplot(gm_values_for_mname["gm_end"], title, out_png)
        box_imgs.append(out_png)
        for g, arr in gm_values_for_mname["gm_end"].items():
            gm_means[f"{g}_gm_end"] = float(np.mean(arr))
    return mname, box_imgs, gm_means


# -------------------- Optional header panel rendering helpers -----------------

def _load_nifti(path: str) -> Optional[np.ndarray]:
    if not path or not os.path.exists(path) or nib is None:
        return None
    try:
        img = nib.load(path)
        data = img.get_fdata()
        return np.asarray(data)
    except Exception:
        return None


def _center_of_mass(mask: np.ndarray) -> Tuple[int, int, int]:
    inds = np.argwhere(mask > 0)
    if inds.size == 0:
        # fallback to volume center
        return tuple(int(s // 2) for s in mask.shape)
    if ndi is not None:
        com = ndi.center_of_mass((mask > 0).astype(np.float32))
        return (int(round(com[0])), int(round(com[1])), int(round(com[2])))
    # numpy mean of indices
    com = inds.mean(axis=0)
    return (int(round(com[0])), int(round(com[1])), int(round(com[2])))


def _largest_components(mask: np.ndarray, k: int = 2) -> List[np.ndarray]:
    if mask is None:
        return []
    m = (mask > 0).astype(np.uint8)
    if ndi is None:
        return [m.astype(bool)] if m.sum() > 0 else []
    lbl, n = ndi.label(m)
    if n == 0:
        return []
    comps = []
    for lab in range(1, n + 1):
        comp = (lbl == lab)
        comps.append((comp.sum(), comp))
    comps.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in comps[:k]]


def render_three_axis_panel(template_img: np.ndarray, mask_img: np.ndarray, out_png: str, alpha: float = 0.35, cmap_name: str = "autumn", size: int = 512, title: Optional[str] = None):
    if template_img is None or mask_img is None:
        return
    com = _center_of_mass(mask_img)
    # Extract slices
    try:
        sag = template_img[com[0], :, :]
        cor = template_img[:, com[1], :]
        axi = template_img[:, :, com[2]]
        sag_m = mask_img[com[0], :, :]
        cor_m = mask_img[:, com[1], :]
        axi_m = mask_img[:, :, com[2]]
    except Exception:
        return
    cmap = plt.get_cmap(cmap_name)
    fig, axs = plt.subplots(1, 3, figsize=(size / 100 * 3, size / 100))
    for ax, base, over, name in zip(axs, [sag, cor, axi], [sag_m, cor_m, axi_m], ["Sagittal", "Coronal", "Axial"]):
        ax.imshow(base.T, cmap="gray", origin="lower")
        ax.imshow(over.T, cmap=cmap, alpha=alpha, origin="lower")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(name, fontsize=8)
    if title:
        fig.suptitle(title, fontsize=10)
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close(fig)


def render_streamlines_gradient_panel(tck_path: str, out_png: str, cmap_name: str = "viridis", max_streamlines: int = 400):
    if load_tck is None or not tck_path or not os.path.exists(tck_path):
        return
    try:
        tck = load_tck(tck_path)
        streamlines = list(tck.streamlines)
    except Exception:
        return
    if not streamlines:
        return
    # Sample if too many
    if len(streamlines) > max_streamlines:
        idx = np.random.choice(len(streamlines), size=max_streamlines, replace=False)
        streamlines = [streamlines[i] for i in idx]
    # Determine bounds for equal aspect
    all_pts = np.concatenate(streamlines, axis=0)
    mins = all_pts.min(axis=0)
    maxs = all_pts.max(axis=0)
    ranges = maxs - mins
    max_range = float(max(ranges)) if float(max(ranges)) > 0 else 1.0
    # Plot
    fig = plt.figure(figsize=(6, 4))
    ax = fig.add_subplot(111, projection='3d')
    cmap = plt.get_cmap(cmap_name)
    # Draw each streamline with segments colored by along-tract index
    for sl in streamlines:
        n = sl.shape[0]
        if n < 2:
            continue
        for i in range(n - 1):
            p0 = sl[i]
            p1 = sl[i + 1]
            c = cmap(i / max(1, n - 1))
            ax.plot([p0[0], p1[0]], [p0[1], p1[1]], [p0[2], p1[2]], color=c, linewidth=0.6)
    # Set limits and aspect
    ax.set_xlim(mins[0], mins[0] + max_range)
    ax.set_ylim(mins[1], mins[1] + max_range)
    ax.set_zlim(mins[2], mins[2] + max_range)
    ax.set_axis_off()
    # Colorbar legend for index
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=1, vmax=100))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Along-tract index (1..100)")
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close(fig)


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
    gm_begin: List[Optional[str]]
    gm_end: List[Optional[str]]
    modalities: Dict[str, str]  # name -> path
    out_dir: str
    tmp_dir: Optional[str]
    keep_intermediate: bool
    stat: str
    threads: int
    csv: str
    min_wm_length_mm: float
    include_masks_as_modalities: bool
    # Optional visualization flags
    plot_tract_panels: bool
    panel_size: int
    panel_alpha: float
    panel_colormap: str
    streamline_colormap: str
    streamline_group: Optional[str]
    # Parallel plotting controls
    plot_workers: int
    plot_parallel_backend: str
    log_commands_to_text: Optional[str]
    flow_chart: Optional[str]


def parse_args() -> Inputs:
    p = argparse.ArgumentParser(description="Streamline Lesions Assessment (MRtrix3/ANTs/FSL)")
    p.add_argument("--tck", nargs="+", required=True, help="Input TCK file(s) in template space")
    p.add_argument("--template", required=True, help="HCP100 template NIfTI in template space")
    p.add_argument("--warp", required=True, help="ANTs deformable transform (subject->template)")
    p.add_argument("--affine", required=True, help="ANTs affine transform (subject->template)")
    p.add_argument("--lesion", default=None, help="Subject-space lesion mask NIfTI (optional)")
    p.add_argument("--wm", required=True, help="Subject-space white matter mask NIfTI")
    p.add_argument("--gm", required=True, help="Subject-space gray matter probability map NIfTI (required). It will be warped and thresholded to a GM mask in template space. If --gm_begin/--gm_end are provided, they will be limited (multiplied) by this GM mask after warping.")
    p.add_argument("--gm_begin", "-b", nargs="+", default=None, help="Per-TCK begin GM mask(s) in template space (optional). Provide one entry per --tck, using 'None' or '-' to skip for a TCK. Order must match --tck.")
    p.add_argument("--gm_end", "-e", nargs="+", default=None, help="Per-TCK end GM mask(s) in template space (optional). Provide one entry per --tck, using 'None' or '-' to skip for a TCK. Order must match --tck.")
    p.add_argument("--gm-thr", type=float, default=0.5, help="Threshold for GM probability map after warping (default: 0.5)")
    p.add_argument("--modality", "-m", action="append", default=[], help="Modality image in subject space; optionally name=path. Repeatable.")
    p.add_argument("--out", required=True, help="Output directory")
    p.add_argument("--csv", default=None, help="Path to common CSV (default: <out>/results.csv)")
    p.add_argument("--stat", default="mean", choices=["mean", "median", "min", "max"], help="Statistic for steps 7 & 10-12 (default: mean)")
    p.add_argument("--threads", type=int, default=1, help="Threads to use where applicable")
    p.add_argument("--keep-intermediate", action="store_true", help="Keep intermediate files")
    p.add_argument("--tmp-dir", default=None, help="Optional base temporary directory for intermediate files; if not set, a per-TCK 'intermediate' folder will be created under --out/<tck_basename>.")
    p.add_argument("--min-wm-length-mm", type=float, default=40.0, help="Minimum streamline length in mm for WM-limited tracts (applied after WM masking, before resampling). Set to 0 to disable. Default: 40.0")
    p.add_argument(
        "--include-masks-as-modalities",
        action="store_true",
        help="If set, also include the prepared template-space GM mask, WM mask, and lesion mask (if available) as additional modalities for along-tract sampling and GM stats. Off by default.")
    # Optional header panels and streamline rendering
    p.add_argument("--plot-tract-panels", action="store_true", help="If set, add a header row to the summary image: left/right orthogonal GM panels and center 3D streamline rendering with along-tract color gradient.")
    p.add_argument("--panel-size", type=int, default=512, help="Size (pixels) of each GM side composite panel image (width). Height adapts based on layout. Default: 512")
    p.add_argument("--panel-alpha", type=float, default=0.35, help="Alpha for GM mask overlays on template in side panels (0-1). Default: 0.35")
    p.add_argument("--panel-colormap", default="autumn", help="Matplotlib colormap name for GM mask overlays in side panels (default: 'autumn')")
    p.add_argument("--streamline-colormap", default="viridis", help="Matplotlib colormap name for along-tract gradient coloring of streamlines (default: 'viridis')")
    p.add_argument("--streamline-group", default=None, help="Which group to render in 3D center panel: one of {all, affected, unaffected}. Default: auto (prefer 'all' if present, else 'unaffected', else any available)")
    # Parallel subplot rendering controls
    p.add_argument("--plot-workers", type=int, default=None, help="Number of parallel workers to render per‑TCK subplots (line charts and GM boxplots). Default: min(--threads, 4). Use 1 to disable parallel plotting.")
    p.add_argument("--plot-parallel-backend", choices=["process", "thread"], default="process", help="Backend for parallel subplot rendering. 'process' (default) is safer for Matplotlib; 'thread' uses threads and may work better on constrained systems.")
    p.add_argument("--log_commands_to_text", required=False, help="Path to text file to log commands executed by the pipeline")
    p.add_argument("--flow-chart", required=False, help="Path to output flow chart (e.g. flow.pdf, flow.jpg, flow.svg)")
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

    # Normalize per-TCK begin/end lists
    num_tck = len(args.tck)

    def _normalize_mask_list(lst):
        if lst is None:
            return [None] * num_tck
        norm = []
        for it in lst:
            s = str(it).strip()
            if s.lower() in ("none", "-", "null", ""):
                norm.append(None)
            else:
                norm.append(s)
        if len(norm) != num_tck:
            raise ValueError(f"Expected {num_tck} entries for --gm_begin/--gm_end to match --tck, got {len(norm)}.")
        return norm

    gm_begin_list = _normalize_mask_list(args.gm_begin)
    gm_end_list = _normalize_mask_list(args.gm_end)

    # Determine default plot workers
    def _default_plot_workers(thr: int) -> int:
        try:
            thr = int(thr)
        except Exception:
            thr = 1
        thr = max(1, thr)
        return max(1, min(thr, 4))

    plot_workers = args.plot_workers if args.plot_workers not in (None, "", "None") else _default_plot_workers(args.threads)
    try:
        plot_workers = int(plot_workers)
    except Exception:
        plot_workers = 1
    if plot_workers < 1:
        plot_workers = 1

    return Inputs(
        tcks=args.tck,
        template=args.template,
        warp=args.warp,
        affine=args.affine,
        lesion=args.lesion,
        wm_mask=args.wm,
        gm_mask=args.gm,
        gm_thr=args.gm_thr,
        gm_begin=gm_begin_list,
        gm_end=gm_end_list,
        modalities=modalities,
        out_dir=out_dir,
        keep_intermediate=args.keep_intermediate,
        tmp_dir=args.tmp_dir,
        stat=args.stat,
        threads=args.threads,
        csv=csv_path,
        min_wm_length_mm=float(args.min_wm_length_mm),
        include_masks_as_modalities=bool(args.include_masks_as_modalities),
        plot_tract_panels=bool(args.plot_tract_panels),
        panel_size=int(args.panel_size),
        panel_alpha=float(args.panel_alpha),
        panel_colormap=str(args.panel_colormap),
        streamline_colormap=str(args.streamline_colormap),
        streamline_group=(str(args.streamline_group) if args.streamline_group not in (None, "", "None") else None),
        plot_workers=int(plot_workers),
        plot_parallel_backend=str(args.plot_parallel_backend),
        log_commands_to_text=args.log_commands_to_text,
        flow_chart=args.flow_chart,
    )


def warp_all_subject_to_template(inputs: Inputs, work_dir: str, gm_begin_path: Optional[str] = None, gm_end_path: Optional[str] = None) -> Dict[str, str]:
    """Prepare masks + modalities in template space.
    Returns mapping name->prepared path.
    - WM/lesion are subject-space masks: warped (NN) to template and binarized.
    - GM is a subject-space probability map: warped (BSpline) to template and thresholded to binary via --gm-thr.
    - Begin/end GM (per-TCK, optional) are already in template space: do NOT warp; just limit by the GM mask via fslmaths -mul -bin.
    - Dilated versions (1.25mm) of begin/end GM are also created for streamline filtering.
    """
    log_step("Step 1: Warp masks and modality images to template space (antsApplyTransforms)")
    ref = inputs.template
    out_paths: Dict[str, str] = {}

    # Warp WM mask (required)
    wm_warped = os.path.join(work_dir, "wm_warped_prob.nii.gz")
    ants_apply_transform(inputs.wm_mask, wm_warped, ref, inputs.warp, inputs.affine, is_mask=False)
    wm_warped_bin = os.path.join(work_dir, "wm_warped_bin.nii.gz")
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
    if gm_begin_path:
        ensure_exists(gm_begin_path, "GM begin mask (template space)")
        gmb_limited = os.path.join(work_dir, "gm_begin_limited.nii.gz")
        # Limit begin mask (template space) by the GM mask
        fslmaths_mul_bin(gm_begin_path, gm_warped_bin, gmb_limited)
        out_paths["gm_begin"] = gmb_limited
        # Additionally create dilated version for filtering
        gmb_dilated = os.path.join(work_dir, "gm_begin_dilated_1.25mm.nii.gz")
        fslmaths_dil_bin(gm_begin_path, gmb_dilated, 1.25)
        out_paths["gm_begin_dilated"] = gmb_dilated
    if gm_end_path:
        ensure_exists(gm_end_path, "GM end mask (template space)")
        gme_limited = os.path.join(work_dir, "gm_end_limited.nii.gz")
        fslmaths_mul_bin(gm_end_path, gm_warped_bin, gme_limited)
        out_paths["gm_end"] = gme_limited
        # Additionally create dilated version for filtering
        gme_dilated = os.path.join(work_dir, "gm_end_dilated_1.25mm.nii.gz")
        fslmaths_dil_bin(gm_end_path, gme_dilated, 1.25)
        out_paths["gm_end_dilated"] = gme_dilated

    # Warp modalities (linear interp)
    warped_modalities: Dict[str, str] = {}
    for name, path in inputs.modalities.items():
        if not os.path.exists(path):
            log_info(f"Modality file not found: {path}. Skipping and will fill with NAs.")
            continue
        outp = os.path.join(work_dir, f"{name}_warped.nii.gz")
        ants_apply_transform(path, outp, ref, inputs.warp, inputs.affine, is_mask=False)
        warped_modalities[name] = outp
    out_paths["modalities"] = warped_modalities  # type: ignore

    # Optionally expose masks as additional modalities for sampling/plots
    if inputs.include_masks_as_modalities:
        def _safe_add(name: str, path: str):
            base = name
            suffix = 1
            while name in warped_modalities:
                name = f"{base}_{suffix}"
                suffix += 1
            warped_modalities[name] = path

        # GM mask (binary, template space)
        if "gm" in out_paths and os.path.exists(out_paths["gm"]):
            _safe_add("GMmask", out_paths["gm"])  # type: ignore
        # WM mask (binary, template space)
        if "wm_mask" in out_paths and os.path.exists(out_paths["wm_mask"]):
            _safe_add("WMmask", out_paths["wm_mask"])  # type: ignore
        # Lesion mask if provided
        if "lesion" in out_paths and os.path.exists(out_paths["lesion"]):
            _safe_add("Lesion", out_paths["lesion"])  # type: ignore

    return out_paths


def split_by_lesion_if_needed(in_tck: str, lesion_mask_tpl: Optional[str], work_dir: str) -> Dict[str, str]:
    log_step("Step 2: Split streamlines by lesion mask (if provided)")
    
    groups: Dict[str, str] = {}
    if lesion_mask_tpl and os.path.exists(lesion_mask_tpl) and not fslstats_is_empty(lesion_mask_tpl):
        affected = os.path.join(work_dir, "tracks_affected.tck")
        unaffected = os.path.join(work_dir, "tracks_unaffected.tck")
        tckedit_include(in_tck, lesion_mask_tpl, affected)
        tckedit_exclude(in_tck, lesion_mask_tpl, unaffected)
        groups["affected"] = affected
        groups["unaffected"] = unaffected
        # Always keep the original (unsplit) tract as group 'all'
        groups["all"] = in_tck
    else:
        if lesion_mask_tpl and os.path.exists(lesion_mask_tpl):
            log_info(f"Lesion mask {lesion_mask_tpl} is empty. Skipping split.")
        groups["all"] = in_tck
    return groups


def restrict_to_wm_and_resample(groups: Dict[str, str], wm_mask_tpl: str, work_dir: str, min_len_mm: Optional[float] = None, gm_begin_dilated: Optional[str] = None, gm_end_dilated: Optional[str] = None) -> Dict[str, Tuple[str, str]]:
    log_step("Step 3 & 4: Restrict to white matter, filter by ROIs, and resample to 100 points")
    out: Dict[str, Tuple[str, str]] = {}
    
    # Identify ROIs for filtering
    rois = [r for r in [gm_begin_dilated, gm_end_dilated] if r]

    for label, tck in groups.items():
        # Step 3a: Restrict streamlines to within WM mask.
        # Note: We split this from ROI/length filtering because tckedit -mask 
        # often cannot be combined with -include or -minlength in a single call.
        wm_unfiltered_tck = os.path.join(work_dir, f"{label}_wm_unfiltered.tck")
        tckedit_mask(tck, wm_mask_tpl, wm_unfiltered_tck)

        # Step 3b: Apply ROI filtering and optional min length filter
        final_wm_tck = os.path.join(work_dir, f"{label}_wm.tck")
        
        cmd = [which_or_die("tckedit"), wm_unfiltered_tck, final_wm_tck]
        if rois:
            log_info(f"Adding ROI filtering for {label} to tckedit")
            for r in rois:
                cmd += ["-include", r]
        if min_len_mm is not None and float(min_len_mm) > 0:
            cmd += ["-minlength", f"{float(min_len_mm):.6g}"]
        
        run_cmd(cmd, inputs=[wm_unfiltered_tck] + rois, outputs=[final_wm_tck])
        ensure_exists(final_wm_tck, "final WM-limited TCK")

        # 4: Resample
        res_tck = os.path.join(work_dir, f"{label}_wm_resampled.tck")
        tckresample_num(final_wm_tck, res_tck, num=100)
        out[label] = (final_wm_tck, res_tck)
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


def along_tract_stats_and_plot(samples_txt: Dict[str, Dict[str, str]], tck_basename: str, out_dir: str, stat: str, plot_workers: int = 1, plot_backend: str = "process") -> Tuple[List[str], Dict[str, Dict[str, np.ndarray]]]:
    log_step("Step 6 & 7: Plot line charts and compute per-index statistics across streamlines")
    # Returns list of created linechart paths per modality row order, and per-group per-modality 100-length arrays
    from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed

    linecharts: List[str] = []
    per_group_per_mod_100: Dict[str, Dict[str, np.ndarray]] = {}

    modalities = sorted({m for g in samples_txt.values() for m in g.keys()})
    # Build per-modality inputs
    jobs: List[Tuple[str, str, str, str, Dict[str, str]]] = []
    for mname in modalities:
        samples_for_modality: Dict[str, str] = {}
        for group, md in samples_txt.items():
            if mname in md:
                samples_for_modality[group] = md[mname]
        jobs.append((mname, tck_basename, out_dir, stat, samples_for_modality))

    if plot_workers > 1 and len(jobs) > 1:
        # Choose backend
        Executor = ProcessPoolExecutor if plot_backend == "process" else ThreadPoolExecutor
        try:
            with Executor(max_workers=plot_workers) as ex:
                futs = [ex.submit(worker_linechart_task, args) for args in jobs]
                for fut in as_completed(futs):
                    mname, out_png, per100 = fut.result()
                    linecharts.append(out_png)
                    per_group_per_mod_100[mname] = {g: np.array(v, dtype=float) for g, v in per100.items()}
        except Exception as e:
            log_info(f"Parallel line chart rendering failed ({e}); falling back to serial.")
            for args in jobs:
                m, out_png, per100 = worker_linechart_task(args)
                linecharts.append(out_png)
                per_group_per_mod_100[m] = {g: np.array(v, dtype=float) for g, v in per100.items()}
    else:
        for args in jobs:
            m, out_png, per100 = worker_linechart_task(args)
            linecharts.append(out_png)
            per_group_per_mod_100[m] = {g: np.array(v, dtype=float) for g, v in per100.items()}

    return linecharts, per_group_per_mod_100


def cleanup_files(paths: List[str]):
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except Exception:
            pass


def gm_limited_stats_and_boxplots(groups_raw: Dict[str, str], gm_paths: Dict[str, str], modalities_tpl: Dict[str, str], tck_basename: str, out_dir: str, stat: str, plot_workers: int = 1, plot_backend: str = "process") -> Tuple[Dict[str, Dict[str, float]], Dict[str, List[str]], Dict[str, Dict[str, Optional[float]]], Dict[str, str]]:
    """Create GM-limited TCKs (overall, begin, end as available) from the non-WM-limited
    group tracts (affected/unaffected or all), sample with -stat_tck, and produce boxplots.

    Returns:
      - dict: modality -> {group-> gm_mean_overall, gm_begin, gm_end as available}
      - dict: modality -> list of boxplot image paths in order [begin/overall, end (optional)].
      - dict: gm_counts_by_part: part_key (gm|gm_begin|gm_end) -> {group->count, 'total'->sum}
      - dict: source_ids: keys like 'count_gm_intersect_total', 'stat_gm_intersect_mean' etc. -> tracker ID
    """
    log_step("Step 9-12: GM-limited stats (tckedit -mask) and boxplots")
    from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed

    gm_keys = [k for k in ["gm_begin", "gm", "gm_end"] if k in gm_paths]
    out_gm_stats: Dict[str, Dict[str, float]] = {}
    boxplot_paths_by_mod: Dict[str, List[str]] = {}
    source_ids: Dict[str, str] = {}

    # Prepare per-modality per-group values arrays for boxplots for begin/overall/end
    per_part_values: Dict[str, Dict[str, Dict[str, np.ndarray]]] = {"gm_begin": {}, "gm": {}, "gm_end": {}}
    gm_counts_by_part: Dict[str, Dict[str, Optional[float]]] = {k: {} for k in ["gm_begin", "gm", "gm_end"]}

    # Build TCKs limited to each GM region per group and sample
    temp_files_to_cleanup: List[str] = []
    for part_key in gm_keys:
        mask_img = gm_paths[part_key]
        total_part_count = 0.0
        any_count = False
        total_cnt_id = None
        for group, base_tck in groups_raw.items():
            gm_tck = os.path.join(out_dir, f"{tck_basename}_{group}_{part_key}.tck")
            # IMPORTANT: limit raw (non-WM) group tracts by GM masks
            tckedit_mask(base_tck, mask_img, gm_tck)
            temp_files_to_cleanup.append(gm_tck)
            # Count streamlines in this GM-limited tract
            cnt, cnt_id = tckstats_output(gm_tck, "count")
            gm_counts_by_part.setdefault(part_key, {})[group] = cnt
            # Map count to sid for write_csv_rows_for_tck
            sid_key = f"count_{part_key}_intersect_group_{group}"
            if cnt_id: source_ids[sid_key] = cnt_id

            if cnt is not None:
                # Avoid double counting: 'all' is roughly 'affected' + 'unaffected'
                # If 'all' is present, use it as the total. Otherwise sum the others.
                if "all" in groups_raw:
                    if group == "all":
                        total_part_count = cnt
                        any_count = True
                        total_cnt_id = cnt_id
                else:
                    total_part_count += cnt
                    any_count = True
                    # If multiple groups, use the last cnt_id or None? 
                    # Usually 'total' is a sum, but here we can link it to the last one or nothing.
                    total_cnt_id = cnt_id

            for mname, mpath in modalities_tpl.items():
                txt = os.path.join(out_dir, f"{tck_basename}_{group}_{part_key}_{mname}_stat.txt")
                tcksample_stat(gm_tck, mpath, stat, txt)
                temp_files_to_cleanup.append(txt)
                # Load 1D values per streamline
                vals = load_matrix_from_txt(txt).ravel()
                per_part_values.setdefault(part_key, {}).setdefault(mname, {})[group] = vals
                # Store source_id for the mean stat
                sid_stat_key = f"stat_{part_key}_intersect_mean_{mname}_{group}"
                source_ids[sid_stat_key] = f"file_{txt}"

        # store total
        gm_counts_by_part.setdefault(part_key, {})["total"] = (total_part_count if any_count else None)
        if total_cnt_id:
            source_ids[f"count_{part_key}_intersect_total"] = total_cnt_id

    # Build per-modality GM values bundle for workers
    gm_values_by_mod: Dict[str, Dict[str, Dict[str, np.ndarray]]] = {}
    for mname in modalities_tpl.keys():
        gm_values_by_mod[mname] = {
            k: (per_part_values.get(k, {}).get(mname, {})) for k in ["gm", "gm_begin", "gm_end"]
        }

    # Dispatch boxplot rendering per modality
    jobs: List[Tuple[str, str, str, str, Dict[str, Dict[str, np.ndarray]]]] = []
    for mname in modalities_tpl.keys():
        jobs.append((mname, tck_basename, out_dir, stat, gm_values_by_mod[mname]))

    if plot_workers > 1 and len(jobs) > 1:
        Executor = ProcessPoolExecutor if plot_backend == "process" else ThreadPoolExecutor
        try:
            with Executor(max_workers=plot_workers) as ex:
                futs = [ex.submit(worker_gm_boxplots_task, args) for args in jobs]
                for fut in as_completed(futs):
                    mname, box_imgs, gm_means = fut.result()
                    boxplot_paths_by_mod[mname] = box_imgs
                    out_gm_stats[mname] = gm_means
        except Exception as e:
            log_info(f"Parallel GM boxplot rendering failed ({e}); falling back to serial.")
            for args in jobs:
                mname, box_imgs, gm_means = worker_gm_boxplots_task(args)
                boxplot_paths_by_mod[mname] = box_imgs
                out_gm_stats[mname] = gm_means
    else:
        for args in jobs:
            mname, box_imgs, gm_means = worker_gm_boxplots_task(args)
            boxplot_paths_by_mod[mname] = box_imgs
            out_gm_stats[mname] = gm_means

    # Step 13: cleanup of intermediate GM files
    if temp_files_to_cleanup:
        log_step("Step 13: Cleanup GM-limited intermediate files")
        # Keep or remove based on flag handled by caller
    return out_gm_stats, boxplot_paths_by_mod, gm_counts_by_part, source_ids


def write_csv_rows_for_tck(
    csv_path: str,
    tck_path: str,
    stat: str,
    per_group_per_mod_100: Dict[str, Dict[str, np.ndarray]],
    gm_stats: Dict[str, Dict[str, float]],
    wm_len_filtered_counts: Dict[str, Optional[float]] = None,
    group_mean_len: Dict[str, Optional[float]] = None,
    group_all_stats: Dict[str, Dict[str, Optional[float]]] = None,
    group_wm_stats: Dict[str, Dict[str, Optional[float]]] = None,
    roi_means: Dict[str, Dict[str, Optional[float]]] = None,
    full_counts: Dict[str, Optional[float]] = None,
    wm_masked_counts: Dict[str, Optional[float]] = None,
    gm_counts_by_part: Dict[str, Dict[str, Optional[float]]] = None,
    roi_filtered_counts: Dict[str, Optional[float]] = None,
    source_ids: Dict[str, str] = None,
    groups_wm_res: Dict[str, Tuple[str, str]] = None,
    modalities_tpl: Dict[str, str] = None,
    all_modality_names: List[str] = None
):
    # Construct header: tck, modality, group, stat, counts/percent/meanlen, along-tract idx_1..idx_100,
    # plus overall/group/WM stats, ROI means, and GM-limited stats. Also explicit streamline counts.
    idx_cols = [f"idx_{i}" for i in range(1, 101)]
    header = [
        "tck",
        "modality",
        "group",
        "stat",
        "mean_length",
        "count_original_total",
        "count_unfiltered_lesion_split_group",
        "count_wm_masked_minlength_filtered_total",
        "count_roi_filtered_total",
        "count_roi_filtered_group",
        "count_gm_intersect_total",
        "count_gm_intersect_group",
        "count_gm_begin_intersect_total",
        "count_gm_begin_intersect_group",
        "count_gm_end_intersect_total",
        "count_gm_end_intersect_group",
        "count_wm_masked_group",
        "count_wm_masked_minlength_filtered_group",
        # Group stats (non-WM)
        "stat_full_tract_" + stat,
        # WM-limited group stats
        "stat_wm_limited_" + stat,
        # ROI means in GM/WM masks
        "roi_GMmask_mean",
        "roi_WMmask_mean",
    ] + idx_cols + ["stat_gm_intersect_mean", "stat_gm_begin_intersect_mean", "stat_gm_end_intersect_mean"]

    # Add columns to tracker (no results.csv node)
    if source_ids:
        # Static links
        if "full_counts_original" in source_ids:
            TRACKER.add_csv_variable("count_original_total", source_node=source_ids["full_counts_original"], label="tckstats (count)")
        if "wm_len_filtered_counts_all" in source_ids:
            TRACKER.add_csv_variable("count_wm_masked_minlength_filtered_total", source_node=source_ids["wm_len_filtered_counts_all"], label="tckstats (count)")
        if "roi_filtered_counts_total" in source_ids:
            TRACKER.add_csv_variable("count_roi_filtered_total", source_node=source_ids["roi_filtered_counts_total"], label="tckstats (count)")
        if "count_gm_intersect_total" in source_ids:
            TRACKER.add_csv_variable("count_gm_intersect_total", source_node=source_ids["count_gm_intersect_total"], label="tckstats (count)")
        if "count_gm_begin_intersect_total" in source_ids:
            TRACKER.add_csv_variable("count_gm_begin_intersect_total", source_node=source_ids["count_gm_begin_intersect_total"], label="tckstats (count)")
        if "count_gm_end_intersect_total" in source_ids:
            TRACKER.add_csv_variable("count_gm_end_intersect_total", source_node=source_ids["count_gm_end_intersect_total"], label="tckstats (count)")

    tck_base = os.path.basename(tck_path)

    # Discover set of groups present (e.g., affected/unaffected or all)
    groups = set()
    for _mname, per_group in per_group_per_mod_100.items():
        for g in per_group.keys():
            groups.add(g)
    if not groups and groups_wm_res:
        groups = set(groups_wm_res.keys())

    # Modality names to iterate over
    mod_names = all_modality_names if all_modality_names else sorted(per_group_per_mod_100.keys())

    # For percent, base it on the WM length-filtered counts if available
    total_count = None
    if wm_len_filtered_counts:
        # Denominator excludes the 'all' group; percentages are only meaningful for lesion-based groups
        vals = [c for k, c in wm_len_filtered_counts.items() if k != "all" and c is not None]
        if vals:
            total_count = float(sum(vals))

    for mname in mod_names:
        per_group = per_group_per_mod_100.get(mname, {})
        mimg = modalities_tpl.get(mname) if modalities_tpl else None
        
        # If no data for this modality (missing file), we still want to output NAs for all groups
        current_groups = sorted(list(groups))
        if not current_groups:
             current_groups = ["all"] # fallback

        for g in current_groups:
            arr100 = per_group.get(g)
            is_modality_missing = (arr100 is None)

            if is_modality_missing:
                # Fill with empty strings if data missing
                arr100_str = [""] * 100
            else:
                arr100_str = [f"{v:.6g}" if not isinstance(v, str) else v for v in arr100]

            # Add group/modality specific links to tracker
            if source_ids and not is_modality_missing:
                if f"group_mean_len_{g}" in source_ids:
                    TRACKER.add_csv_variable("mean_length", source_node=source_ids[f"group_mean_len_{g}"], label="tckstats (mean)")
                if f"full_counts_{g}" in source_ids:
                    TRACKER.add_csv_variable("count_unfiltered_lesion_split_group", source_node=source_ids[f"full_counts_{g}"], label="tckstats (count)")
                if f"wm_len_filtered_counts_{g}" in source_ids:
                    TRACKER.add_csv_variable("count_roi_filtered_group", source_node=source_ids[f"wm_len_filtered_counts_{g}"], label="tckstats (count)")
                    TRACKER.add_csv_variable("count_wm_masked_minlength_filtered_group", source_node=source_ids[f"wm_len_filtered_counts_{g}"], label="tckstats (count)")
                if f"count_gm_intersect_group_{g}" in source_ids:
                    TRACKER.add_csv_variable("count_gm_intersect_group", source_node=source_ids[f"count_gm_intersect_group_{g}"], label="tckstats (count)")
                if f"count_gm_begin_intersect_group_{g}" in source_ids:
                    TRACKER.add_csv_variable("count_gm_begin_intersect_group", source_node=source_ids[f"count_gm_begin_intersect_group_{g}"], label="tckstats (count)")
                if f"count_gm_end_intersect_group_{g}" in source_ids:
                    TRACKER.add_csv_variable("count_gm_end_intersect_group", source_node=source_ids[f"count_gm_end_intersect_group_{g}"], label="tckstats (count)")
                if f"wm_masked_counts_{g}" in source_ids:
                    TRACKER.add_csv_variable("count_wm_masked_group", source_node=source_ids[f"wm_masked_counts_{g}"], label="tckstats (count)")
                
                # Stats
                if f"group_all_stats_{mname}_{g}" in source_ids:
                    TRACKER.add_csv_variable("stat_full_tract_" + stat, source_node=source_ids[f"group_all_stats_{mname}_{g}"], label="tcksample (mean)")
                if f"group_wm_stats_{mname}_{g}" in source_ids:
                    TRACKER.add_csv_variable("stat_wm_limited_" + stat, source_node=source_ids[f"group_wm_stats_{mname}_{g}"], label="tcksample (mean)")
                
                # GM Stats
                if f"stat_gm_intersect_mean_{mname}_{g}" in source_ids:
                    TRACKER.add_csv_variable("stat_gm_intersect_mean", source_node=source_ids[f"stat_gm_intersect_mean_{mname}_{g}"], label="mean")
                if f"stat_gm_begin_intersect_mean_{mname}_{g}" in source_ids:
                    TRACKER.add_csv_variable("stat_gm_begin_intersect_mean", source_node=source_ids[f"stat_gm_begin_intersect_mean_{mname}_{g}"], label="mean")
                if f"stat_gm_end_intersect_mean_{mname}_{g}" in source_ids:
                    TRACKER.add_csv_variable("stat_gm_end_intersect_mean", source_node=source_ids[f"stat_gm_end_intersect_mean_{mname}_{g}"], label="mean")

                # ROI means
                if f"roi_means_{mname}_GMmask" in source_ids:
                    TRACKER.add_csv_variable("roi_GMmask_mean", source_node=source_ids[f"roi_means_{mname}_GMmask"], label="fslstats (mean)")
                if f"roi_means_{mname}_WMmask" in source_ids:
                    TRACKER.add_csv_variable("roi_WMmask_mean", source_node=source_ids[f"roi_means_{mname}_WMmask"], label="fslstats (mean)")

                # Along-tract
                if groups_wm_res and g in groups_wm_res:
                    res_tck = groups_wm_res[g][1]
                    if res_tck:
                        TRACKER.add_csv_variable("idx_1", source_node=f"file_{res_tck}", label="tcksample")
                        TRACKER.add_csv_variable("idx_50", source_node=f"file_{res_tck}", label="tcksample")
                        TRACKER.add_csv_variable("idx_100", source_node=f"file_{res_tck}", label="tcksample")

            # Counts by category
            if is_modality_missing:
                n_len_filt = None
                n_wm_masked = None
                n_full_group = None
                n_full_total = None
                n_original_total = None
                n_roi_filt_group = None
                n_roi_filt_total = None
                gm_total = None
                gm_group = None
                gmb_total = None
                gmb_group = None
                gme_total = None
                gme_group = None
                meanlen = None
                gm = None
                gmb = None
                gme = None
                g_all_val = None
                g_wm_val = None
                roi_gm = None
                roi_wm = None
            else:
                n_len_filt = wm_len_filtered_counts.get(g) if wm_len_filtered_counts else None
                n_wm_masked = wm_masked_counts.get(g) if wm_masked_counts else None
                n_full_group = full_counts.get(g) if full_counts else None
                n_full_total = full_counts.get("total") if full_counts else None
                n_original_total = full_counts.get("original") if full_counts else None
                
                n_roi_filt_group = roi_filtered_counts.get(g) if roi_filtered_counts else None
                n_roi_filt_total = roi_filtered_counts.get("total") if roi_filtered_counts else None

                gm_total = gm_counts_by_part.get("gm", {}).get("total") if gm_counts_by_part else None
                gm_group = gm_counts_by_part.get("gm", {}).get(g) if gm_counts_by_part else None
                gmb_total = gm_counts_by_part.get("gm_begin", {}).get("total") if gm_counts_by_part else None
                gmb_group = gm_counts_by_part.get("gm_begin", {}).get(g) if gm_counts_by_part else None
                gme_total = gm_counts_by_part.get("gm_end", {}).get("total") if gm_counts_by_part else None
                gme_group = gm_counts_by_part.get("gm_end", {}).get(g) if gm_counts_by_part else None

                meanlen = group_mean_len.get(g) if group_mean_len else None

                gm = gm_stats.get(mname, {}).get(f"{g}_gm")
                gmb = gm_stats.get(mname, {}).get(f"{g}_gm_begin")
                gme = gm_stats.get(mname, {}).get(f"{g}_gm_end")

                # Additional stats (non-count)
                g_all_val = None
                if group_all_stats and mname in group_all_stats and g in group_all_stats[mname]:
                    g_all_val = group_all_stats[mname].get(g)
                g_wm_val = None
                if group_wm_stats and mname in group_wm_stats and g in group_wm_stats[mname]:
                    g_wm_val = group_wm_stats[mname].get(g)
                roi_gm = roi_means.get(mname, {}).get("GMmask") if roi_means else None
                roi_wm = roi_means.get(mname, {}).get("WMmask") if roi_means else None

            values = [
                tck_base,
                mname,
                g,
                stat,
                (f"{meanlen:.6g}" if meanlen is not None else ""),
                (f"{n_original_total:.6g}" if n_original_total is not None else ""),
                (f"{n_full_group:.6g}" if n_full_group is not None else ""),
                (f"{n_full_total:.6g}" if n_full_total is not None else ""),
                (f"{n_roi_filt_total:.6g}" if n_roi_filt_total is not None else ""),
                (f"{n_roi_filt_group:.6g}" if n_roi_filt_group is not None else ""),
                (f"{gm_total:.6g}" if gm_total is not None else ""),
                (f"{gm_group:.6g}" if gm_group is not None else ""),
                (f"{gmb_total:.6g}" if gmb_total is not None else ""),
                (f"{gmb_group:.6g}" if gmb_group is not None else ""),
                (f"{gme_total:.6g}" if gme_total is not None else ""),
                (f"{gme_group:.6g}" if gme_group is not None else ""),
                (f"{n_wm_masked:.6g}" if n_wm_masked is not None else ""),
                (f"{n_len_filt:.6g}" if n_len_filt is not None else ""),
                # per-group (non-WM) written in column; blank for non-applicable
                (f"{g_all_val:.6g}" if g_all_val is not None else ""),
                # WM-limited per-group values
                (f"{g_wm_val:.6g}" if g_wm_val is not None else ""),
                # ROI means
                (f"{roi_gm:.6g}" if roi_gm is not None else ""),
                (f"{roi_wm:.6g}" if roi_wm is not None else ""),
            ] + arr100_str + [
                (f"{gm:.6g}" if gm is not None else ""),
                (f"{gmb:.6g}" if gmb is not None else ""),
                (f"{gme:.6g}" if gme is not None else ""),
            ]
            save_csv_row(csv_path, header, values)


def stitch_final_figure(tck_path: str, modalities: List[str], linecharts_by_mod: Dict[str, str], boxplots_by_mod: Dict[str, List[str]], out_dir: str, header_row: Optional[List[str]] = None) -> str:
    log_step("Step 14: Stitch figures into final JPEG")
    tck_base = os.path.splitext(os.path.basename(tck_path))[0]
    rows: List[List[str]] = []
    # Optional header row at the very top
    if header_row:
        header = [p for p in header_row if p and os.path.exists(p)]
        if header:
            rows.append(header)
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

    # Set global command log file if provided
    global LOG_COMMANDS_TO_TEXT
    LOG_COMMANDS_TO_TEXT = inputs.log_commands_to_text

    if inputs.flow_chart:
        TRACKER.enabled = True

    # Basic tool availability checks
    for b in ["antsApplyTransforms", "tckedit", "tckresample", "tcksample", "tckstats", "fslmaths", "fslstats"]:
        which_or_die(b)

    # Global output dirs
    make_dirs(inputs.out_dir)
    common_csv = inputs.csv
    log_info(f"Common CSV: {common_csv}")

    for i, tck_path in enumerate(inputs.tcks):
        ensure_exists(tck_path, "TCK file")
        tck_base = os.path.splitext(os.path.basename(tck_path))[0]
        tck_out_dir = os.path.join(inputs.out_dir, tck_base)
        # Pick intermediate directory: user-provided base tmp dir or inside output per TCK
        if inputs.tmp_dir:
            inter_dir = os.path.join(inputs.tmp_dir, tck_base)
        else:
            inter_dir = os.path.join(tck_out_dir, "intermediate")
        make_dirs(tck_out_dir)
        make_dirs(inter_dir)

        # Resolve per-TCK GM begin/end masks
        gm_begin_path = inputs.gm_begin[i] if inputs.gm_begin and i < len(inputs.gm_begin) else None
        gm_end_path = inputs.gm_end[i] if inputs.gm_end and i < len(inputs.gm_end) else None

        # Step 1: warp/prepare (per-TCK begin/end are template-space; only limited by GM)
        warped = warp_all_subject_to_template(inputs, inter_dir, gm_begin_path=gm_begin_path, gm_end_path=gm_end_path)
        wm_tpl = warped["wm_mask"]
        lesion_tpl = warped.get("lesion")
        gm_paths = {k: v for k, v in warped.items() if k in ("gm", "gm_begin", "gm_end")}
        modalities_tpl = warped["modalities"]  # type: ignore

        # Step 2: lesion split
        # Groups is a tuple which contains the name of the tract (i.e. all/affacted/unaffected) and a path to the .tck file
        groups = split_by_lesion_if_needed(
            tck_path,
            lesion_tpl,
            inter_dir
        )

        # Step 3 & 4: apply WM mask, ROI filter, and optional min length filter, then resample
        groups_wm_res = restrict_to_wm_and_resample(
            groups,
            wm_tpl,
            inter_dir,
            min_len_mm=inputs.min_wm_length_mm,
            gm_begin_dilated=warped.get("gm_begin_dilated"),
            gm_end_dilated=warped.get("gm_end_dilated")
        )

        # Master source ID tracker for linking CSV variables in flow chart
        master_source_ids: Dict[str, str] = {}

        # Step 5
        samples_txt = sample_modalities_along_tracts(groups_wm_res, modalities_tpl, inter_dir)

        # Compute streamline counts and mean lengths for multiple tract definitions
        # A) WM-limited AFTER length restriction AND ROI filtering
        wm_len_filtered_counts: Dict[str, Optional[float]] = {}
        group_mean_len: Dict[str, Optional[float]] = {}
        for label, (wm_tck, _res_tck) in groups_wm_res.items():
            cnt, cnt_id = tckstats_output(wm_tck, "count")
            mlen, mlen_id = tckstats_output(wm_tck, "mean")
            wm_len_filtered_counts[label] = cnt
            group_mean_len[label] = mlen
            if cnt_id: master_source_ids[f"wm_len_filtered_counts_{label}"] = cnt_id
            if mlen_id: master_source_ids[f"group_mean_len_{label}"] = mlen_id

        # B) ROI-filtered counts (if applicable)
        roi_filtered_counts: Dict[str, Optional[float]] = {}
        # We now check per group since filtering happened per group in Step 3
        has_roi_filtering = any([warped.get("gm_begin_dilated"), warped.get("gm_end_dilated")])
        if has_roi_filtering:
            # Since ROI filtering happened after WM masking, we report the counts of the tracts
            # that passed both WM masking and ROI filtering.
            roi_filtered_counts["total"] = wm_len_filtered_counts.get("all")
            master_source_ids["roi_filtered_counts_total"] = master_source_ids.get("wm_len_filtered_counts_all")
            for glabel in groups.keys():
                roi_filtered_counts[glabel] = wm_len_filtered_counts.get(glabel)
                master_source_ids[f"roi_filtered_counts_{glabel}"] = master_source_ids.get(f"wm_len_filtered_counts_{glabel}")
        else:
            roi_filtered_counts["total"] = None

        # C) FULL tract counts (non-WM), per group and total
        full_counts: Dict[str, Optional[float]] = {}
        # original total from input TCK
        val, sid = tckstats_output(tck_path, "count")
        full_counts["original"] = val
        if sid: master_source_ids["full_counts_original"] = sid
        
        # per-group full counts
        for glabel, gtck in groups.items():
            val, sid = tckstats_output(gtck, "count")
            full_counts[glabel] = val
            if sid: master_source_ids[f"full_counts_{glabel}"] = sid
        
        full_counts["total"] = wm_len_filtered_counts.get("all")
        master_source_ids["full_counts_total"] = master_source_ids.get("wm_len_filtered_counts_all")

        # D) WM-masked counts WITHOUT length restriction (temporary TCKs)
        wm_masked_counts: Dict[str, Optional[float]] = {}
        tmp_wm_masked_files: List[str] = []
        for glabel, gtck in groups.items():
            tmp_wm = os.path.join(inter_dir, f"{glabel}_wm_noLen.tck")
            tckedit_mask(gtck, wm_tpl, tmp_wm)
            val, sid = tckstats_output(tmp_wm, "count")
            wm_masked_counts[glabel] = val
            if sid: master_source_ids[f"wm_masked_counts_{glabel}"] = sid
            tmp_wm_masked_files.append(tmp_wm)

        # Step 6 & 7 (store linecharts in intermediate folder)
        linecharts, per_group_per_mod_100 = along_tract_stats_and_plot(samples_txt, tck_base, inter_dir, inputs.stat, plot_workers=inputs.plot_workers, plot_backend=inputs.plot_parallel_backend)

        # Additional statistics for CSV: group (non-WM) and WM-limited per modality (no overall/merged tract)
        # Prepare containers
        group_all_stats: Dict[str, Dict[str, Optional[float]]] = {}
        group_wm_stats: Dict[str, Dict[str, Optional[float]]] = {}
        roi_means: Dict[str, Dict[str, Optional[float]]] = {}

        # Compute ROI means (same per modality across groups) using template-space masks
        gm_mask_tpl = None
        wm_mask_tpl = None
        if "gm" in gm_paths:
            gm_mask_tpl = gm_paths["gm"]
        if wm_tpl:
            wm_mask_tpl = wm_tpl

        for mname, mimg in modalities_tpl.items():
            # Group non-WM stats
            group_all_stats[mname] = {}
            for glabel, gtck in groups.items():
                out_txt = os.path.join(inter_dir, f"{glabel}_all_{mname}_{inputs.stat}.txt")
                val, sid = tcksample_stat_mean(gtck, mimg, inputs.stat, out_txt)
                group_all_stats[mname][glabel] = val
                if sid: master_source_ids[f"group_all_stats_{mname}_{glabel}"] = sid

            # Group WM-limited stats
            group_wm_stats[mname] = {}
            for glabel, (wm_tck, _res) in groups_wm_res.items():
                out_txt = os.path.join(inter_dir, f"{glabel}_wm_{mname}_{inputs.stat}.txt")
                val, sid = tcksample_stat_mean(wm_tck, mimg, inputs.stat, out_txt)
                group_wm_stats[mname][glabel] = val
                if sid: master_source_ids[f"group_wm_stats_{mname}_{glabel}"] = sid

            # ROI means
            roi_means[mname] = {}
            if gm_mask_tpl and os.path.exists(gm_mask_tpl):
                val, sid = fslstats_masked_mean(mimg, gm_mask_tpl)
                roi_means[mname]["GMmask"] = val
                if sid: master_source_ids[f"roi_means_{mname}_GMmask"] = sid
            else:
                roi_means[mname]["GMmask"] = None
            if wm_mask_tpl and os.path.exists(wm_mask_tpl):
                val, sid = fslstats_masked_mean(mimg, wm_mask_tpl)
                roi_means[mname]["WMmask"] = val
                if sid: master_source_ids[f"roi_means_{mname}_WMmask"] = sid
            else:
                roi_means[mname]["WMmask"] = None

        # Step 8: cleanup resampled, wm-limited, and Nx100 text files if not keeping
        if not inputs.keep_intermediate:
            log_step("Step 8: Cleanup WM-limited/resampled TCKs and along-tract samples")
            cleanup = []
            for label, (wm_tck, res_tck) in groups_wm_res.items():
                cleanup.extend([wm_tck, res_tck])
                # Also cleanup the intermediate wm_only tck
                wm_only = os.path.join(inter_dir, f"{label}_wm_only.tck")
                cleanup.append(wm_only)
            for g, md in samples_txt.items():
                for _m, txt in md.items():
                    cleanup.append(txt)
            # Additional stat files
            try:
                for mname in modalities_tpl.keys():
                    # per group
                    for glabel in groups.keys():
                        cleanup.append(os.path.join(inter_dir, f"{glabel}_all_{mname}_{inputs.stat}.txt"))
                        cleanup.append(os.path.join(inter_dir, f"{glabel}_wm_{mname}_{inputs.stat}.txt"))
            except Exception:
                pass
            # Temporary WM-masked (no length) TCKs
            try:
                for p in tmp_wm_masked_files:
                    cleanup.append(p)
            except Exception:
                pass
            cleanup_files(cleanup)

        # Step 9-12: GM-limited stats and boxplots (store boxplots in intermediate folder)
        gm_stats: Dict[str, Dict[str, float]] = {}
        boxplots_by_mod: Dict[str, List[str]] = {}
        gm_counts_by_part: Dict[str, Dict[str, Optional[float]]] = {}
        if gm_paths:
            # IMPORTANT: GM-limited stats should be derived from non-WM-limited group tracts
            res = gm_limited_stats_and_boxplots(groups, gm_paths, modalities_tpl, tck_base, inter_dir, inputs.stat, plot_workers=inputs.plot_workers, plot_backend=inputs.plot_parallel_backend)
            gm_stats, boxplots_by_mod, gm_counts_by_part, gm_source_ids = res
            master_source_ids.update(gm_source_ids)
            # Step 13 cleanup of GM-limited artifacts
            if not inputs.keep_intermediate:
                log_step("Step 13: Cleanup GM-limited TCKs and text files")
                # No-op here; final cleanup will remove the entire intermediate directory
                to_del = []
                cleanup_files(to_del)

        # Determine all modality names from inputs (including missing ones)
        all_modality_names = sorted(inputs.modalities.keys())
        if inputs.include_masks_as_modalities:
            # Re-generate the names that would have been added
            if "gm" in warped: all_modality_names.append("GMmask")
            if "wm_mask" in warped: all_modality_names.append("WMmask")
            if "lesion" in warped: all_modality_names.append("Lesion")
            all_modality_names = sorted(list(set(all_modality_names)))

        # Write CSV rows per modality/group including counts, lengths, and new statistics
        write_csv_rows_for_tck(
            common_csv,
            tck_path,
            inputs.stat,
            per_group_per_mod_100,
            gm_stats,
            wm_len_filtered_counts=wm_len_filtered_counts,
            group_mean_len=group_mean_len,
            group_all_stats=group_all_stats,
            group_wm_stats=group_wm_stats,
            roi_means=roi_means,
            full_counts=full_counts,
            wm_masked_counts=wm_masked_counts,
            gm_counts_by_part=gm_counts_by_part,
            roi_filtered_counts=roi_filtered_counts,
            source_ids=master_source_ids,
            groups_wm_res=groups_wm_res,
            modalities_tpl=modalities_tpl,
            all_modality_names=all_modality_names
        )

        # Step 14: stitch final figure per TCK
        linecharts_by_mod = {}
        for p in linecharts:
            # map back by modality name from filename
            bn = os.path.basename(p)
            # expects format: <tckbase>_<modname>_linechart.png
            modname = bn.replace(f"{tck_base}_", "").replace("_linechart.png", "")
            linecharts_by_mod[modname] = p
        # Optional header panels and streamline rendering
        header_row: List[str] = []
        if inputs.plot_tract_panels and nib is not None:
            try:
                template_arr = _load_nifti(inputs.template)
                gm_arr = _load_nifti(gm_paths.get("gm")) if gm_paths else None
                left_mask = None
                right_mask = None
                left_title = None
                right_title = None
                if gm_paths and "gm_begin" in gm_paths:
                    left_mask = _load_nifti(gm_paths["gm_begin"])
                    left_title = "GM begin"
                if gm_paths and "gm_end" in gm_paths:
                    right_mask = _load_nifti(gm_paths["gm_end"])
                    right_title = "GM end"
                # If missing begin/end, use up to two largest components from overall GM
                if (left_mask is None or right_mask is None) and gm_arr is not None:
                    comps = _largest_components(gm_arr, k=2)
                    if left_mask is None and len(comps) >= 1:
                        left_mask = comps[0]
                        left_title = "GM component #1"
                    if right_mask is None and len(comps) >= 2:
                        right_mask = comps[1]
                        right_title = "GM component #2"
                # Render side panels if possible
                left_png = os.path.join(inter_dir, f"{tck_base}_panel_left.png")
                right_png = os.path.join(inter_dir, f"{tck_base}_panel_right.png")
                if template_arr is not None and left_mask is not None:
                    render_three_axis_panel(template_arr, left_mask, left_png, alpha=inputs.panel_alpha, cmap_name=inputs.panel_colormap, size=inputs.panel_size, title=left_title)
                    if os.path.exists(left_png):
                        header_row.append(left_png)
                # Center streamlines panel: choose group
                center_png = os.path.join(inter_dir, f"{tck_base}_streamlines.png")
                group_choice = inputs.streamline_group
                if not group_choice:
                    if "all" in groups_wm_res:
                        group_choice = "all"
                    elif "unaffected" in groups_wm_res:
                        group_choice = "unaffected"
                    else:
                        group_choice = next(iter(groups_wm_res.keys())) if groups_wm_res else None
                if group_choice and group_choice in groups_wm_res:
                    _wm_tck_path, resampled_tck_path = groups_wm_res[group_choice]
                    render_streamlines_gradient_panel(resampled_tck_path, center_png, cmap_name=inputs.streamline_colormap)
                    if os.path.exists(center_png):
                        header_row.append(center_png)
                # Right panel
                if template_arr is not None and right_mask is not None:
                    render_three_axis_panel(template_arr, right_mask, right_png, alpha=inputs.panel_alpha, cmap_name=inputs.panel_colormap, size=inputs.panel_size, title=right_title)
                    if os.path.exists(right_png):
                        header_row.append(right_png)
            except Exception as e:
                log_info(f"Header panel rendering skipped due to error: {e}")
        final_jpg = stitch_final_figure(tck_path, all_modality_names, linecharts_by_mod, boxplots_by_mod, tck_out_dir, header_row=(header_row if header_row else None))
        log_info(f"Final figure: {final_jpg}")

        # Final cleanup of intermediate directory unless user requested to keep it
        if not inputs.keep_intermediate:
            log_step("Final cleanup: remove intermediate directory")
            try:
                shutil.rmtree(inter_dir, ignore_errors=True)
            except Exception:
                pass

    log_info("All done.")

    if inputs.flow_chart:
        TRACKER.export(inputs.flow_chart)


if __name__ == "__main__":
    main()

