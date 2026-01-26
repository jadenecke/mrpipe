import sys
from pickletools import string1

from mrpipe.meta.ImageWithSideCar import ImageWithSideCar
from mrpipe.meta import LoggerModule
from mrpipe.meta.PathClass import Path
from mrpipe.Helper import Helper
from typing import List
from numpy import cross
import glob
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import matplotlib.colors as colors
import pandas as pd
from matplotlib import animation

logger = LoggerModule.Logger()

class MEGRE():
    def __init__(self, inputDirectory: Path = None, magnitudePaths: List[Path] = None, phasePaths: List[Path] = None,
                 magnitudeJsonPaths: List[Path] = None, phaseJsonPaths: List[Path] = None, echoNumber: int = None,
                 echoTimes: List[float] = None):
        self.echoNumber = None
        self.echoTimes = None
        self.magnitude = []
        self.phase = []

        if inputDirectory is not None:
            niftiFiles = glob.glob(str(inputDirectory.join("*.nii*")))
            jsonFiles = glob.glob(str(inputDirectory.join("*.json")))
            if len(niftiFiles) <= 1:
                logger.error("No nifti files found. Will not proceed. Directory of files: " + str(inputDirectory))
                #TODO maybe solve this more gracefully: if file is not found config exits, but realy the processing module should get removed with an error from the session.
                #sys.exit(1)
                return None
            self._magnitudePaths, self._phasePaths = Helper.separate_files(niftiFiles, ["ph", "pha", "phase"], ensureEqual=True)
            self._magnitudeJsonPaths, self._phaseJsonPaths = Helper.separate_files(jsonFiles, ["ph", "pha", "phase"], ensureEqual=True)
            #bring image and json paths in the same order:
            self._magnitudePaths, self._magnitudeJsonPaths = Helper.match_lists(self._magnitudePaths, self._magnitudeJsonPaths)
            self._phasePaths, self._phaseJsonPaths = Helper.match_lists(self._phasePaths, self._phaseJsonPaths)
        else:
            self._magnitudePaths = magnitudePaths
            self._phasePaths = phasePaths
            self._magnitudeJsonPaths = magnitudeJsonPaths
            self._phaseJsonPaths = phaseJsonPaths

        if self._magnitudeJsonPaths is not None and self._phaseJsonPaths is not None:
            logger.debug("Taking MEGRE information from nifti files and json sidecars")
            if not len(self._magnitudePaths) == len(self._phasePaths) == len(self._magnitudeJsonPaths) == len(self._phaseJsonPaths):
                logger.error(f"File number of magnitude and phase and json files do not match: {self._magnitudePaths}, {self._phasePaths}, {self._magnitudeJsonPaths}, {self._phaseJsonPaths}")
                self._magnitudePaths = self._magnitudeJsonPaths = self._phasePaths = self._phaseJsonPaths = None
            self.magnitude: List[ImageWithSideCar] = [ImageWithSideCar(imagePath=fp, jsonPath=jp) for fp, jp in zip(self._magnitudePaths, self._magnitudeJsonPaths)]
            self.phase: List[ImageWithSideCar] = [ImageWithSideCar(imagePath=fp, jsonPath=jp) for fp, jp in zip(self._phasePaths, self._phaseJsonPaths)]
            self.echoNumber = len(self.magnitude)
            self.echoTimes = [mag.getAttribute("EchoTime") for mag in self.magnitude]
            # sort them by echo times
            self.sort_by_echoTimes() #only required if echo times are picked up by json files and from directory
        else:
            if inputDirectory is not None:
                # TODO: This setup will lead to unwanted side effects if the image paths are determined automatically from an input directory, but json Paths are none (because none present), then the images will be unordered and not match the echo timings
                logger.error(f"Echo times could not be determined from the json files in this input directory: {inputDirectory}. This will highly likely cause errors because the image files were automatically determined and can not be brought in the correct order. This session will be removed.")
                self._magnitudePaths = self._magnitudeJsonPaths = self._phasePaths = self._phaseJsonPaths = None
            logger.debug("Taking MEGRE information from nifti files and utilizing general echo number and time information")
            if echoNumber is None or echoTimes is None:
                logger.error(f"No Echo Number and Echo times for the given magnitude and phase images. This is to few information to work with. Magnitude file: {self._magnitudePaths}")
                self._magnitudePaths = self._magnitudeJsonPaths = self._phasePaths = self._phaseJsonPaths = None

            #TODO Fix this: just assume that jsons must be present. Otherwise instruct user to create jsons files with necessary information.
            self.echoNumber = echoNumber
            self.echoTimes = echoTimes

        logger.debug(f"Identified: {self}")

    def get_magnitude_paths(self):
        return [mag.imagePath for mag in self.magnitude]

    def get_phase_paths(self):
        return [pha.imagePath for pha in self.phase]

    def get_b0_directions(self):
        resList = []
        for mag in self.magnitude:
            ori = mag.getAttribute("ImageOrientationPatientDICOM")
            Xz = ori[2]
            Yz = ori[5]
            Zxyz = cross(ori[0:3], ori[3:6])
            Zz = Zxyz[2]
            resList.append([-Xz, -Yz, Zz])
        for i in range(1, len(resList)):
            eps = 0.000001
            if sum([abs(a_i - b_i) for a_i, b_i in zip(resList[0], resList[i])]) > eps:
                logger.error(
                    f"Different b0 field directions from different echos for, returning None and failing for the session: {self.magnitude.jsonPaths[0]}")
        logger.info("Calculated B0 field direction of image based on ImageOrientationPatientDICOM: {H}")
        return resList[0]

    def validate(self) -> bool:
        if self.echoNumber is None or self.echoTimes is None:
            return False
        if self.magnitude is None or self.phase is None:
            return False
        if len(self.magnitude) <= 2:
            logger.warning("Number of magnitude/Phase images must be greater than 2")
            return False
        if len(self.echoTimes) < 2:
            return False
        if not len(self.magnitude) == len(self.phase) == len(self.echoTimes):
            return False
        return True

    def sort_by_echoTimes(self):
        magEchoTimes = [mag.getAttribute("EchoTime") for mag in self.magnitude]
        phaEchoTimes = [pha.getAttribute("EchoTime") for pha in self.phase]
        #Error check if Echo times are missing:
        if any([mag is None for mag in magEchoTimes]) or any([pha is None for pha in phaEchoTimes]):
            logger.error(f"Found no magnitude/phase echo times for {magEchoTimes}/{self._magnitudePaths} and {phaEchoTimes}/{self._phasePaths} for sorting. This may result in errors later on.")
            return None
        # Combine the lists into a list of tuples
        combinedMag = list(zip(self.magnitude, magEchoTimes))
        combinedPha = list(zip(self.phase, phaEchoTimes))
        # Sort the combined list based on the echoTimes values
        combinedMag.sort(key=lambda x: x[1])
        combinedPha.sort(key=lambda x: x[1])
        logger.debug(f"Sorting by Echo. \nResult Magnitude: {combinedMag}, \nResult Phase: {combinedPha}")
        # Unzip the sorted combined list back into individual lists
        self.magnitude, self.echoTimes = zip(*combinedMag)
        self.phase, _ = zip(*combinedPha)

    def __str__(self):
        return f"MEGRE seqeuence: Echo Number: {self.echoNumber} ({self.echoTimes})\nMagnitude:\n{[str(m) for m in self.magnitude]}\nPhase:\n{[str(p) for p in self.phase]}"
    
class DWI():
    bavl_rounding_warning_thrown = False
    def __init__(self, inputDirectory: Path = None, images4d_filepaths: List[Path] = None, sidecar_filepaths: List[Path] = None,
                 bval_filepaths: List[Path] = None, bvec_filepaths: List[Path] = None, onlyWithReversePhaseEncoding: bool = True,
                 bval_tol: int = 20, non_gaussian_cutoff: int = 1500):
        # individual inputs will take precedence over inputDirectory

        #processing args:
        self.bval_tol = bval_tol
        self.non_gaussian_cutoff = non_gaussian_cutoff

        #File Paths
        self.image = None
        self.bval = None
        self.bvec = None
        self.image_reverse = None
        self.bval_reverse = None
        self.bvec_reverse = None

        #Attributes of main Image
        self.bval_vec = None
        self.bvec_mat = None
        self.diffShemeExact = None
        self.diffShemeRounded = None
        self.image_encoding_direction = None
        self.is_multishell = None
        self.is_fullshell = None
        self.contains_b0 = None
        self.is_non_gaussian = None
        self.nb0s = None

        #atributes of reverse encoded Image
        self.bval_vec_reverse = None
        self.bvec_mat_reverse = None
        self.diffShemeExact_reverse = None
        self.diffShemeRounded_reverse = None
        self.image_encoding_direction_reverse = None
        self.is_fullshell_reverse = None
        self.contains_b0_reverse = None
        self.is_non_gaussian_reverse = None
        self.nb0s_reverse = None


        if inputDirectory is not None:
            potential_images4d_filepaths = glob.glob(str(inputDirectory.join("*.nii*")))
            potential_sidecar_filepaths = glob.glob(str(inputDirectory.join("*.json")))
            potential_bval_filepaths = glob.glob(str(inputDirectory.join("*.bvec")))
            potential_bvec_filepaths = glob.glob(str(inputDirectory.join("*.bval")))

            if len(potential_images4d_filepaths) <= 1:
                logger.error("No nifti files found. Will not proceed. Directory of files: " + str(inputDirectory))
                # TODO maybe solve this more gracefully: if file is not found config exits, but realy the processing module should get removed with an error from the session: see whether return did the trick.
                #sys.exit(1)
                return None

            potential_images4d_filepaths, potential_sidecar_filepaths, potential_bval_filepaths, potential_bvec_filepaths = Helper.match_lists_multi(potential_images4d_filepaths,
                                     potential_sidecar_filepaths,
                                     potential_bval_filepaths,
                                     potential_bvec_filepaths)

            if images4d_filepaths is None:
                images4d_filepaths = potential_images4d_filepaths
            if sidecar_filepaths is None:
                sidecar_filepaths = potential_sidecar_filepaths
            if bval_filepaths is None:
                bval_filepaths = potential_bval_filepaths
            if bvec_filepaths is None:
                bvec_filepaths = potential_bvec_filepaths

        # check if all lists ar either of length 1 or 2 (if onlyWithReversePhaseEncoding is True) and if not raise error
        if  all(len(x) in [1] for x in [images4d_filepaths, sidecar_filepaths, bval_filepaths, bvec_filepaths]):
            logger.debug("Only one image per volume, no reverse phase encoding")
            if onlyWithReversePhaseEncoding:
                logger.error("Only one image per volume, but onlyWithReversePhaseEncoding is True. This is not allowed, will skip this session.")
                return

            self.image = ImageWithSideCar(imagePath=images4d_filepaths[0], jsonPath=sidecar_filepaths[0])
            self.bval = bval_filepaths[0]
            self.bvec = bvec_filepaths[0]
            self.image_reverse = None
            self.bval_reverse = None
            self.bvec_reverse = None

        elif all(len(x) in [2] for x in [self.images4d_filepaths, self.sidecar_filepaths, self.bval_filepaths, self.bvec_filepaths]):
            logger.debug("Two images per volume, with reverse phase encoding")

            l0 = sum([len(line.split(" ")) for line in open(bval_filepaths[0])])
            l1 = sum([len(line.split(" ")) for line in open(bval_filepaths[1])])
            if l0 > l1:
                self.image = ImageWithSideCar(imagePath=images4d_filepaths[0], jsonPath=sidecar_filepaths[0])
                self.bval = bval_filepaths[0]
                self.bvec = bvec_filepaths[0]
                self.image_reverse = ImageWithSideCar(imagePath=images4d_filepaths[1], jsonPath=sidecar_filepaths[1])
                self.bval_reverse = bval_filepaths[1]
                self.bvec_reverse = bvec_filepaths[1]
            elif l1 > l0:
                self.image = ImageWithSideCar(imagePath=images4d_filepaths[1], jsonPath=sidecar_filepaths[1])
                self.bval = bval_filepaths[1]
                self.bvec = bvec_filepaths[1]
                self.image_reverse = ImageWithSideCar(imagePath=images4d_filepaths[0], jsonPath=sidecar_filepaths[0])
                self.bval_reverse = bval_filepaths[0]
                self.bvec_reverse = bvec_filepaths[0]
            else:
                logger.error("Both bval files have the same number of lines. This is not allowed, will skip this session.")
        else :
            logger.error(
                f"Not all file lists have length 1 or 2 despite onlyWithReversePhaseEncoding being True. File counts: images:{len(self.images4d_filepaths)}, sidecars:{len(self.sidecar_filepaths)}, bvals:{len(self.bval_filepaths)}, bvecs:{len(self.bvec_filepaths)}")
            raise ValueError("Invalid number of input files")

        if self.image.getAttribute("PhaseEncodingDirection") == self.image_reverse.getAttribute("PhaseEncodingDirection"):
            logger.critical(f"PhaseEncodingDirection of images is identical. This is very much unexpected and most likely indicates a problem in the nifti conversion. Image: {self.image.imagePath}, Image_reverse: {self.image_reverse.imagePath}")

    def read_dwi_params(self):
        import pandas as pd
        if self.image and self.image.imagePath.exists():
            if self.bval.exists():
                # self.bval_vec = np.genfromtxt(self.bval, dtype=int, delimiter=' ', names=None) # some files have multiple spaces as seperator, the this does not work
                self.bval_vec = pd.read_csv(self.bval, header=None, sep=r'\s+', nrows=1, dtype=float).to_numpy()
                self.diffShemeExact = list(set(self.bval_vec))
                self.diffShemeExact.sort()
                self.diffShemeRounded = list(set([(y / 10).round() * 10 for y in list(set(self.diffShemeExact))]))
                if not DWI.bavl_rounding_warning_thrown and len(self.diffShemeRounded) != len(self.diffShemeExact):
                    logger.error(f"DWI bval file contains minor variations in diffusion strength, shells will be rounded to determine protocol structure. Original: {self.diffShemeExact}, rounded: {self.diffShemeRounded}")
                self.nb0s = sum(self.bval_vec <= self.bval_tol)
                if self.nb0s > 0:
                    self.contains_b0 = True
                    numerator = 1
                else:
                    self.contains_b0 = False
                    numerator = 0
                if any([x > self.non_gaussian_cutoff for x in self.diffShemeRounded]):
                    self.is_non_gaussian = True

                if len(self.diffShemeRounded) == (1 + numerator):
                    self.is_multishell = False
                elif len(self.diffShemeRounded) == (0 + numerator):
                    self.is_multishell = False
                else:
                    self.is_multishell = True
                self.image_encoding_direction = self.image.getAttribute("PhaseEncodingDirection")
            else:
                return False
            if self.bvec.exists():
                # self.bvec_mat = np.genfromtxt(self.bvec, dtype=int, delimiter=' ', names=None)
                self.bvec_mat = pd.read_csv(self.bvec, header=None, sep=r'\s+', nrows=3, dtype=float).to_numpy()
                self.is_fullshell = DWI.is_fullshell(self.bvec_mat)
            else:
                return False

        if self.image_reverse and self.image_reverse.imagePath.exists():
            if self.bval_reverse.exists():
                # self.bval_vec = np.genfromtxt(self.bval, dtype=int, delimiter=' ', names=None) # some files have multiple spaces as seperator, the this does not work
                self.bval_vec_reverse = pd.read_csv(self.bval_reverse, header=None, sep=r'\s+', nrows=1, dtype=float).to_numpy()
                self.diffShemeExact_reverse = list(set(self.bval_vec_reverse))
                self.diffShemeExact_reverse.sort()
                self.diffShemeRounded_reverse = list(set([(y / 10).round() * 10 for y in list(set(self.diffShemeExact_reverse))]))
                if not DWI.bavl_rounding_warning_thrown and len(self.diffShemeRounded_reverse) != len(self.diffShemeExact_reverse):
                    logger.error(f"DWI bval file contains minor variations in diffusion strength, shells will be rounded to determine protocol structure. Original: {self.diffShemeExact}, rounded: {self.diffShemeRounded}")
                self.nb0s_reverse = sum(self.bval_vec_reverse <= self.bval_tol)
                if self.nb0s_reverse > 0:
                    self.contains_b0_reverse = True
                    numerator_reverse = 1
                else:
                    self.contains_b0_reverse = False
                    numerator_reverse = 0
                if any([x > self.non_gaussian_cutoff for x in self.diffShemeRounded_reverse]):
                    self.is_non_gaussian_reverse = True

                if len(self.diffShemeRounded_reverse) == (1 + numerator_reverse):
                    self.is_multishell_reverse = False
                elif len(self.diffShemeRounded_reverse) == (0 + numerator_reverse):
                    self.is_multishell_reverse = False
                else:
                    self.is_multishell_reverse = True
                self.image_encoding_direction_reverse = self.image_reverse.getAttribute("PhaseEncodingDirection")
            else:
                return False
            if self.bvec.exists():
                # self.bvec_mat = np.genfromtxt(self.bvec, dtype=int, delimiter=' ', names=None)
                self.bvec_mat_reverse = pd.read_csv(self.bvec_reverse, header=None, sep=r'\s+', nrows=3, dtype=float).to_numpy()
                self.is_fullshell_reverse = DWI.is_fullshell(self.bvec_mat_reverse)
            else:
                return False
        return True

    def validate(self) -> bool:
        if self.image is None or self.bval is None or self.bvec is None:
            return False
        return True

    @staticmethod
    def has_antipodes(vectors, ang_tol_deg=1.0):
        """
        Determine if for each unique direction, its antipode is present
        within angular tolerance. Returns True if full-shell (antipodal
        coverage), False if half-shell.
        """

        from collections import defaultdict
        v = DWI.normalize_vectors(vectors)
        n = len(v)
        if n == 0:
            return False
        cos_tol = np.cos(np.deg2rad(ang_tol_deg))

        # Build a quick search structure by hashing rounded coords
        def key(vec, k=3):
            return tuple(np.round(vec, k))

        buckets = defaultdict(list)
        for i, vec in enumerate(v):
            buckets[key(vec)].append(i)
        # For each direction, check existence of antipode within tolerance
        for i in range(n):
            antipode = -v[i]
            # candidates: check near rounded key and neighboring roundings
            found = False
            # Try multiple rounding granularities for robustness
            for k in (3, 2, 4):
                cand = buckets.get(tuple(np.round(antipode, k)), [])
                if cand:
                    # verify angular match
                    if np.max(v[cand] @ antipode) >= cos_tol:
                        found = True
                        break
            if not found:
                # also do a brute-force fallback if hashing misses
                dots = v @ antipode
                if np.max(dots) >= cos_tol:
                    found = True
            if not found:
                return False
        return True

    @staticmethod
    def normalize_vectors(bvecs, eps=1e-12):
        bvecs = np.asarray(bvecs, dtype=float)
        norms = np.linalg.norm(bvecs, axis=1, keepdims=True)
        norms = np.where(norms < eps, 1.0, norms)
        return bvecs / norms

    @staticmethod
    def group_shells(bvals, tol=50):
        bvals = np.asarray(bvals).astype(float)
        sorted_idx = np.argsort(bvals)
        shells = []
        for idx in sorted_idx:
            b = bvals[idx]
            placed = False
            for sb, members in shells:
                if abs(b - sb) <= tol:
                    members.append(idx)
                    placed = True
                    break
            if not placed:
                shells.append([b, [idx]])
        shell_map = {}
        for _, members in shells:
            b_mean = float(np.mean(bvals[members]))
            shell_map[b_mean] = members
        return shell_map

    @staticmethod
    def normalize_vectors(bvecs, eps=1e-12):
        bvecs = np.asarray(bvecs, dtype=float)
        norms = np.linalg.norm(bvecs, axis=1, keepdims=True)
        norms = np.where(norms < eps, 1.0, norms)
        return bvecs / norms

    @staticmethod
    def unique_directions(vectors, ang_tol_deg=1.0):
        v = DWI.normalize_vectors(vectors)
        used = np.zeros(len(v), dtype=bool)
        reps = []
        groups = []
        cos_tol = np.cos(np.deg2rad(ang_tol_deg))
        for i in range(len(v)):
            if used[i]:
                continue
            rep = v[i]
            same = []
            for j in range(i, len(v)):
                if used[j]:
                    continue
                c = np.dot(rep, v[j])
                if c >= cos_tol:
                    same.append(j)
                    used[j] = True
            reps.append(i)
            groups.append(same)
        return reps, groups

    @staticmethod
    def is_fullshell(vectors):
        if not any(vectors[:, 0] < 0):
            return False
        if not any(vectors[:, 1] < 0):
            return False
        if not any(vectors[:, 2] < 0):
            return False
        return True

    @staticmethod
    def analyze_protocol(bvals, bvecs, b_tol=10, ang_tol_deg=1.0, exclude_b0=True, b0_max=20):
        bvals = np.asarray(bvals).astype(float)
        bvecs = np.asarray(bvecs).astype(float)
        assert bvecs.shape[1] == 3 and bvecs.shape[0] == bvals.shape[0], "Mismatched bvals/bvecs"
        shells = DWI.group_shells(bvals, tol=b_tol)
        report = []
        for shell_b, idxs in sorted(shells.items(), key=lambda kv: kv[0]):
            if exclude_b0 and shell_b <= b0_max:
                continue
            vecs = bvecs[idxs]
            reps, _ = DWI.unique_directions(vecs, ang_tol_deg=ang_tol_deg)
            n_dirs = len(reps)
            full = DWI.is_fullshell(vecs)
            report.append({
                "shell_b": shell_b,
                "indices": idxs,
                "n_dirs": n_dirs,
                "is_full_shell": full
            })
        return report

    @staticmethod
    def plot_shells_as_arrows(ax, bvals, bvecs, report, elev=20, azim=30, scale_mode="relative"):
        """
        Plot arrows (quivers) from origin in direction of b-vectors.
        Arrow length is scaled by corresponding b-value.
        """

        bvals = np.asarray(bvals).astype(float)
        bvecs = DWI.normalize_vectors(np.asarray(bvecs).astype(float))

        # Scaling
        all_idxs = np.concatenate([np.asarray(s["indices"], dtype=int) for s in report]) if report else np.array([], dtype=int)
        b_for_scale = bvals[all_idxs] if len(all_idxs) else np.array([1.0])
        b_max = float(np.max(b_for_scale)) if np.any(b_for_scale > 0) else 1.0

        def length_from_b(b):
            if scale_mode == "absolute":
                return b
            return 0.2 + 0.8 * (b / b_max if b_max > 0 else 0.0)

        color_map1 = ["#E41A1C", "#4DAF4A", "#984EA3", "#F781BF", "#FF7F00", "#A65628", "#377EB8"]
        color_map = colors.ListedColormap(color_map1)
        # colors = plt.get_cmap('tab10', max(1, len(report)))

        legend_handles = []
        for i, shell in enumerate(report):
            idxs = np.asarray(shell["indices"], dtype=int)
            vecs = bvecs[idxs]
            bs = bvals[idxs]
            lengths = np.vectorize(length_from_b)(bs)
            U = vecs[:, 0] * lengths
            V = vecs[:, 1] * lengths
            W = vecs[:, 2] * lengths

            ax.quiver(
                np.zeros_like(U), np.zeros_like(V), np.zeros_like(W),
                U, V, W,
                length=1.0, normalize=False, color=color_map(i), linewidth=0.8, arrow_length_ratio=0.12, alpha=0.4,
            )

            # Build legend entry per shell (color only)
            label = f"b≈{int(round(shell['shell_b']))} | {shell['n_dirs']} dirs | {'full' if shell['is_full_shell'] else 'half'}"
            legend_handles.append(Line2D([0], [0], color=color_map(i), lw=3, label=label))

        # # Context sphere
        # u = np.linspace(0, 2*np.pi, 60)
        # v = np.linspace(0, np.pi, 30)
        # xs = np.outer(np.cos(u), np.sin(v))
        # ys = np.outer(np.sin(u), np.sin(v))
        # zs = np.outer(np.ones_like(u), np.cos(v))
        # ax.plot_wireframe(xs, ys, zs, rstride=6, cstride=6, color='gray', alpha=0.3, linewidth=1)

        ax.set_box_aspect([1, 1, 1])
        ax.set_xlim([-1, 1])
        ax.set_ylim([-1, 1])
        ax.set_zlim([-1, 1])
        ax.view_init(elev=elev, azim=azim)
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')

        # Color legend for shells
        ax.legend(handles=legend_handles, title="b-shells", loc='lower center', bbox_to_anchor=(0.5, -0.2), borderaxespad=0.)

        plt.tight_layout()
        ax.grid(False)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_zticks([])
        return ax

    @staticmethod
    def render_rotation(bvals, bvecs, report, filename, figsize=(4, 4), dpi=72, elev=20, frames=45, fps=8, scale_mode="relative"):
        """
        Create a 360° rotation animation around the vertical axis (azimuth).
        filename: ends with .mp4 (preferred) or .gif (needs ImageMagick or Pillow writer).
        """
        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111, projection='3d')

        DWI.plot_shells_as_arrows(ax, bvals, bvecs, report, scale_mode=scale_mode)

        def init():
            ax.view_init(elev=elev, azim=0)
            return (fig,)

        def animate(f):
            az = 360.0 * (f / frames)
            ax.view_init(elev=elev, azim=az)
            return (fig,)

        anim = animation.FuncAnimation(fig, animate, init_func=init, frames=frames, interval=1000 / fps, blit=False)

        if filename.lower().endswith(".mp4"):
            try:
                writer = animation.FFMpegWriter(fps=fps, bitrate=3000)
                anim.save(filename, writer=writer, dpi=dpi)
            except Exception as e:
                print("FFmpeg writer not available or failed:", e)
                print("Try installing FFmpeg, or save as GIF instead.")
        elif filename.lower().endswith(".gif"):
            try:
                anim.save(filename, writer='pillow', fps=fps)
            except Exception as e:
                print("Pillow writer not available or failed:", e)
                print("Ensure Pillow is installed and try again.")
        else:
            print("Unsupported extension. Use .mp4 or .gif.")

        plt.close(fig)