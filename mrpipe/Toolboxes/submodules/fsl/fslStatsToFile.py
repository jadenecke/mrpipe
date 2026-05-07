# infile: Path, output: Path, options: List[str], mask: Path = None,
#                  preoptions: List[str] = None
#
#         self.inputImage = infile
#         self.options = Helper.ensure_list(options, flatten=True)
#         if preoptions is None:
#             self.preOptions = []
#         else:
#             self.preOptions = Helper.ensure_list(preoptions, flatten=True)
#         self.outputFile = output
#         self.mask = mask
#
#
#
#     def getCommand(self):
#         command = f"fslstats"
#         for opt in self.preOptions:
#             command += f" {opt}"
#         command += f" {self.inputImage.path}"
#         for opt in self.options:
#             if opt == "-k":
#                 command += f" -k {self.mask.path}"
#             elif opt == "-V":
#                 command += " -V  | awk '{print $2}'"
#                 break
#             else:
#                 command += f" {opt}"
#         command += f" > {self.outputFile}"
#         return command

import argparse
import subprocess
from pathlib import Path
from typing import List, Optional


class FslStatsCommand:
    def __init__(
        self,
        infile: Path,
        output: Path,
        options: List[str],
        mask: Optional[Path] = None,
        preoptions: Optional[List[str]] = None,
    ):
        self.inputImage = infile
        self.options = options or []
        self.preOptions = preoptions or []
        self.outputFile = output
        self.mask = mask

    def build_args(self) -> List[str]:
        args = ["fslstats"]

        args.extend(self.preOptions)
        args.append(str(self.inputImage))

        for opt in self.options:
            if opt == "-k":
                if not self.mask:
                    raise ValueError("Mask path must be provided when using '-k'")
                args.extend(["-k", str(self.mask)])
            else:
                args.append(opt)

        return args

    def run(self):
        args = self.build_args()

        result = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )

        output_text = result.stdout.strip()

        # Replace awk '{print $2}' behavior for -V
        if "-V" in self.options:
            # fslstats -V outputs: "<voxels> <volume>"
            parts = output_text.split()
            if len(parts) >= 2:
                output_text = parts[1]
            else:
                raise ValueError("Unexpected output format for -V")

        with open(self.outputFile, "w") as f:
            f.write(output_text + "\n")


def main():
    parser = argparse.ArgumentParser(description="Run fslstats")

    parser.add_argument("-i ", "--infile",
                        type=Path,
                        required=True,
                        help="Input image")

    parser.add_argument("-o", "--output",
                        type=Path,
                        required=True,
                        help="Output file")

    parser.add_argument(
        "--opt",
        action="append",
        required=True,
        help="Option to pass to fslstats (repeatable, e.g. -o=-V -o=-k)",
    )

    parser.add_argument(
        "--preoptions",
        action="append",
        default=[],
        help="Options before input image",
    )

    parser.add_argument(
        "--mask",
        type=Path,
        help="Mask image (required if -k is used)",
    )

    args = parser.parse_args()
    print(args)
    cmd = FslStatsCommand(
        infile=args.infile,
        output=args.output,
        options=args.opt,
        mask=args.mask,
        preoptions=args.preoptions,
    )

    cmd.run()


if __name__ == "__main__":
    main()