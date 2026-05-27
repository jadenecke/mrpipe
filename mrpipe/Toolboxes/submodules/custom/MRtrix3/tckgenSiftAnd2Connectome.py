#!/usr/bin/env python3
import argparse
import atexit
import os
import subprocess
import sys
import tempfile

def run(cmd):
    print(">>>", " ".join(cmd))
    subprocess.run(cmd, check=True)

def check_file(path, label):
    if not os.path.isfile(path):
        print(f"ERROR: {label} does not exist: {path}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="tckgen → sift2 → connectome pipeline with weighting maps and mean length"
    )

    parser.add_argument("wmfodNorm")
    parser.add_argument("T1_5TTReg")
    parser.add_argument("nstreamlines")
    parser.add_argument("outputbase")
    parser.add_argument("scratch")

    parser.add_argument("--threads", type=int, default=None)
    parser.add_argument("--force", action="store_true")

    parser.add_argument("--atlasNameList", nargs="+", required=True)
    parser.add_argument("--atlasFileList", nargs="+", required=True)
    parser.add_argument("--weightMapList", nargs="+", required=False, default=None)

    args = parser.parse_args()

    # --- Sanity checks ---
    if len(args.atlasNameList) != len(args.atlasFileList):
        print("ERROR: atlasNameList and atlasFileList must have same length")
        sys.exit(1)

    if args.weightMapList is not None:
        if len(args.weightMapList) != len(args.atlasNameList):
            print("ERROR: weightMapList must match atlas list length")
            sys.exit(1)

    # Check scratch
    scratch = os.path.abspath(args.scratch)
    if not os.path.isdir(scratch):
        print(f"ERROR: Scratch directory does not exist: {scratch}")
        sys.exit(1)

    # Check files
    check_file(args.wmfodNorm, "wmfodNorm")
    check_file(args.T1_5TTReg, "T1_5TTReg")

    for name, f in zip(args.atlasNameList, args.atlasFileList):
        check_file(f, f"Atlas file for {name}")

    if args.weightMapList:
        for w in args.weightMapList:
            check_file(w, "Weight map")

    # Check atlas names
    if len(set(args.atlasNameList)) != len(args.atlasNameList):
        print("ERROR: Duplicate atlas names detected")
        sys.exit(1)

    # --- Create temp working directory ---
    work_dir = tempfile.mkdtemp(prefix="tckgenSift2connectome_", dir=scratch)
    print(f"Using temporary working directory: {work_dir}")

    def cleanup():
        if os.path.isdir(work_dir):
            print(f"Deleting temp working directory {work_dir}")
            subprocess.run(["rm", "-rf", work_dir])
    atexit.register(cleanup)

    # --- Build flags ---
    threads_flag = ["-nthreads", str(args.threads)] if args.threads else []
    force_flag = ["-force"] if args.force else []

    wmfodNorm = os.path.abspath(args.wmfodNorm)
    T1_5TTReg = os.path.abspath(args.T1_5TTReg)
    outputbase = args.outputbase

    tck_file = os.path.join(work_dir, "tcks.tck")
    sift_weights = os.path.join(work_dir, "tcks_siftWeights.txt")

    # --- tckgen ---
    run([
        "tckgen",
        "-algorithm", "iFOD2",
        "-act", T1_5TTReg,
        "-select", args.nstreamlines,
        "-seed_dynamic", wmfodNorm,
        *threads_flag,
        *force_flag,
        wmfodNorm,
        tck_file
    ])

    # --- SIFT2 ---
    run([
        "tcksift2",
        "-act", T1_5TTReg,
        tck_file,
        wmfodNorm,
        sift_weights
    ])

    # --- Mean streamline length ---
    mean_length_file = f"{outputbase}mean_length.txt"
    run([
        "tckstats",
        "-output", "mean",
        tck_file
    ])

    # Capture mean length
    result = subprocess.run(
        ["tckstats", "-output", "mean", tck_file],
        check=True,
        capture_output=True,
        text=True
    )
    with open(mean_length_file, "w") as f:
        f.write(result.stdout.strip() + "\n")

    print(f"Mean streamline length written to {mean_length_file}")

    # --- Connectomes ---
    for idx, (name, atlas_file) in enumerate(zip(args.atlasNameList, args.atlasFileList)):
        weight_flag = []
        if args.weightMapList:
            weight_flag = ["-scale_file", args.weightMapList[idx], "-stat_edge", "mean"]

        out_csv = f"{outputbase}{name}.csv"
        out_csv = f"{outputbase}{name}.csv"

        print(f"Running connectome for atlas: {name}")

        run([
            "tck2connectome",
            "-symmetric",
            "-zero_diagonal",
            "-scale_invnodevol",
            "-assignment_end_voxels",
            "-tck_weights_in", sift_weights,
            *weight_flag,
            tck_file,
            atlas_file,
            out_csv
        ])

if __name__ == "__main__":
    main()
