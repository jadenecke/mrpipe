#!/usr/bin/env python3
"""
Script to extract tracer and imaging window information from dynamic PET DICOM files.
Extracts radiopharmaceutical information and frame timing directly from DICOM headers.
"""

import argparse
import os
from pathlib import Path
from collections import defaultdict
import pydicom
from pydicom.errors import InvalidDicomError

# =============================================================================
# NORMATIVE TRACER AND PROTOCOL INFORMATION
# =============================================================================

# Known tracers by half-life (in seconds) for identification
TRACER_HALF_LIVES = {
    "F-18": {"half_life_range": (6400, 6800), "half_life_nominal": 6586},  # ~109.77 minutes
    "C-11": {"half_life_range": (1150, 1300), "half_life_nominal": 1224},  # ~20.4 minutes
    "Ga-68": {"half_life_range": (3900, 4200), "half_life_nominal": 4062},  # ~67.7 minutes
    "Rb-82": {"half_life_range": (70, 85), "half_life_nominal": 76},  # ~1.27 minutes
    "N-13": {"half_life_range": (580, 620), "half_life_nominal": 598},  # ~9.97 minutes
    "O-15": {"half_life_range": (115, 130), "half_life_nominal": 122},  # ~2.04 minutes
}

# Common PET protocols with imaging windows (in minutes post-injection)
# Format: tracer_key -> list of protocols with window ranges and BIDS suggestions
PET_PROTOCOLS = {
    # FDG - Glucose metabolism
    "FDG": {
        "radionuclide": "F-18",
        "protocols": [
            {"name": "FDG_early", "window": (0, 15), "bids_suffix": "pet", "bids_tracer": "FDG",
             "description": "FDG early/dynamic - perfusion-like or kinetic modeling"},
            {"name": "FDG_standard", "window": (45, 90), "bids_suffix": "pet", "bids_tracer": "FDG",
             "description": "FDG standard static - glucose metabolism"},
        ]
    },
    # Amyloid tracers
    "FBB": {  # Florbetaben / Neuraceq
        "radionuclide": "F-18",
        "protocols": [
            {"name": "FBB_early", "window": (0, 20), "bids_suffix": "pet", "bids_tracer": "FBB",
             "description": "FBB early - perfusion-like"},
            {"name": "FBB_standard", "window": (70, 110), "bids_suffix": "pet", "bids_tracer": "FBB",
             "description": "FBB standard - amyloid imaging"},
        ]
    },
    "FLORBETABEN": {  # Alias
        "radionuclide": "F-18",
        "protocols": [
            {"name": "FBB_early", "window": (0, 20), "bids_suffix": "pet", "bids_tracer": "FBB",
             "description": "FBB early - perfusion-like"},
            {"name": "FBB_standard", "window": (70, 110), "bids_suffix": "pet", "bids_tracer": "FBB",
             "description": "FBB standard - amyloid imaging"},
        ]
    },
    "AV45": {  # Florbetapir / Amyvid
        "radionuclide": "F-18",
        "protocols": [
            {"name": "AV45_early", "window": (0, 20), "bids_suffix": "pet", "bids_tracer": "AV45",
             "description": "AV45 early - perfusion-like"},
            {"name": "AV45_standard", "window": (50, 70), "bids_suffix": "pet", "bids_tracer": "AV45",
             "description": "AV45 standard - amyloid imaging"},
        ]
    },
    "FLORBETAPIR": {  # Alias
        "radionuclide": "F-18",
        "protocols": [
            {"name": "AV45_early", "window": (0, 20), "bids_suffix": "pet", "bids_tracer": "AV45",
             "description": "AV45 early - perfusion-like"},
            {"name": "AV45_standard", "window": (50, 70), "bids_suffix": "pet", "bids_tracer": "AV45",
             "description": "AV45 standard - amyloid imaging"},
        ]
    },
    "FMM": {  # Flutemetamol / Vizamyl
        "radionuclide": "F-18",
        "protocols": [
            {"name": "FMM_early", "window": (0, 20), "bids_suffix": "pet", "bids_tracer": "FMM",
             "description": "FMM early - perfusion-like"},
            {"name": "FMM_standard", "window": (85, 115), "bids_suffix": "pet", "bids_tracer": "FMM",
             "description": "FMM standard - amyloid imaging"},
        ]
    },
    "FLUTEMETAMOL": {  # Alias
        "radionuclide": "F-18",
        "protocols": [
            {"name": "FMM_early", "window": (0, 20), "bids_suffix": "pet", "bids_tracer": "FMM",
             "description": "FMM early - perfusion-like"},
            {"name": "FMM_standard", "window": (85, 115), "bids_suffix": "pet", "bids_tracer": "FMM",
             "description": "FMM standard - amyloid imaging"},
        ]
    },
    "NAV4694": {  # NAV4694 / AZD4694
        "radionuclide": "F-18",
        "protocols": [
            {"name": "NAV4694_early", "window": (0, 20), "bids_suffix": "pet", "bids_tracer": "NAV4694",
             "description": "NAV4694 early - perfusion-like"},
            {"name": "NAV4694_standard", "window": (40, 70), "bids_suffix": "pet", "bids_tracer": "NAV4694",
             "description": "NAV4694 standard - amyloid imaging"},
        ]
    },
    "PIB": {  # Pittsburgh Compound B (C-11)
        "radionuclide": "C-11",
        "protocols": [
            {"name": "PIB_early", "window": (0, 15), "bids_suffix": "pet", "bids_tracer": "PIB",
             "description": "PIB early - perfusion-like"},
            {"name": "PIB_standard", "window": (40, 70), "bids_suffix": "pet", "bids_tracer": "PIB",
             "description": "PIB standard - amyloid imaging"},
        ]
    },
    # Tau tracers
    "AV1451": {  # Flortaucipir / Tauvid
        "radionuclide": "F-18",
        "protocols": [
            {"name": "AV1451_early", "window": (0, 20), "bids_suffix": "pet", "bids_tracer": "AV1451",
             "description": "AV1451 early - perfusion-like"},
            {"name": "AV1451_standard", "window": (75, 105), "bids_suffix": "pet", "bids_tracer": "AV1451",
             "description": "AV1451 standard - tau imaging"},
        ]
    },
    "FLORTAUCIPIR": {  # Alias
        "radionuclide": "F-18",
        "protocols": [
            {"name": "AV1451_early", "window": (0, 20), "bids_suffix": "pet", "bids_tracer": "AV1451",
             "description": "AV1451 early - perfusion-like"},
            {"name": "AV1451_standard", "window": (75, 105), "bids_suffix": "pet", "bids_tracer": "AV1451",
             "description": "AV1451 standard - tau imaging"},
        ]
    },
    "PI2620": {  # PI-2620
        "radionuclide": "F-18",
        "protocols": [
            {"name": "PI2620_early", "window": (0, 20), "bids_suffix": "pet", "bids_tracer": "PI2620",
             "description": "PI-2620 early - perfusion-like"},
            {"name": "PI2620_standard", "window": (60, 90), "bids_suffix": "pet", "bids_tracer": "PI2620",
             "description": "PI-2620 standard - tau imaging"},
        ]
    },
    "MK6240": {
        "radionuclide": "F-18",
        "protocols": [
            {"name": "MK6240_early", "window": (0, 20), "bids_suffix": "pet", "bids_tracer": "MK6240",
             "description": "MK-6240 early - perfusion-like"},
            {"name": "MK6240_standard", "window": (90, 110), "bids_suffix": "pet", "bids_tracer": "MK6240",
             "description": "MK-6240 standard - tau imaging"},
        ]
    },
    # PSMA tracers (oncology)
    "PSMA": {
        "radionuclide": "Ga-68",
        "protocols": [
            {"name": "PSMA_early", "window": (0, 10), "bids_suffix": "pet", "bids_tracer": "PSMA",
             "description": "PSMA early"},
            {"name": "PSMA_standard", "window": (50, 80), "bids_suffix": "pet", "bids_tracer": "PSMA",
             "description": "PSMA standard - prostate imaging"},
        ]
    },
    # DOTATATE (neuroendocrine)
    "DOTATATE": {
        "radionuclide": "Ga-68",
        "protocols": [
            {"name": "DOTATATE_standard", "window": (40, 90), "bids_suffix": "pet", "bids_tracer": "DOTATATE",
             "description": "DOTATATE standard - neuroendocrine imaging"},
        ]
    },
    # Perfusion tracers
    "NH3": {  # N-13 Ammonia
        "radionuclide": "N-13",
        "protocols": [
            {"name": "NH3_dynamic", "window": (0, 20), "bids_suffix": "pet", "bids_tracer": "NH3",
             "description": "N-13 Ammonia - myocardial perfusion"},
        ]
    },
    "H2O": {  # O-15 Water
        "radionuclide": "O-15",
        "protocols": [
            {"name": "H2O_dynamic", "window": (0, 10), "bids_suffix": "pet", "bids_tracer": "H2O",
             "description": "O-15 Water - cerebral blood flow"},
        ]
    },
    "RB82": {  # Rubidium-82
        "radionuclide": "Rb-82",
        "protocols": [
            {"name": "Rb82_dynamic", "window": (0, 10), "bids_suffix": "pet", "bids_tracer": "Rb82",
             "description": "Rb-82 - myocardial perfusion"},
        ]
    },
}

# Tracer name aliases for matching
TRACER_ALIASES = {
    "FLUORODEOXYGLUCOSE": "FDG",
    "18F-FDG": "FDG",
    "F18-FDG": "FDG",
    "[18F]FDG": "FDG",
    "2-DEOXY-2-[18F]FLUORO-D-GLUCOSE": "FDG",
    "FLORBETABEN": "FBB",
    "NEURACEQ": "FBB",
    "[18F]FLORBETABEN": "FBB",
    "FLORBETAPIR": "AV45",
    "AMYVID": "AV45",
    "[18F]FLORBETAPIR": "AV45",
    "[18F]AV45": "AV45",
    "FLUTEMETAMOL": "FMM",
    "VIZAMYL": "FMM",
    "[18F]FLUTEMETAMOL": "FMM",
    "PITTSBURGH COMPOUND B": "PIB",
    "[11C]PIB": "PIB",
    "C-11 PIB": "PIB",
    "FLORTAUCIPIR": "AV1451",
    "TAUVID": "AV1451",
    "[18F]FLORTAUCIPIR": "AV1451",
    "[18F]AV-1451": "AV1451",
    "PI-2620": "PI2620",
    "[18F]PI-2620": "PI2620",
    "[18F]MK-6240": "MK6240",
    "MK-6240": "MK6240",
    "68GA-PSMA": "PSMA",
    "GA-68 PSMA": "PSMA",
    "[68GA]PSMA": "PSMA",
    "68GA-DOTATATE": "DOTATATE",
    "[68GA]DOTATATE": "DOTATATE",
    "N-13 AMMONIA": "NH3",
    "[13N]AMMONIA": "NH3",
    "O-15 WATER": "H2O",
    "[15O]WATER": "H2O",
    "[15O]H2O": "H2O",
    "RUBIDIUM-82": "RB82",
    "RB-82": "RB82",
}


def identify_radionuclide_from_halflife(half_life_seconds):
    """Identify radionuclide based on half-life."""
    if half_life_seconds is None:
        return None

    for nuclide, info in TRACER_HALF_LIVES.items():
        if info["half_life_range"][0] <= half_life_seconds <= info["half_life_range"][1]:
            return nuclide
    return None


def normalize_tracer_name(tracer_name):
    """Normalize tracer name to standard key."""
    if tracer_name is None:
        return None

    # Convert to uppercase and remove common separators
    normalized = tracer_name.upper().strip()
    normalized = normalized.replace("-", "").replace("_", "").replace(" ", "")

    # Check direct match first
    if normalized in PET_PROTOCOLS:
        return normalized

    # Check aliases
    for alias, standard in TRACER_ALIASES.items():
        alias_normalized = alias.upper().replace("-", "").replace("_", "").replace(" ", "")
        if alias_normalized in normalized or normalized in alias_normalized:
            return standard

    # Partial matching for common patterns
    if "FDG" in normalized or "FLUORODEOXYGLUCOSE" in normalized:
        return "FDG"
    if "FLORBETABEN" in normalized or "FBB" in normalized or "NEURACEQ" in normalized:
        return "FBB"
    if "FLORBETAPIR" in normalized or "AV45" in normalized or "AMYVID" in normalized:
        return "AV45"
    if "FLUTEMETAMOL" in normalized or "FMM" in normalized or "VIZAMYL" in normalized:
        return "FMM"
    if "PIB" in normalized or "PITTSBURGH" in normalized:
        return "PIB"
    if "FLORTAUCIPIR" in normalized or "AV1451" in normalized or "TAUVID" in normalized:
        return "AV1451"
    if "PI2620" in normalized:
        return "PI2620"
    if "MK6240" in normalized:
        return "MK6240"
    if "PSMA" in normalized:
        return "PSMA"
    if "DOTATATE" in normalized or "DOTATOC" in normalized:
        return "DOTATATE"
    if "AMMONIA" in normalized or "NH3" in normalized:
        return "NH3"
    if "WATER" in normalized or "H2O" in normalized:
        return "H2O"
    if "RUBIDIUM" in normalized or "RB82" in normalized:
        return "RB82"

    return None


def guess_modality_and_bids(tracer_info, frames):
    """
    Guess the modality/protocol and BIDS naming based on tracer and frame timing.

    Returns a dictionary with:
    - protocol_name: Identified protocol name
    - bids_tracer: BIDS-compatible tracer label
    - bids_suffix: BIDS suffix (typically 'pet')
    - scan_type: 'early', 'standard', 'dynamic', or 'unknown'
    - description: Human-readable description
    - confidence: 'high', 'medium', or 'low'
    - notes: List of any notes/warnings
    """
    result = {
        'protocol_name': None,
        'bids_tracer': None,
        'bids_suffix': 'pet',
        'scan_type': 'unknown',
        'description': None,
        'confidence': 'low',
        'notes': [],
        'bids_filename_suggestion': None,
    }

    if not frames:
        result['notes'].append("No frame timing information available")
        return result

    # Get imaging window in minutes
    first_frame = frames[0]
    last_frame = frames[-1]

    window_start_ms = first_frame.get('frame_start_time_ms')
    window_end_ms = last_frame.get('frame_end_time_ms')

    if window_start_ms is None or window_end_ms is None:
        result['notes'].append("Incomplete frame timing information")
        return result

    window_start_min = window_start_ms / 60000.0
    window_end_min = window_end_ms / 60000.0
    window_duration_min = window_end_min - window_start_min

    # Determine if this is likely a dynamic or static scan
    num_frames = len(frames)
    is_dynamic = num_frames > 1

    # Try to identify tracer
    tracer_name = tracer_info.get('tracer_name')
    tracer_code = tracer_info.get('tracer_code')
    half_life = tracer_info.get('half_life_seconds')

    # Normalize tracer name
    normalized_tracer = normalize_tracer_name(tracer_name) or normalize_tracer_name(tracer_code)

    # If tracer not identified by name, try by radionuclide half-life
    identified_radionuclide = identify_radionuclide_from_halflife(half_life)

    if normalized_tracer and normalized_tracer in PET_PROTOCOLS:
        protocol_info = PET_PROTOCOLS[normalized_tracer]
        result['bids_tracer'] = normalized_tracer
        result['confidence'] = 'high'

        # Find matching protocol based on timing window
        best_match = None
        best_overlap = 0

        for protocol in protocol_info['protocols']:
            proto_start, proto_end = protocol['window']

            # Calculate overlap between actual window and protocol window
            overlap_start = max(window_start_min, proto_start)
            overlap_end = min(window_end_min, proto_end)
            overlap = max(0, overlap_end - overlap_start)

            # Check if imaging window falls within protocol window
            if window_start_min >= proto_start - 10 and window_end_min <= proto_end + 10:
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_match = protocol

        if best_match:
            result['protocol_name'] = best_match['name']
            result['description'] = best_match['description']
            result['bids_tracer'] = best_match['bids_tracer']

            # Determine scan type
            if 'early' in best_match['name'].lower():
                result['scan_type'] = 'early'
            elif 'dynamic' in best_match['name'].lower():
                result['scan_type'] = 'dynamic'
            else:
                result['scan_type'] = 'standard'
        else:
            # No exact match, make educated guess
            result['confidence'] = 'medium'

            if window_start_min < 20:
                result['scan_type'] = 'early'
                result['protocol_name'] = f"{normalized_tracer}_early"
                result['description'] = f"{normalized_tracer} early scan - possibly perfusion-like or dynamic"
            else:
                result['scan_type'] = 'standard'
                result['protocol_name'] = f"{normalized_tracer}_standard"
                result['description'] = f"{normalized_tracer} standard/late scan"

            result['notes'].append(f"Imaging window ({window_start_min:.1f}-{window_end_min:.1f} min) doesn't match typical protocols exactly")

    elif identified_radionuclide:
        # Could identify radionuclide but not specific tracer
        result['confidence'] = 'low'
        result['notes'].append(f"Tracer not identified, but radionuclide appears to be {identified_radionuclide}")

        if window_start_min < 20:
            result['scan_type'] = 'early'
            result['protocol_name'] = f"{identified_radionuclide}_unknown_early"
            result['description'] = f"Unknown {identified_radionuclide} tracer - early scan"
        else:
            result['scan_type'] = 'standard'
            result['protocol_name'] = f"{identified_radionuclide}_unknown_standard"
            result['description'] = f"Unknown {identified_radionuclide} tracer - standard scan"

        result['bids_tracer'] = f"{identified_radionuclide}unknown"

    else:
        # Cannot identify tracer or radionuclide
        result['notes'].append("Could not identify tracer or radionuclide")

        if window_start_min < 20:
            result['scan_type'] = 'early'
            result['protocol_name'] = "unknown_early"
            result['description'] = "Unknown tracer - early scan"
        else:
            result['scan_type'] = 'standard'
            result['protocol_name'] = "unknown_standard"
            result['description'] = "Unknown tracer - standard scan"

        result['bids_tracer'] = "unknown"

    # Add dynamic flag if multiple frames
    if is_dynamic:
        result['notes'].append(f"Dynamic scan with {num_frames} time frames")
        if 'dynamic' not in result['scan_type']:
            result['scan_type'] = f"{result['scan_type']}_dynamic" if result['scan_type'] != 'unknown' else 'dynamic'

    # Generate BIDS filename suggestion
    # Format: sub-<label>_ses-<label>_trc-<tracer>_rec-<label>_pet.nii.gz
    tracer_label = result['bids_tracer'] or 'unknown'

    # Add reconstruction label based on scan type
    if result['scan_type'] == 'early' or 'early' in result['scan_type']:
        rec_label = 'early'
    elif result['scan_type'] == 'standard':
        rec_label = 'standard'
    else:
        rec_label = None

    bids_parts = [f"trc-{tracer_label}"]
    if rec_label:
        bids_parts.append(f"rec-{rec_label}")
    bids_parts.append("pet")

    result['bids_filename_suggestion'] = "sub-<label>_ses-<label>_" + "_".join(bids_parts) + ".nii.gz"

    return result


def get_dicom_files(directory):
    """Recursively find all DICOM files in a directory and group by Series Instance UID."""
    scan_groups = defaultdict(list)

    for root, dirs, files in os.walk(directory):
        for file in files:
            filepath = os.path.join(root, file)
            try:
                # Try to read as DICOM
                ds = pydicom.dcmread(filepath, stop_before_pixels=True, force=True)
                if hasattr(ds, 'Modality') and ds.Modality == 'PT':
                    # Use Series Instance UID (0020,000E) as the unique identifier
                    series_instance_uid = getattr(ds, 'SeriesInstanceUID', 'Unknown')
                    scan_groups[series_instance_uid].append(filepath)
            except (InvalidDicomError, Exception):
                continue

    return scan_groups


def extract_radiopharmaceutical_info(ds):
    """Extract radiopharmaceutical information from DICOM dataset."""
    info = {
        'tracer_name': None,
        'tracer_code': None,
        'radionuclide': None,
        'half_life_seconds': None,
        'injected_dose_bq': None,
        'injection_time': None,
        'start_time': None,
    }

    # Try to get from Radiopharmaceutical Information Sequence (0054,0016)
    if hasattr(ds, 'RadiopharmaceuticalInformationSequence') and ds.RadiopharmaceuticalInformationSequence:
        rp_seq = ds.RadiopharmaceuticalInformationSequence[0]

        # Radiopharmaceutical name
        if hasattr(rp_seq, 'Radiopharmaceutical'):
            info['tracer_name'] = rp_seq.Radiopharmaceutical

        # Radiopharmaceutical Code Sequence for standardized tracer identification
        if hasattr(rp_seq, 'RadiopharmaceuticalCodeSequence') and rp_seq.RadiopharmaceuticalCodeSequence:
            code_seq = rp_seq.RadiopharmaceuticalCodeSequence[0]
            if hasattr(code_seq, 'CodeMeaning'):
                info['tracer_code'] = code_seq.CodeMeaning
            if hasattr(code_seq, 'CodeValue'):
                info['tracer_code_value'] = code_seq.CodeValue

        # Radionuclide information
        if hasattr(rp_seq, 'RadionuclideCodeSequence') and rp_seq.RadionuclideCodeSequence:
            nuc_seq = rp_seq.RadionuclideCodeSequence[0]
            if hasattr(nuc_seq, 'CodeMeaning'):
                info['radionuclide'] = nuc_seq.CodeMeaning

        # Half-life
        if hasattr(rp_seq, 'RadionuclideHalfLife'):
            info['half_life_seconds'] = float(rp_seq.RadionuclideHalfLife)

        # Injected dose
        if hasattr(rp_seq, 'RadionuclideTotalDose'):
            info['injected_dose_bq'] = float(rp_seq.RadionuclideTotalDose)

        # Injection time
        if hasattr(rp_seq, 'RadiopharmaceuticalStartTime'):
            info['injection_time'] = str(rp_seq.RadiopharmaceuticalStartTime)
        elif hasattr(rp_seq, 'RadiopharmaceuticalStartDateTime'):
            info['injection_time'] = str(rp_seq.RadiopharmaceuticalStartDateTime)

    # Acquisition/Series time as fallback for start time
    if hasattr(ds, 'AcquisitionTime'):
        info['start_time'] = str(ds.AcquisitionTime)
    elif hasattr(ds, 'SeriesTime'):
        info['start_time'] = str(ds.SeriesTime)

    return info


def extract_frame_timing(ds):
    """Extract frame timing information from DICOM dataset."""
    frame_info = {
        'frame_reference_time_ms': None,
        'actual_frame_duration_ms': None,
        'frame_start_time_ms': None,
        'frame_end_time_ms': None,
        'number_of_time_slices': None,
    }

    # Frame Reference Time (0054,1300) - time from injection  in ms
    if hasattr(ds, 'FrameReferenceTime'):
        frame_info['frame_reference_time_ms'] = float(ds.FrameReferenceTime)

    # Actual Frame Duration (0018,1242) in ms
    if hasattr(ds, 'ActualFrameDuration'):
        frame_info['actual_frame_duration_ms'] = float(ds.ActualFrameDuration)

    # Calculate frame start and end times
    if frame_info['frame_reference_time_ms'] is not None and frame_info['actual_frame_duration_ms'] is not None:
        # Frame reference time is typically the mid-frame time (not in my case, its beginning)
        frame_info['frame_start_time_ms'] = frame_info['frame_reference_time_ms']
        frame_info['frame_reference_time_ms'] = frame_info['frame_reference_time_ms'] + frame_info['actual_frame_duration_ms'] / 2
        frame_info['frame_end_time_ms'] = frame_info['frame_start_time_ms'] + frame_info['actual_frame_duration_ms']

    # Number of Time Slices (0054,0101)
    if hasattr(ds, 'NumberOfTimeSlices'):
        frame_info['number_of_time_slices'] = int(ds.NumberOfTimeSlices)

    # Try to get from Number of Frames
    if hasattr(ds, 'NumberOfFrames'):
        frame_info['number_of_frames'] = int(ds.NumberOfFrames)

    return frame_info


def analyze_pet_dicoms(dicom_dir):
    """Analyze PET DICOM files and extract tracer and timing information for all scans."""

    print(f"Scanning directory: {dicom_dir}")
    scan_groups = get_dicom_files(dicom_dir)

    if not scan_groups:
        print("No PET DICOM files found.")
        return None

    total_files = sum(len(files) for files in scan_groups.values())
    print(f"Found {total_files} PET DICOM files in {len(scan_groups)} distinct scan(s)")

    all_results = []

    for series_instance_uid, dicom_files in scan_groups.items():
        print(f"\nProcessing scan with Series Instance UID: {series_instance_uid[:50]}..."
              if len(series_instance_uid) > 50 else f"\nProcessing scan with Series Instance UID: {series_instance_uid}")

        # Collect frame information from all files in this scan
        frames = []
        tracer_info = None

        for filepath in dicom_files:
            try:
                ds = pydicom.dcmread(filepath, stop_before_pixels=True)

                # Get tracer info (should be same across all files, so just get once)
                if tracer_info is None:
                    tracer_info = extract_radiopharmaceutical_info(ds)

                # Get frame timing
                frame_timing = extract_frame_timing(ds)

                # Add instance/slice info for sorting
                frame_timing['instance_number'] = getattr(ds, 'InstanceNumber', None)
                frame_timing['slice_location'] = getattr(ds, 'SliceLocation', None)
                frame_timing['image_position'] = getattr(ds, 'ImagePositionPatient', None)
                frame_timing['filepath'] = filepath

                frames.append(frame_timing)

            except Exception as e:
                print(f"Error reading {filepath}: {e}")
                continue

        # Analyze unique frames based on timing (OUTSIDE the for filepath loop)
        unique_frames = {}
        for frame in frames:
            key = (frame['frame_reference_time_ms'], frame['actual_frame_duration_ms'])
            if key not in unique_frames:
                unique_frames[key] = frame

        # Sort frames by reference time (OUTSIDE the for frame loop)
        sorted_frames = sorted(unique_frames.values(),
                               key=lambda x: x['frame_reference_time_ms'] if x['frame_reference_time_ms'] is not None else 0)

        # Guess modality and BIDS naming (OUTSIDE the loops)
        modality_guess = guess_modality_and_bids(tracer_info, sorted_frames)

        scan_result = {
            'series_instance_uid': series_instance_uid,
            'tracer_info': tracer_info,
            'frames': sorted_frames,
            'total_dicom_files': len(dicom_files),
            'modality_guess': modality_guess,
        }
        all_results.append(scan_result)

    return all_results


def format_time_ms_to_min(time_ms):
    """Convert milliseconds to minutes."""
    if time_ms is None:
        return None
    return time_ms / 60000.0


def format_duration_ms_to_sec(duration_ms):
    """Convert milliseconds to seconds."""
    if duration_ms is None:
        return None
    return duration_ms / 1000.0


def print_results(results):
    """Print the analysis results in a readable format."""

    if results is None:
        return

    print("\n" + "=" * 70)
    print("PET DICOM ANALYSIS RESULTS")
    print("=" * 70)

    print("\n" + "#" * 70)
    print("USE WITH CARE! AI generated code with only minimal human review.")
    print("#" * 70)

    for scan_idx, scan_result in enumerate(results, 1):
        series_uid = scan_result['series_instance_uid']
        tracer = scan_result['tracer_info']
        frames = scan_result['frames']

        print(f"\n{'=' * 70}")
        print(f"SCAN {scan_idx} OF {len(results)}")
        print("=" * 70)

        # Scan Identification
        print("\n--- SCAN IDENTIFICATION ---")
        print(f"  Series Instance UID: {series_uid}")

        # Tracer Information
        print("\n--- TRACER INFORMATION ---")
        print(f"  Radiopharmaceutical: {tracer['tracer_name'] or 'Not specified'}")
        if tracer.get('tracer_code'):
            print(f"  Standardized Name:   {tracer['tracer_code']}")
        print(f"  Radionuclide:        {tracer['radionuclide'] or 'Not specified'}")
        if tracer['half_life_seconds']:
            print(f"  Half-life:           {tracer['half_life_seconds']:.1f} seconds ({tracer['half_life_seconds'] / 60:.2f} minutes)")
        if tracer['injected_dose_bq']:
            print(f"  Injected Dose:       {tracer['injected_dose_bq'] / 1e6:.2f} MBq")
        if tracer['injection_time']:
            print(f"  Injection Time:      {tracer['injection_time']}")

        # Frame Timing Information
        print("\n--- IMAGING WINDOW INFORMATION ---")
        print(f"  Total DICOM files:   {scan_result['total_dicom_files']}")
        print(f"  Unique time frames:  {len(frames)}")

        if frames:
            # Calculate overall imaging window
            first_frame = frames[0]
            last_frame = frames[-1]

            window_start_ms = first_frame['frame_start_time_ms']
            window_end_ms = last_frame['frame_end_time_ms']

            if window_start_ms is not None and window_end_ms is not None:
                window_start_min = format_time_ms_to_min(window_start_ms)
                window_end_min = format_time_ms_to_min(window_end_ms)
                total_duration_min = window_end_min - window_start_min

                print(f"\n  Imaging Window:      {window_start_min:.1f} - {window_end_min:.1f} minutes post-injection")
                print(f"  Total Duration:      {total_duration_min:.1f} minutes")

            # Frame details
            print("\n--- FRAME DETAILS ---")
            print(f"  {'Frame':<6} {'Start (min)':<12} {'End (min)':<12} {'Duration (sec)':<15} {'Mid-frame (min)':<15}")
            print("  " + "-" * 60)

            frame_durations = []
            for i, frame in enumerate(frames, 1):
                start_min = format_time_ms_to_min(frame['frame_start_time_ms'])
                end_min = format_time_ms_to_min(frame['frame_end_time_ms'])
                duration_sec = format_duration_ms_to_sec(frame['actual_frame_duration_ms'])
                mid_min = format_time_ms_to_min(frame['frame_reference_time_ms'])

                if duration_sec is not None:
                    frame_durations.append(duration_sec)

                start_str = f"{start_min:.2f}" if start_min is not None else "N/A"
                end_str = f"{end_min:.2f}" if end_min is not None else "N/A"
                dur_str = f"{duration_sec:.1f}" if duration_sec is not None else "N/A"
                mid_str = f"{mid_min:.2f}" if mid_min is not None else "N/A"

                print(f"  {i:<6} {start_str:<12} {end_str:<12} {dur_str:<15} {mid_str:<15}")

            # Summary of frame durations
            if frame_durations:
                unique_durations = list(set(frame_durations))
                unique_durations.sort()
                print("\n--- FRAME DURATION SUMMARY ---")
                if len(unique_durations) == 1:
                    print(f"  All frames have uniform duration: {unique_durations[0]:.1f} seconds ({unique_durations[0] / 60:.2f} minutes)")
                else:
                    print(f"  Frame durations vary:")
                    for dur in unique_durations:
                        count = frame_durations.count(dur)
                        print(f"    {dur:.1f} seconds ({dur / 60:.2f} minutes): {count} frame(s)")

                # Modality/BIDS Guess
        modality = scan_result.get('modality_guess', {})
        if modality:
            print("\n--- MODALITY / BIDS GUESS ---")
            print(f"  Protocol Name:       {modality.get('protocol_name', 'Unknown')}")
            print(f"  Scan Type:           {modality.get('scan_type', 'Unknown')}")
            print(f"  Description:         {modality.get('description', 'N/A')}")
            print(f"  Confidence:          {modality.get('confidence', 'low').upper()}")
            print(f"  BIDS Tracer Label:   {modality.get('bids_tracer', 'unknown')}")
            print(f"  BIDS Filename:       {modality.get('bids_filename_suggestion', 'N/A')}")
            if modality.get('notes'):
                print(f"  Notes:")
                for note in modality['notes']:
                    print(f"    - {note}")

    print("\n" + "=" * 70)


def export_to_json(results, output_path):
    """Export results to a JSON file."""
    import json

    export_data = {
        'README': "USE WITH CARE! AI generated code with only minimal human review.",
        'scans': []
    }

    for scan_result in results:
        tracer_info = scan_result['tracer_info']
        frames = scan_result['frames']

        scan_export = {
            'series_instance_uid': scan_result['series_instance_uid'],
            'tracer': {
                'name': tracer_info['tracer_name'],
                'standardized_name': tracer_info.get('tracer_code'),
                'radionuclide': tracer_info['radionuclide'],
                'half_life_seconds': tracer_info['half_life_seconds'],
                'injected_dose_MBq': tracer_info['injected_dose_bq'] / 1e6 if tracer_info['injected_dose_bq'] else None,
                'injection_time': tracer_info['injection_time'],
            },
            'imaging_window': {},
            'frames': []
        }

        if frames:
            first_frame = frames[0]
            last_frame = frames[-1]

            scan_export['imaging_window'] = {
                'start_minutes': format_time_ms_to_min(first_frame['frame_start_time_ms']),
                'end_minutes': format_time_ms_to_min(last_frame['frame_end_time_ms']),
                'total_frames': len(frames)
            }

            for i, frame in enumerate(frames, 1):
                scan_export['frames'].append({
                    'frame_number': i,
                    'start_minutes': format_time_ms_to_min(frame['frame_start_time_ms']),
                    'end_minutes': format_time_ms_to_min(frame['frame_end_time_ms']),
                    'duration_seconds': format_duration_ms_to_sec(frame['actual_frame_duration_ms']),
                    'mid_frame_minutes': format_time_ms_to_min(frame['frame_reference_time_ms'])
                })

        # Add modality guess
        modality = scan_result.get('modality_guess', {})
        scan_export['modality_guess'] = {
            'protocol_name': modality.get('protocol_name'),
            'scan_type': modality.get('scan_type'),
            'description': modality.get('description'),
            'confidence': modality.get('confidence'),
            'bids_tracer': modality.get('bids_tracer'),
            'bids_filename_suggestion': modality.get('bids_filename_suggestion'),
            'notes': modality.get('notes', []),
        }

        export_data['scans'].append(scan_export)

    with open(output_path, 'w') as f:
        json.dump(export_data, f, indent=2)

    print(f"\nResults exported to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Extract tracer and imaging window information from dynamic PET DICOM files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python pet_dicom_analyzer.py /path/to/dicom/folder
  python pet_dicom_analyzer.py /path/to/dicom/folder -o results.json
        """
    )
    parser.add_argument('dicom_dir', type=str,
                        help='Path to directory containing PET DICOM files')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='Output JSON file path (optional)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')

    args = parser.parse_args()

    if not os.path.isdir(args.dicom_dir):
        print(f"Error: Directory not found: {args.dicom_dir}")
        return 1

    results = analyze_pet_dicoms(args.dicom_dir)

    if results:
        print_results(results)

        if args.output:
            export_to_json(results, args.output)

    return 0


if __name__ == "__main__":
    exit(main())



#what chatgpt thinks is typical for PET:

# # Known tracers by half-life (in seconds)
# TRACER_HALF_LIVES = {
#     # F-18 tracers (half-life ~109.77 minutes = 6586 seconds)
#     "F-18": {
#         "half_life_range": (6400, 6800),
#         "tracers": ["FDG", "FBB", "Florbetaben", "AV45", "Florbetapir", "FMM", "Flutemetamol",
#                     "PI-2620", "MK-6240", "NAV4694", "AV-1451", "Flortaucipir", "FAPI"]
#     },
#     # C-11 tracers (half-life ~20.4 minutes = 1224 seconds)
#     "C-11": {
#         "half_life_range": (1150, 1300),
#         "tracers": ["PIB", "PiB", "Pittsburgh Compound B", "Raclopride", "Methionine", "Choline"]
#     },
#     # Ga-68 tracers (half-life ~67.7 minutes = 4062 seconds)
#     "Ga-68": {
#         "half_life_range": (3900, 4200),
#         "tracers": ["DOTATATE", "DOTATOC", "PSMA", "FAPI"]
#     },
#     # Rb-82 (half-life ~1.27 minutes = 76 seconds)
#     "Rb-82": {
#         "half_life_range": (70, 85),
#         "tracers": ["Rubidium-82", "Rb-82"]
#     },
#     # N-13 (half-life ~9.97 minutes = 598 seconds)
#     "N-13": {
#         "half_life_range": (580, 620),
#         "tracers": ["Ammonia", "NH3"]
#     },
#     # O-15 (half-life ~2.04 minutes = 122 seconds)
#     "O-15": {
#         "half_life_range": (115, 130),
#         "tracers": ["Water", "H2O", "Oxygen"]
#     }
# }
#
# # Common imaging protocols by tracer (approximate windows in minutes)
# COMMON_PROTOCOLS = {
#     "FDG": {"typical_start": 45, "typical_end": 75, "typical_duration": 10, "description": "Static or dynamic glucose metabolism"},
#     "FBB": {"typical_start": 70, "typical_end": 100, "typical_duration": 20, "description": "Amyloid PET (Neuraceq)"},
#     "AV45": {"typical_start": 50, "typical_end": 70, "typical_duration": 20, "description": "Amyloid PET (Amyvid)"},
#     "FMM": {"typical_start": 90, "typical_end": 110, "typical_duration": 20, "description": "Amyloid PET (Vizamyl)"},
#     "NAV4694": {"typical_start": 40, "typical_end": 70, "typical_duration": 30, "description": "Amyloid PET"},
#     "PIB": {"typical_start": 40, "typical_end": 70, "typical_duration": 30, "description": "Amyloid PET (C-11)"},
#     "AV-1451": {"typical_start": 75, "typical_end": 105, "typical_duration": 30, "description": "Tau PET (Tauvid)"},
#     "PI-2620": {"typical_start": 60, "typical_end": 90, "typical_duration": 30, "description": "Tau PET"},
#     "MK-6240": {"typical_start": 90, "typical_end": 110, "typical_duration": 20, "description": "Tau PET"},
# }
