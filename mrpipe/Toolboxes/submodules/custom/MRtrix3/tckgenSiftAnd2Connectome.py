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

    parser.add_argument('-w', '--wmfodNorm', dest="wmfodNorm", type=str)
    parser.add_argument('-a', '--T1_5TTReg', dest="T1_5TTReg", type=str)
    parser.add_argument('-n', '--nstreamlines', dest='nstreamlines', type=str, default="20000000",)
    parser.add_argument('-o', '--outputbase', dest="outputbase", type=str)
    parser.add_argument('-s', '--scratch', dest="scratch", type=str)

    parser.add_argument("--threads", type=str, default=None)
    parser.add_argument("--force", action="store_true")

    parser.add_argument("--atlasNameList", nargs="+", required=True, type=str)
    parser.add_argument("--atlasFileList", nargs="+", required=True, type=str)

    parser.add_argument("--weightMaps", nargs="+", required=False, default=None, type=str)
    parser.add_argument("--weightMapsNames", nargs="+", required=False, default=None, type=str)

    args = parser.parse_args()

    # --- Sanity checks ---
    if len(args.atlasNameList) != len(args.atlasFileList):
        print("ERROR: atlasNameList and atlasFileList must have same length")
        sys.exit(1)

    if len(args.weightMaps) != len(args.weightMapsNames):
        print("ERROR: atlasNameList and atlasFileList must have same length")
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

    if args.weightMaps:
        for w in args.weightMaps:
            check_file(w, "Weight map")

    # Check atlas names
    if len(set(args.atlasNameList)) != len(args.atlasNameList):
        print("ERROR: Duplicate atlas names detected")
        sys.exit(1)

    if len(set(args.weightMapsNames)) != len(args.weightMapsNames):
        print("ERROR: Duplicate weight map names detected")
        sys.exit(1)

    # --- Create temp working directory ---
    work_dir = tempfile.mkdtemp(prefix="tckgenSift2connectome_", dir=scratch)
    print(f"Using temporary working directory: {work_dir}")

    def cleanup():
        if os.path.isdir(work_dir):
            print(f"Deleting temp working directory {work_dir}")
            subprocess.run(["rm", "-rf", work_dir])
    #atexit.register(cleanup)

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

    # --- Scale Files ---
    if args.weightMaps:
        for weight_map_name, weight_map in zip(args.weightMapsNames, args.weightMaps):
            run([
                "tcksample",
                "-stat_tck", "median",
                tck_file,
                weight_map,
                os.path.join(work_dir, f"{weight_map_name}.txt")
            ])



    # --- Connectomes ---
    for name, atlas_file in zip(args.atlasNameList, args.atlasFileList):
        print(f"Running connectome for atlas: {name}")

        run([
            "tck2connectome",
            "-symmetric",
            "-zero_diagonal",
            "-scale_invnodevol",
            "-assignment_end_voxels",
            "-tck_weights_in", sift_weights,
            tck_file,
            atlas_file,
            f"{outputbase}{name}_weightedStreamlineNumber.csv"
        ])

        run([
            "tck2connectome",
            "-symmetric",
            "-zero_diagonal",
            "-assignment_end_voxels",
            "-tck_weights_in", sift_weights,
            "-scale_length", "-stat_edge", "mean",
            tck_file,
            atlas_file,
            f"{outputbase}{name}_StreamlineLength.csv"
        ])

        if args.weightMaps:
            for weight_map_name, weight_map in zip(args.weightMapsNames, args.weightMaps):

                run([
                    "tck2connectome",
                    "-symmetric",
                    "-zero_diagonal",
                    "-assignment_end_voxels",
                    "-tck_weights_in", sift_weights,
                    "-scale_file", os.path.join(work_dir, f"{weight_map_name}.txt"), "-stat_edge", "mean",
                    tck_file,
                    atlas_file,
                    f"{outputbase}{name}_{weight_map_name}.csv"
                ])

if __name__ == "__main__":
    main()
