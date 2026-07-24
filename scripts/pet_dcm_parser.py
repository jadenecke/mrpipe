#!/usr/bin/env python3
"""
Script to extract tracer and imaging window information from dynamic PET DICOM files.
Extracts radiopharmaceutical information and frame timing directly from DICOM headers.
"""

import argparse
import os
import re
from collections import defaultdict

import pydicom
from pydicom.errors import InvalidDicomError
from datetime import datetime, timedelta
import numpy as np

def parse_dicom_time(time_str):
    """
    Parse DICOM time string to datetime.time object.
    
    DICOM time formats:
    - (0018,1072) Radiopharmaceutical Start Time: [134500.000000] -> 13:45:00
    - (0008,0031) Series Time: [151502.000] -> 15:15:02
    """
    if time_str is None:
        return None
    
    # Clean the string - remove brackets and whitespace
    time_str = str(time_str).strip().strip('[]')
    
    try:
        # Handle formats with fractional seconds: HHMMSS.ffffff or HHMMSS.fff
        if '.' in time_str:
            main_part, frac_part = time_str.split('.')
        else:
            main_part = time_str
            frac_part = '0'

        # split date off of main part if necessary:
        if len(main_part) > 6:
            #date_part = main_part[:-6]
            main_part = main_part[-6:]

        # Pad main part if needed (some DICOM files may have shortened format)
        main_part = main_part.zfill(6)
        
        hours = int(main_part[0:2])
        minutes = int(main_part[2:4])
        seconds = int(main_part[4:6])
        
        # Convert fractional seconds to microseconds
        frac_part = frac_part.ljust(6, '0')[:6]
        microseconds = int(frac_part)
        
        return datetime(1900, 1, 1, hours, minutes, seconds, microseconds)
    except (ValueError, IndexError):
        return None


def time_to_ms_since_midnight(dt):
    """Convert datetime to milliseconds since midnight."""
    if dt is None:
        return None
    return (dt.hour * 3600 + dt.minute * 60 + dt.second) * 1000 + dt.microsecond / 1000


def ms_to_time_string(ms):
    """Convert milliseconds since midnight to HH:MM:SS.f format."""
    if ms is None:
        return None
    total_seconds = ms / 1000
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:04.1f}"


# =============================================================================
# NORMATIVE TRACER AND PROTOCOL INFORMATION

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
# WARNING: SOME LOGIC IN THE BELOW CODE RELIES ON THAT THERE IS NO OVERLAPPING TRACER WINDOWS, at least for the standard window
PET_PROTOCOLS = {
    # FDG - Glucose metabolism
    "FDG": {
        "radionuclide": "F-18",
        "protocols": [
            {"name": "FDG_early", "window": (0, 15), "bids_suffix": "pet", "bids_tracer": "FDG",
             "description": "FDG early/dynamic - perfusion-like or kinetic modeling"},
            {"name": "FDG_standard", "window": (30, 60), "bids_suffix": "pet", "bids_tracer": "FDG",
             "description": "FDG standard static - glucose metabolism"},
        ]
    },
    # Amyloid tracers
    "FBB": {  # Florbetaben / Neuraceq
        "radionuclide": "F-18",
        "protocols": [
            {"name": "FBB_early", "window": (0, 20), "bids_suffix": "pet", "bids_tracer": "FBB",
             "description": "FBB early - perfusion-like"},
            {"name": "FBB_standard", "window": (90, 110), "bids_suffix": "pet", "bids_tracer": "FBB",
             "description": "FBB standard - amyloid imaging"},
        ]
    },
    # "FLORBETABEN": {  # Alias
    #     "radionuclide": "F-18",
    #     "protocols": [
    #         {"name": "FBB_early", "window": (0, 20), "bids_suffix": "pet", "bids_tracer": "FBB",
    #          "description": "FBB early - perfusion-like"},
    #         {"name": "FBB_standard", "window": (70, 110), "bids_suffix": "pet", "bids_tracer": "FBB",
    #          "description": "FBB standard - amyloid imaging"},
    #     ]
    # },
    "AV45": {  # Florbetapir / Amyvid
        "radionuclide": "F-18",
        "protocols": [
            {"name": "AV45_early", "window": (0, 20), "bids_suffix": "pet", "bids_tracer": "AV45",
             "description": "AV45 early - perfusion-like"},
            {"name": "AV45_standard", "window": (50, 70), "bids_suffix": "pet", "bids_tracer": "AV45",
             "description": "AV45 standard - amyloid imaging"},
        ]
    },
    # "FLORBETAPIR": {  # Alias
    #     "radionuclide": "F-18",
    #     "protocols": [
    #         {"name": "AV45_early", "window": (0, 20), "bids_suffix": "pet", "bids_tracer": "AV45",
    #          "description": "AV45 early - perfusion-like"},
    #         {"name": "AV45_standard", "window": (50, 70), "bids_suffix": "pet", "bids_tracer": "AV45",
    #          "description": "AV45 standard - amyloid imaging"},
    #     ]
    # },
    "FMM": {  # Flutemetamol / Vizamyl
        "radionuclide": "F-18",
        "protocols": [
            {"name": "FMM_early", "window": (0, 20), "bids_suffix": "pet", "bids_tracer": "FMM",
             "description": "FMM early - perfusion-like"},
            {"name": "FMM_standard", "window": (90, 110), "bids_suffix": "pet", "bids_tracer": "FMM",
             "description": "FMM standard - amyloid imaging"},
        ]
    },
    # "FLUTEMETAMOL": {  # Alias
    #     "radionuclide": "F-18",
    #     "protocols": [
    #         {"name": "FMM_early", "window": (0, 20), "bids_suffix": "pet", "bids_tracer": "FMM",
    #          "description": "FMM early - perfusion-like"},
    #         {"name": "FMM_standard", "window": (85, 115), "bids_suffix": "pet", "bids_tracer": "FMM",
    #          "description": "FMM standard - amyloid imaging"},
    #     ]
    # },
    "NAV4694": {  # NAV4694 / AZD4694
        "radionuclide": "F-18",
        "protocols": [
            {"name": "NAV4694_early", "window": (0, 20), "bids_suffix": "pet", "bids_tracer": "NAV4694",
             "description": "NAV4694 early - perfusion-like"},
            {"name": "NAV4694_standard", "window": (50, 70), "bids_suffix": "pet", "bids_tracer": "NAV4694",
             "description": "NAV4694 standard - amyloid imaging"},
        ]
    },
    "PIB": {  # Pittsburgh Compound B (C-11)
        "radionuclide": "C-11",
        "protocols": [
            {"name": "PIB_early", "window": (0, 15), "bids_suffix": "pet", "bids_tracer": "PIB",
             "description": "PIB early - perfusion-like"},
            {"name": "PIB_standard", "window": (50, 70), "bids_suffix": "pet", "bids_tracer": "PIB",
             "description": "PIB standard - amyloid imaging"},
        ]
    },
    # Tau tracers
    "AV1451": {  # Flortaucipir / Tauvid
        "radionuclide": "F-18",
        "protocols": [
            {"name": "AV1451_early", "window": (0, 20), "bids_suffix": "pet", "bids_tracer": "AV1451",
             "description": "AV1451 early - perfusion-like"},
            {"name": "AV1451_standard", "window": (80, 100), "bids_suffix": "pet", "bids_tracer": "AV1451",
             "description": "AV1451 standard - tau imaging"},
        ]
    },
    # "FLORTAUCIPIR": {  # Alias
    #     "radionuclide": "F-18",
    #     "protocols": [
    #         {"name": "AV1451_early", "window": (0, 20), "bids_suffix": "pet", "bids_tracer": "AV1451",
    #          "description": "AV1451 early - perfusion-like"},
    #         {"name": "AV1451_standard", "window": (75, 105), "bids_suffix": "pet", "bids_tracer": "AV1451",
    #          "description": "AV1451 standard - tau imaging"},
    #     ]
    # },
    "PI2620": {  # PI-2620
        "radionuclide": "F-18",
        "protocols": [
            {"name": "PI2620_early", "window": (0, 20), "bids_suffix": "pet", "bids_tracer": "PI2620",
             "description": "PI-2620 early - perfusion-like"},
            {"name": "PI2620_standard", "window": (45, 75), "bids_suffix": "pet", "bids_tracer": "PI2620",
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
    "[18F] NAV-4694": "NAV4694",
    "[18F]NAV-4694": "NAV4694",
    "M62": "MK6240",
    "P26": "PI2620",
    "T80": "AV1451",
    "T807": "AV1451",
    "BTA": "PIB"
}


# Regex patterns for detecting tracer mentions in free-text DICOM fields
# (StudyDescription / SeriesDescription / ProtocolName). Patterns use word
# boundaries and tolerate common separators (space, dash, underscore) between
# letters and digits (e.g. "AV45", "AV-45", "AV_45"). Short abbreviations that
# would cause false positives in free text (e.g. "M62", "P26", "T80") are
# deliberately omitted here — they are only trusted from the standardized
# Radiopharmaceutical fields.
TRACER_FREETEXT_PATTERNS = {
    "FDG":      [r"\bFDG\b", r"FLUORODEOXYGLUCOSE", r"FLUORO[\W_]?DEOXY[\W_]?GLUCOSE"],
    "FBB":      [r"\bFBB\b", r"FLORBETABEN", r"NEURACEQ"],
    "AV45":     [r"\bAV[\W_]?45\b", r"FLORBETAPIR", r"AMYVID"],
    "FMM":      [r"\bFMM\b", r"FLUTEMETAMOL", r"VIZAMYL"],
    "PIB":      [r"\bPIB\b", r"PITTSBURGH", r"COMPOUND[\W_]?B\b", r"BTA"],
    "AV1451":   [r"\bAV[\W_]?1451\b", r"\bT807\b", r"FLORTAUCIPIR", r"TAUVID"],
    "PI2620":   [r"\bPI[\W_]?2620\b"],
    "MK6240":   [r"\bMK[\W_]?6240\b"],
    "NAV4694":  [r"\bNAV[\W_]?4694\b", r"\bAZD[\W_]?4694\b"],
    "PSMA":     [r"\bPSMA\b"],
    "DOTATATE": [r"\bDOTATATE\b", r"\bDOTATOC\b"],
    "NH3":      [r"\bNH3\b", r"\bAMMONIA\b"],
    "H2O":      [r"\bH2O\b", r"\bWATER\b"],
    "RB82":     [r"\bRB[\W_]?82\b", r"\bRUBIDIUM\b"],
}


def detect_tracers_from_text(text):
    """Detect PET tracer(s) mentioned in a free-text field.

    Returns a set of tracer keys (matching PET_PROTOCOLS keys). Because these
    fields are unstandardized, multiple keys may be returned when the text
    contains several tracer hints (e.g. a scanner-wide protocol name that lists
    a menu of tracers).
    """
    if not text:
        return set()
    normalized = str(text).upper()
    hits = set()
    for tracer_key, patterns in TRACER_FREETEXT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, normalized):
                hits.add(tracer_key)
                break
    return hits


# When a candidate's free-text timing fit outperforms the primary by at least
# this margin AND clears the absolute floor, the primary tracer is overridden.
TIMING_OVERRIDE_MARGIN = 0.15
TIMING_OVERRIDE_MIN_SCORE = 0.30


def score_tracer_timing_fit(tracer_key, window_start_min, window_end_min):
    """Score how well a candidate tracer's known protocol windows match a given
    imaging window (in minutes post-injection).

    Score per protocol = overlap / max(scan_duration, protocol_duration).
    It's symmetric and penalizes both under- and over-shooting the expected
    window: a 90-110 min scan against FBB_standard (90-110) scores 1.0, against
    FDG_standard (40-60) scores 0.

    Returns:
      - score: best protocol score (0.0 - 1.0)
      - best_protocol: dict of the best matching protocol, or None
      - per_protocol: list of {name, window, score} for diagnostics
    """
    protocols_info = PET_PROTOCOLS.get(tracer_key)
    if not protocols_info:
        return {'score': 0.0, 'best_protocol': None, 'per_protocol': []}

    window_duration = max(0.0, window_end_min - window_start_min)
    if window_duration == 0:
        return {'score': 0.0, 'best_protocol': None, 'per_protocol': []}

    best_score = 0.0
    best_proto = None
    per_protocol = []
    for proto in protocols_info['protocols']:
        proto_start, proto_end = proto['window']
        proto_duration = proto_end - proto_start
        if proto_duration <= 0:
            continue
        overlap = max(0.0, min(window_end_min, proto_end) - max(window_start_min, proto_start))
        score = overlap / max(window_duration, proto_duration)
        per_protocol.append({
            'name': proto['name'],
            'window_min': [proto_start, proto_end],
            'score': round(score, 3),
        })
        if score > best_score:
            best_score = score
            best_proto = proto
    return {'score': best_score, 'best_protocol': best_proto, 'per_protocol': per_protocol}


def _extract_scan_window_min(frames):
    """Return (start_min, end_min) of the imaging window in minutes post-injection.
    Prefers the corrected times when available, falls back to raw frame times.
    Returns (None, None) if frames don't have usable timing.
    """
    if not frames:
        return None, None
    first, last = frames[0], frames[-1]
    start_ms = first.get('frame_start_time_ms_WithCorrections')
    if start_ms is None:
        start_ms = first.get('frame_start_time_ms')
    end_ms = last.get('frame_end_time_ms_WithCorrections')
    if end_ms is None:
        end_ms = last.get('frame_end_time_ms')
    if start_ms is None or end_ms is None:
        return None, None
    return start_ms / 60000.0, end_ms / 60000.0

def synthesize_frame_times_if_missing(frame, tracer_info, nFrames):
    """
    If no individual frame timing exists, but injection_time and acquisition_time
    are available, synthesize 5-minute frames (only when delay >= 20 min).
    Adds a strong warning flag into tracer_info['warnings'].
    """
    #
    # inj =
    # acq =
    #
    # if inj is None or acq is None:
    #     print("Warning: Was trying to synthesize frame times, but injection_time or acquisition_time is missing. ")
    #     return frame  # nothing to do
    #
    # inj_dt = parse_dicom_time(inj)
    # acq_dt = parse_dicom_time(acq)
    #
    # if inj_dt is None or acq_dt is None:
    #     print("Warning: Was trying to synthesize frame times, but injection_time or acquisition_time is invalid - datetime invalid")
    #     return frame

    inj_ms = tracer_info.get('injection_time_ms')
    acq_ms = tracer_info.get('series_time_ms')

    print(inj_ms)
    print(acq_ms)

    if inj_ms is None or acq_ms is None:
        print("Warning: Was trying to synthesize frame times, but injection_time or acquisition_time is invalid - time since midnight is None. ")
        return frame

    delay_ms = acq_ms - inj_ms
    delay_min = (acq_ms - inj_ms) / 60000.0

    if delay_min < 20:
        print(f"Warning: Was trying to synthesize frame times, but delay is less than 20 min: {delay_min} min. ")
        return frame

    # --- Synthesize 5-minute frames ---
    synthetic_frames = {}
    frame_duration_ms = 5 * 60000  # 5 minutes

    # Use acquisition time as start of first frame
    start_ms = acq_ms

    for i in range(nFrames):
        f_new = frame.copy()
        f_new['frame_start_time_ms'] = i * frame_duration_ms
        f_new['frame_end_time_ms'] = (i+1) * frame_duration_ms
        f_new['actual_frame_duration_ms'] = frame_duration_ms
        f_new['frame_reference_time_ms'] = (i * frame_duration_ms) + frame_duration_ms // 2
        # Calculate actual clock times if injection time is available
        if tracer_info and tracer_info.get('injection_time_ms') is not None:
            injection_time_ms = tracer_info['injection_time_ms']

            # Calculate clock times by adding frame offset to injection time
            start_clock_ms = injection_time_ms + f_new['frame_start_time_ms']
            mid_clock_ms = injection_time_ms + f_new['frame_reference_time_ms']
            end_clock_ms = injection_time_ms + f_new['frame_end_time_ms']

            f_new['calculated_start_time'] = ms_to_time_string(start_clock_ms)
            f_new['calculated_mid_time'] = ms_to_time_string(mid_clock_ms)
            f_new['calculated_end_time'] = ms_to_time_string(end_clock_ms)

        # Mark synthetic timing
        f_new['synthetic_timing'] = True
        key = (f_new['frame_reference_time_ms'], f_new['actual_frame_duration_ms'])
        synthetic_frames[key] = f_new
    return synthetic_frames



def analyze_tracer_agreement(tracer_info, frames=None):
    """Cross-check the primary tracer (from RadiopharmaceuticalInformationSequence)
    against tracer hints found in free-text description fields, and — when
    frame timing is available — score each candidate against its known protocol
    windows to pick a final ``selected_tracer``.

    Returns a dict with:
      - primary_tracer: normalized tracer key from the standardized DICOM fields
      - freetext_tracers: sorted list of distinct tracer keys detected across
        StudyDescription / SeriesDescription / ProtocolName
      - freetext_tracers_by_field: per-field detection details
      - agreement: one of 'agree', 'agree_ambiguous', 'disagree',
                   'no_primary_tracer', 'no_freetext_hint'
      - disagreement: bool flag — True only when a primary tracer is present,
        freetext hints exist, and the primary tracer is not among them.
      - timing_scores: {tracer_key: {score, best_protocol, per_protocol}} for
        every candidate (primary + freetext hints), when frame timing is usable
      - scan_window_minutes: (start, end) window used for scoring, or None
      - selected_tracer: tracer key downstream code should treat as authoritative;
        equals primary except when timing evidence overrides
      - selection_reason: short explanation of how selected_tracer was chosen
      - notes: human-readable notes describing the outcome
    """
    primary = normalize_tracer_name(tracer_info.get('tracer_name')) \
              or normalize_tracer_name(tracer_info.get('tracer_code'))

    freetext_sources = {
        'study_description': tracer_info.get('study_description'),
        'series_description': tracer_info.get('series_description'),
        'protocol_name': tracer_info.get('protocol_name'),
    }
    per_field = {name: sorted(detect_tracers_from_text(txt))
                 for name, txt in freetext_sources.items()}
    all_freetext = set()
    for hits in per_field.values():
        all_freetext.update(hits)

    # Assemble candidate set (primary + freetext hints), preserving primary first.
    candidates = []
    if primary:
        candidates.append(primary)
    for k in sorted(all_freetext):
        if k not in candidates:
            candidates.append(k)

    # Score each candidate against the corrected frame window.
    w_start_min, w_end_min = _extract_scan_window_min(frames)
    timing_scores = {}
    if w_start_min is not None and w_end_min is not None:
        for cand in candidates:
            timing_scores[cand] = score_tracer_timing_fit(cand, w_start_min, w_end_min)

    result = {
        'primary_tracer': primary,
        'freetext_tracers': sorted(all_freetext),
        'freetext_tracers_by_field': per_field,
        'agreement': None,
        'disagreement': False,
        'timing_scores': timing_scores,
        'scan_window_minutes': [round(w_start_min, 2), round(w_end_min, 2)]
            if w_start_min is not None else None,
        'selected_tracer': primary,
        'selection_reason': None,
        'notes': [],
    }

    if not all_freetext:
        result['agreement'] = 'no_freetext_hint'
        result['notes'].append(
            "No tracer hints found in StudyDescription / SeriesDescription / ProtocolName."
        )
    elif primary is None:
        result['agreement'] = 'no_primary_tracer'
        result['notes'].append(
            f"No primary tracer identified from DICOM Radiopharmaceutical fields; "
            f"free-text suggests: {sorted(all_freetext)}."
        )
    elif primary in all_freetext:
        others = sorted(all_freetext - {primary})
        if others:
            result['agreement'] = 'agree_ambiguous'
            result['notes'].append(
                f"Primary tracer '{primary}' matches a free-text hint, but other tracer "
                f"names were also mentioned: {others}."
            )
        else:
            result['agreement'] = 'agree'
    else:
        result['agreement'] = 'disagree'
        result['disagreement'] = True
        result['notes'].append(
            f"DISAGREEMENT: primary tracer is '{primary}' but free-text hints suggest "
            f"{sorted(all_freetext)}. Frame timing used to pick the more likely tracer."
        )

    # --- Selection: pick the best-fitting candidate when timing evidence exists ---
    if timing_scores:
        ranked = sorted(timing_scores.items(), key=lambda kv: kv[1]['score'], reverse=True)
        best_key, best_info = ranked[0]
        best_score = best_info['score']
        primary_score = timing_scores.get(primary, {}).get('score', 0.0) if primary else 0.0

        if primary is None:
            if best_score > 0:
                result['selected_tracer'] = best_key
                result['selection_reason'] = (
                    f"No primary tracer; selecting free-text candidate '{best_key}' with "
                    f"best timing fit (score {best_score:.2f})."
                )
            elif candidates:
                result['selected_tracer'] = candidates[0]
                result['selection_reason'] = (
                    f"No primary tracer and no candidate protocol matched the frame window; "
                    f"defaulting to first free-text candidate '{candidates[0]}'."
                )
        elif best_key == primary:
            result['selection_reason'] = (
                f"Primary tracer '{primary}' has the best timing fit "
                f"(score {primary_score:.2f}); keeping primary."
            )
        elif (best_score >= TIMING_OVERRIDE_MIN_SCORE
              and best_score >= primary_score + TIMING_OVERRIDE_MARGIN):
            result['selected_tracer'] = best_key
            result['selection_reason'] = (
                f"Overriding primary '{primary}' (timing fit {primary_score:.2f}) with "
                f"free-text candidate '{best_key}' (timing fit {best_score:.2f}) — "
                f"substantially better match to the frame window "
                f"{result['scan_window_minutes']} min."
            )
            result['notes'].append(result['selection_reason'])
        else:
            result['selection_reason'] = (
                f"Primary tracer '{primary}' retained (timing fit {primary_score:.2f}); "
                f"best alternative '{best_key}' scored {best_score:.2f}, below the override "
                f"threshold (>= {TIMING_OVERRIDE_MIN_SCORE:.2f} absolute and "
                f"+{TIMING_OVERRIDE_MARGIN:.2f} over primary)."
            )
    elif candidates:
        # No timing available — cannot arbitrate; keep primary if present, else first freetext.
        if primary is None:
            result['selected_tracer'] = candidates[0]
            result['selection_reason'] = (
                f"No frame timing available for arbitration; defaulting to first candidate "
                f"'{candidates[0]}'."
            )
        else:
            result['selection_reason'] = (
                f"No frame timing available for arbitration; keeping primary '{primary}'."
            )

    return result


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


def guess_modality_and_bids(tracer_info, frames, preferred_tracer=None):
    """
    Guess the modality/protocol and BIDS naming based on tracer and frame timing.

    If ``preferred_tracer`` is provided (typically the ``selected_tracer`` from
    :func:`analyze_tracer_agreement`), that key is used instead of the tracer
    derived from the standardized Radiopharmaceutical fields — enabling BIDS
    output to reflect a free-text override when frame timing disagreed with
    the DICOM label.

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
        'tracer_end_expected': None,
        'tracer_end_expected': None,
    }

    if not frames:
        result['notes'].append("No frame timing information available")
        return result

    # Get imaging window in minutes
    first_frame = frames[0]
    last_frame = frames[-1]

    window_start_ms = first_frame.get('frame_start_time_ms_WithCorrections')
    window_end_ms = last_frame.get('frame_end_time_ms_WithCorrections')

    if window_start_ms is None or window_end_ms is None:
        result['notes'].append("Incomplete frame timing information")
        return result

    window_start_min = window_start_ms / 60000.0
    window_end_min = window_end_ms / 60000.0
    window_duration_min = window_end_min - window_start_min

    # If frame duration is ~5 minutes, round window edges to nearest minute
    # (helps clean up slight timing jitter in dynamic protocols).
    if frames and frames[0].get('actual_frame_duration_ms') is not None:
        frame_dur_min = frames[0]['actual_frame_duration_ms'] / 60000.0
        if 4.5 <= frame_dur_min <= 5.5:
            window_start_min = round(window_start_min)
            window_end_min = round(window_end_min)
            window_duration_min = window_end_min - window_start_min

    # Determine if this is likely a dynamic or static scan
    num_frames = len(frames)
    is_dynamic = num_frames > 1

    # Try to identify tracer
    tracer_name = tracer_info.get('tracer_name')
    tracer_code = tracer_info.get('tracer_code')
    half_life = tracer_info.get('half_life_seconds')

    # Normalize tracer name — if the caller provided a preferred_tracer (e.g. the
    # frame-timing-arbitrated winner from analyze_tracer_agreement), use it
    # instead of the DICOM label. Note the override so downstream sees why the
    # BIDS output diverges from the Radiopharmaceutical field.
    dicom_derived_tracer = normalize_tracer_name(tracer_name) or normalize_tracer_name(tracer_code)
    if preferred_tracer and preferred_tracer in PET_PROTOCOLS:
        normalized_tracer = preferred_tracer
        if dicom_derived_tracer and dicom_derived_tracer != preferred_tracer:
            result['notes'].append(
                f"Tracer overridden from DICOM label '{dicom_derived_tracer}' to "
                f"'{preferred_tracer}' based on free-text hints + frame-timing fit."
            )
    else:
        normalized_tracer = dicom_derived_tracer

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

        # Flag whether the current tracer has a perfectly fitting window
        window_fits_perfectly = False
        if best_match is not None:
            proto_start, proto_end = best_match['window']
            if abs(window_start_min - proto_start) < 1e-6 and abs(window_end_min - proto_end) < 1e-6:
                window_fits_perfectly = True
            else:
                result['confidence'] = 'medium'
            result['tracer_begin_expected'] = proto_start
            result['tracer_end_expected'] = proto_end

        # If not fully dynamic and window does not perfectly fit this tracer,
        # search for another tracer whose protocol window matches exactly.
        result['alternative_tracer_bids'] = None
        result['window_fits_protocol'] = window_fits_perfectly


        if result['scan_type'] != 'dynamic_full' and not window_fits_perfectly:
            for other_tracer, other_info in PET_PROTOCOLS.items():
                if other_tracer == normalized_tracer:
                    continue
                for proto in other_info['protocols']:
                    o_start, o_end = proto['window']
                    if abs(window_start_min - o_start) < 1e-6 and abs(window_end_min - o_end) < 1e-6:
                        result['alternative_tracer_bids'] = proto.get('bids_tracer', other_tracer)
                        result['notes'].append(
                            f"Imaging window {window_start_min:.2f}-{window_end_min:.2f} min "
                            f"matches protocol '{proto['name']}' of tracer '{other_tracer}' "
                            f"perfectly; current tracer window does not."
                        )
                        break
                if result['alternative_tracer_bids'] is not None:
                    break


        # Detect fully dynamic scan: starts near 0 and reaches standard window (if defined)
        standard_windows = [
            p['window'] for p in protocol_info['protocols']
            if 'standard' in p['name'].lower()
        ]
        if standard_windows:
            standard_start_min = min(w[0] for w in standard_windows)
            if window_start_min <= 5 and window_end_min >= (standard_start_min - 5):
                result['scan_type'] = 'dynamic_full'
                result['protocol_name'] = f"{normalized_tracer}_dynamic_full"
                result['description'] = f"{normalized_tracer} fully dynamic scan spanning early and standard window"
                result['notes'].append("Imaging window starts at ~0 and reaches standard window; treating as fully dynamic scan.")
                best_match = None

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
        elif result['scan_type'] == 'unknown':
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

            result['notes'].append(f"Imaging window ({window_start_min:.2f}-{window_end_min:.2f} min) doesn't match typical protocols exactly")

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
        'series_description': None,
        'protocol_name': None,
        'study_description': None,
        'manufacturer': None,
        'model_name': None,
        'half_life_seconds': None,
        'injected_dose_bq': None,
        'injection_time': None,
        'injection_time_ms': None,
        'start_time': None,
        'series_time': None,
        'series_time_ms': None,
        'study_id': None,
        'patient_name': None,
        'patient_id': None,
        'study_date': None,
        'series_date': None,
        'acquisition_date': None,
        'content_date': None,
        'study_time': None,
        'deidentification_method': None,
        'clinical_trial_series_id': None,
        'injection_to_scan_diff_ms_raw': None,
        'warnings': [],
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

        # Injection time (0018,1072) - Radiopharmaceutical Start Time
        if hasattr(rp_seq, 'RadiopharmaceuticalStartTime'):
            info['injection_time'] = str(rp_seq.RadiopharmaceuticalStartTime)
            parsed_time = parse_dicom_time(info['injection_time'])
            info['injection_time_ms'] = time_to_ms_since_midnight(parsed_time)
        elif hasattr(rp_seq, 'RadiopharmaceuticalStartDateTime'):
            info['injection_time'] = str(rp_seq.RadiopharmaceuticalStartDateTime)

    # Series Time (0008,0031)
    if hasattr(ds, 'SeriesTime'):
        info['series_time'] = str(ds.SeriesTime)
        parsed_time = parse_dicom_time(info['series_time'])
        info['series_time_ms'] = time_to_ms_since_midnight(parsed_time)

    # Acquisition/Series time as fallback for start time
    if hasattr(ds, 'AcquisitionTime'):
        info['start_time'] = str(ds.AcquisitionTime)
    elif hasattr(ds, 'SeriesTime'):
        info['start_time'] = str(ds.SeriesTime)

    if hasattr(ds, 'SeriesDescription'):
        info['series_description'] = str(ds.SeriesDescription)

    if hasattr(ds, 'ProtocolName'):
        info['protocol_name'] = str(ds.ProtocolName)

    if hasattr(ds, 'StudyDescription'):
        info['study_description'] = str(ds.StudyDescription)

    if hasattr(ds, 'Manufacturer'):
        info['manufacturer'] = str(ds.Manufacturer)

    if hasattr(ds, 'ManufacturerModelName'):
        info['model_name'] = str(ds.ManufacturerModelName)

    # New fields
    if hasattr(ds, 'StudyID'):
        info['study_id'] = str(ds.StudyID)

    if hasattr(ds, 'PatientName'):
        info['patient_name'] = str(ds.PatientName)

    if hasattr(ds, 'PatientID'):
        info['patient_id'] = str(ds.PatientID)

    if hasattr(ds, 'StudyDate'):
        info['study_date'] = str(ds.StudyDate)

    if hasattr(ds, 'SeriesDate'):
        info['series_date'] = str(ds.SeriesDate)

    if hasattr(ds, 'AcquisitionDate'):
        info['acquisition_date'] = str(ds.AcquisitionDate)

    if hasattr(ds, 'ContentDate'):
        info['content_date'] = str(ds.ContentDate)

    if hasattr(ds, 'StudyTime'):
        info['study_time'] = str(ds.StudyTime)

    if hasattr(ds, 'DeidentificationMethod'):
        info['deidentification_method'] = str(ds.DeidentificationMethod)

    if hasattr(ds, 'ClinicalTrialSeriesID'):
        info['clinical_trial_series_id'] = str(ds.ClinicalTrialSeriesID)

    return info


def extract_frame_timing(ds, tracer_info=None):
    """Extract frame timing information from DICOM dataset."""
    frame_info = {
        'frame_reference_time_ms': None,
        'actual_frame_duration_ms': None,
        'frame_start_time_ms': None,
        'frame_end_time_ms': None,
        'number_of_time_slices': None,
        'calculated_start_time': None,
        'calculated_mid_time': None,
        'calculated_end_time': None,
        'frame_start_time_ms_WithCorrections': None,
        'frame_end_time_ms_WithCorrections': None,
        'calculated_start_time_WithCorrections': None,
        'calculated_mid_time_WithCorrections': None,
        'calculated_end_time_WithCorrections': None
    }



    # Frame Reference Time (0054,1300) - time from injection in ms
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

        # Calculate actual clock times if injection time is available
        if tracer_info and tracer_info.get('injection_time_ms') is not None:
            injection_time_ms = tracer_info['injection_time_ms']
            
            # Calculate clock times by adding frame offset to injection time
            start_clock_ms = injection_time_ms + frame_info['frame_start_time_ms']
            mid_clock_ms = injection_time_ms + frame_info['frame_reference_time_ms']
            end_clock_ms = injection_time_ms + frame_info['frame_end_time_ms']

            frame_info['calculated_start_time'] = ms_to_time_string(start_clock_ms)
            frame_info['calculated_mid_time'] = ms_to_time_string(mid_clock_ms)
            frame_info['calculated_end_time'] = ms_to_time_string(end_clock_ms)

    # Number of Time Slices (0054,0101)
    if hasattr(ds, 'NumberOfTimeSlices'):
        frame_info['number_of_time_slices'] = int(ds.NumberOfTimeSlices)

    # Try to get from Number of Frames
    if hasattr(ds, 'NumberOfFrames'):
        frame_info['number_of_frames'] = int(ds.NumberOfFrames)

    return frame_info


def analyze_pet_dicoms(dicom_dirs):
    """Analyze PET DICOM files and extract tracer and timing information for all scans."""
    scan_groups = defaultdict(list)
    for dir in dicom_dirs:
        print(f"Scanning directory: {dir}")
        scan_groups = scan_groups | get_dicom_files(dir)


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

                # Get frame timing (pass tracer_info for clock time calculation)
                frame_timing = extract_frame_timing(ds, tracer_info)

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

        first_frame = next(iter(unique_frames.values()), None)
        if not first_frame:
            Exception(f"Error: No frames found for dcm files, must be corrupted: {dicom_files}")
        if len(unique_frames.keys()) == 1:
            if first_frame and first_frame['number_of_time_slices'] > 1:
                print(f"Warning: No frame timings found, however dcm header suggest {first_frame['number_of_time_slices']} frames. Trying to reconstruct from injection time an acquisition time.")
                # Add strong warning
                tracer_info['warnings'].append(
                    "NO PER-FRAME TIMING IN DICOM — SYNTHETIC 5-MINUTE FRAMES GENERATED "
                    "FROM INJECTION/ACQUISITION TIMES ONLY. USE EXTREME CAUTION."
                )
                unique_frames = synthesize_frame_times_if_missing(first_frame, tracer_info, first_frame['number_of_time_slices'])
                print(unique_frames)

        if len(unique_frames.keys()) != first_frame['number_of_time_slices']:
            print(len(unique_frames.keys()))
            print(first_frame['number_of_time_slices'])
            print(f"Warning: Number of frames collected differs from number of suggested frames! This warrants inspection and implies an error of the recorded frame times: {first_frame['filepath']}")

        # Sort frames by reference time (OUTSIDE the for frame loop)
        sorted_frames = sorted(unique_frames.values(),
                               key=lambda x: x['frame_reference_time_ms'] if x['frame_reference_time_ms'] is not None else 0)

        #correct frame timings:
        if tracer_info and tracer_info.get('series_time_ms') is not None and tracer_info.get('injection_time_ms') is not None:
            first_frame = sorted_frames[0]
            applyOffsetTime = False
            if first_frame['frame_start_time_ms'] % first_frame['actual_frame_duration_ms']  !=  0:
                applyOffsetTime = True
                print(f"! Found start frame time to be not multiple of reference frame time. Assuming time is mid-frame time.")

            tracer_info['injection_to_scan_diff_ms_raw'] = tracer_info['series_time_ms'] - tracer_info['injection_time_ms']
            time_diff_ms = np.round(tracer_info['injection_to_scan_diff_ms_raw'] / first_frame['actual_frame_duration_ms']) * first_frame['actual_frame_duration_ms']
            # round raw time to the nearest multiple of starting frame time to adjust for slight inacuracies.
            # also set to 0 if it is less then 10 minutes.
            if time_diff_ms < 300000 and time_diff_ms >= 0:
                time_diff_ms = 0
                tracer_info['warnings'].append("Injection-to-Scan time is < 5 min, assuming fully dynamic scan and setting correction to 0.")
            elif tracer_info['injection_to_scan_diff_ms_raw'] != time_diff_ms:
                tracer_info['warnings'].append("Injection-to-Scan time is not multiple of first frame duration. Rounding to nearest multiple of first frame duration (assuming that this is the intended scanning time frame).")


            for frame in sorted_frames:
                if applyOffsetTime:
                    offsetTime = frame['frame_start_time_ms'] % frame['actual_frame_duration_ms']
                else:
                    offsetTime = 0

                # If frame duration is ~5 minutes, round window edges to nearest minute
                # (helps clean up slight timing jitter in dynamic protocols).
                if frame.get('actual_frame_duration_ms') is not None:
                    frame_dur_min = sorted_frames[0]['actual_frame_duration_ms'] / 60000.0
                    if 4.5 <= frame_dur_min <= 5.5:
                        frame['frame_start_time_ms'] = round(frame['frame_start_time_ms'] / 60000.0) * 60000
                        frame['frame_end_time_ms'] = round(frame['frame_end_time_ms'] / 60000.0) * 60000


                frame['offset_correction_time'] = offsetTime
                frame['frame_start_time_ms_WithCorrections'] = frame['frame_start_time_ms'] + time_diff_ms - offsetTime
                frame['frame_mid_time_ms_WithCorrections'] = frame['frame_reference_time_ms'] + time_diff_ms - offsetTime
                frame['frame_end_time_ms_WithCorrections'] = frame['frame_end_time_ms'] + time_diff_ms - offsetTime
                frame['calculated_start_clock_WithCorrections'] = tracer_info['injection_time_ms'] + frame['frame_start_time_ms_WithCorrections']
                frame['calculated_mid_clock_WithCorrections'] = tracer_info['injection_time_ms'] + frame['frame_mid_time_ms_WithCorrections']
                frame['calculated_end_clock_WithCorrections'] = tracer_info['injection_time_ms'] + frame['frame_end_time_ms_WithCorrections']



        # Cross-check the standardized tracer label against free-text hints in
        # StudyDescription / SeriesDescription / ProtocolName. Uses the corrected
        # frame window (falls back to raw times) to score candidate tracers and
        # select the best-fitting one.
        tracer_agreement = analyze_tracer_agreement(tracer_info, sorted_frames)
        if tracer_agreement['disagreement']:
            selected = tracer_agreement.get('selected_tracer')
            primary = tracer_agreement.get('primary_tracer')
            if selected and selected != primary:
                tracer_info['warnings'].append(
                    f"Tracer label overridden: Radiopharmaceutical field says '{primary}' but "
                    f"free-text hints {tracer_agreement['freetext_tracers']} + frame-timing fit "
                    f"prefer '{selected}'. BIDS output uses '{selected}'."
                )
            else:
                tracer_info['warnings'].append(
                    f"Tracer label disagreement (unresolved): Radiopharmaceutical field says "
                    f"'{primary}' but free-text hints suggest {tracer_agreement['freetext_tracers']}. "
                    f"Frame timing was insufficient to arbitrate — keeping primary."
                )

        # Guess modality and BIDS naming, honoring the arbitrated tracer selection.
        modality_guess = guess_modality_and_bids(
            tracer_info, sorted_frames,
            preferred_tracer=tracer_agreement.get('selected_tracer'),
        )

        scan_result = {
            'series_instance_uid': series_instance_uid,
            'dicom_path': os.path.dirname(dicom_files[0]),
            'tracer_info': tracer_info,
            'frames': sorted_frames,
            'total_dicom_files': len(dicom_files),
            'modality_guess': modality_guess,
            'tracer_agreement': tracer_agreement,
        }
        all_results.append(scan_result)

    return all_results


def format_time_ms_to_min(time_ms):
    """Convert milliseconds to minutes, rounded to 1 decimal place."""
    if time_ms is None:
        return None
    return round(time_ms / 60000.0, 2)


def format_duration_ms_to_sec(duration_ms):
    """Convert milliseconds to seconds, rounded to 1 decimal place."""
    if duration_ms is None:
        return None
    return round(duration_ms / 1000.0, 1)


def print_results(results):
    """Print the analysis results in a readable format."""

    if results is None:
        return

    print("\n" + "=" * 70)
    print("PET DICOM ANALYSIS RESULTS")
    print("=" * 70)

    print("\n" + "#" * 70)
    print("USE WITH CARE! AI generated code with some human review.")
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
        print(f"  Patient Name:        {tracer.get('patient_name')}")
        print(f"  Patient ID:          {tracer.get('patient_id')}")
        print(f"  Study ID:            {tracer.get('study_id')}")
        print(f"  Study Date:          {tracer.get('study_date')}")
        print(f"  Series Instance UID: {series_uid}")
        print(f"  DICOM Path:          {scan_result['dicom_path']}")
        print(f"  Study Description:   {tracer.get('study_description')}")
        print(f"  Series Description:  {tracer['series_description']}")
        print(f"  Protocol Name:       {tracer['protocol_name']}")
        print(f"  Manufacturer:        {tracer['manufacturer']}")
        print(f"  Model Name:          {tracer['model_name']}")

        # Tracer Information
        print("\n--- TRACER INFORMATION ---")
        print(f"  Radiopharmaceutical: {tracer['tracer_name'] or 'Not specified'}")
        if tracer.get('tracer_code'):
            print(f"  Standardized Name:   {tracer['tracer_code']}")
        print(f"  Radionuclide:        {tracer['radionuclide'] or 'Not specified'}")
        if tracer['half_life_seconds']:
            print(f"  Half-life:           {tracer['half_life_seconds']:.2f} seconds ({round(tracer['half_life_seconds'] / 60, 1)} minutes)")
        if tracer['injected_dose_bq']:
            print(f"  Injected Dose:       {tracer['injected_dose_bq'] / 1e6:.2f} MBq")
        if tracer['injection_time']:
            print(f"  Injection Time (0018,1072): {tracer['injection_time']}")
        if tracer['series_time']:
            print(f"  Series Time (0008,0031):    {tracer['series_time']}")
        if tracer.get('injection_time_ms') is not None and tracer.get('series_time_ms') is not None:
            time_diff_ms = tracer['series_time_ms'] - tracer['injection_time_ms']
            time_diff_min = round(time_diff_ms / 60000.0, 1)
            print(f"  Series-Injection Diff:      {time_diff_min} minutes")
        if tracer.get('warnings'):
            print('  WARNINGS:')
            for warning in tracer['warnings']: print(f"  * {warning}")

        # # Calculate and display time difference between series and injection
        # if tracer.get('injection_time_ms') is not None and tracer.get('series_time_ms') is not None:
        #     time_diff_ms = tracer['series_time_ms'] - tracer['injection_time_ms']
        #     time_diff_min = round(time_diff_ms / 60000.0, 1)
        #     print(f"  Series-Injection Diff:      {time_diff_min} minutes")

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
                window_start_min_calc = format_time_ms_to_min(first_frame['frame_start_time_ms_WithCorrections'])
                window_end_min_calc = format_time_ms_to_min(last_frame['frame_end_time_ms_WithCorrections'])
                total_duration_min_withCorrections = window_end_min_calc - window_start_min_calc
                print(f"\n  Imaging Window (Raw):      {window_start_min:.2f} - {window_end_min:.2f} minutes post-injection")
                try:
                    print(f"  Imaging Window (Calculated):      {window_start_min_calc:.2f} - {window_end_min_calc:.2f} minutes post-injection")
                except Exception as e:
                    continue

                print(f"  Total Duration (Raw):      {total_duration_min:.2f} minutes")
                print(f"  Total Duration (Calculated):      {total_duration_min_withCorrections:.2f} minutes")
                if total_duration_min != total_duration_min_withCorrections:
                    print("  ! WARNING: Calculated duration does not match raw duration. Investigate. This may imply that time difference between injection time and scan start exceeds frame duration. The calculated frame times are most likely incorrect. Proceed with caution")

                # Frame details (RAW)
                print("\n--- FRAME DETAILS (RAW) ---")
                has_clock_times = any(frame.get('calculated_start_time') for frame in frames)

                if has_clock_times:
                    print(f"  {'Frame':<6} {'Start (min)':<12} {'End (min)':<12} {'Duration (sec)':<15} {'Mid-frame (min)':<15} {'Clock Start':<12} {'Clock End':<12}")
                    print("  " + "-" * 96)
                else:
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

                    start_str = f"{start_min}" if start_min is not None else "N/A"
                    end_str = f"{end_min}" if end_min is not None else "N/A"
                    dur_str = f"{duration_sec}" if duration_sec is not None else "N/A"
                    mid_str = f"{mid_min}" if mid_min is not None else "N/A"

                    if has_clock_times:
                        clock_start = frame.get('calculated_start_time') or 'N/A'
                        clock_end = frame.get('calculated_end_time') or 'N/A'
                        print(f"  {i:<6} {start_str:<12} {end_str:<12} {dur_str:<15} {mid_str:<15} {clock_start:<12} {clock_end:<12}")
                    else:
                        print(f"  {i:<6} {start_str:<12} {end_str:<12} {dur_str:<15} {mid_str:<15}")

                # Frame details (calculated)
                if tracer.get('injection_time_ms') is not None and tracer.get('series_time_ms') is not None:
                    print("\n--- FRAME DETAILS (Calculated) ---")
                    has_clock_times = any(frame.get('calculated_start_clock_WithCorrections') for frame in frames)

                    if has_clock_times:
                        print(f"  {'Frame':<6} {'Start (min)':<12} {'End (min)':<12} {'Duration (sec)':<15} {'Mid-frame (min)':<15} {'Offset-Time (sec)':<17} {'Clock Start':<12} {'Clock End':<12}")
                        print("  " + "-" * 96)
                    else:
                        print(f"  {'Frame':<6} {'Start (min)':<12} {'End (min)':<12} {'Duration (sec)':<15} {'Mid-frame (min)':<15} {'Offset-Time (sec)':<17}")
                        print("  " + "-" * 60)

                    frame_durations = []
                    for i, frame in enumerate(frames, 1):
                        start_min = format_time_ms_to_min(frame['frame_start_time_ms_WithCorrections'])
                        end_min = format_time_ms_to_min(frame['frame_end_time_ms_WithCorrections'])
                        duration_sec = format_duration_ms_to_sec(frame['actual_frame_duration_ms'])
                        mid_min = format_time_ms_to_min(frame['frame_mid_time_ms_WithCorrections'])

                        if duration_sec is not None:
                            frame_durations.append(duration_sec)

                        start_str = f"{start_min}" if start_min is not None else "N/A"
                        end_str = f"{end_min}" if end_min is not None else "N/A"
                        dur_str = f"{duration_sec}" if duration_sec is not None else "N/A"
                        mid_str = f"{mid_min}" if mid_min is not None else "N/A"
                        off_str = f"{frame['offset_correction_time']/1000.0:.2f}" if frame.get('offset_correction_time') is not None else "N/A"

                        if has_clock_times:
                            clock_start = ms_to_time_string(frame['calculated_start_clock_WithCorrections']) or 'N/A'
                            clock_end = ms_to_time_string(frame['calculated_end_clock_WithCorrections']) or 'N/A'
                            print(f"  {i:<6} {start_str:<12} {end_str:<12} {dur_str:<15} {mid_str:<15} {off_str:<17} {clock_start:<12} {clock_end:<12}")
                        else:
                            print(f"  {i:<6} {start_str:<12} {end_str:<12} {dur_str:<15} {mid_str:<15} {off_str:<17}")

                # Summary of frame durations
                if frame_durations:
                    unique_durations = list(set(frame_durations))
                    unique_durations.sort()
                    print("\n--- FRAME DURATION SUMMARY ---")
                    if len(unique_durations) == 1:
                        print(f"  All frames have uniform duration: {unique_durations[0]} seconds ({round(unique_durations[0] / 60, 1)} minutes)")
                    else:
                        print(f"  Frame durations vary:")
                        for dur in unique_durations:
                            count = frame_durations.count(dur)
                            print(f"    {dur} seconds ({round(dur / 60, 1)} minutes): {count} frame(s)")

                # Modality/BIDS Guess
        agreement = scan_result.get('tracer_agreement', {})
        if agreement:
            print("\n--- TRACER LABEL vs. FREE-TEXT CROSS-CHECK ---")
            print(f"  Primary Tracer (Radiopharmaceutical field): {agreement.get('primary_tracer')}")
            per_field = agreement.get('freetext_tracers_by_field', {}) or {}
            for field_name, hits in per_field.items():
                pretty = ", ".join(hits) if hits else "(no tracer hint)"
                print(f"    {field_name:<20} -> {pretty}")
            print(f"  Agreement:           {agreement.get('agreement')}")
            print(f"  Disagreement Flag:   {agreement.get('disagreement')}")

            timing_scores = agreement.get('timing_scores', {}) or {}
            if timing_scores:
                window = agreement.get('scan_window_minutes')
                window_str = f"{window[0]:.2f}-{window[1]:.2f} min" if window else "n/a"
                print(f"  Timing Fit Scores (scan window {window_str}):")
                for cand, info in sorted(timing_scores.items(), key=lambda kv: kv[1]['score'], reverse=True):
                    best_proto = info.get('best_protocol')
                    proto_name = best_proto['name'] if best_proto else 'no matching protocol'
                    print(f"    {cand:<10} score={info['score']:.2f}  (best protocol: {proto_name})")

            selected = agreement.get('selected_tracer')
            primary = agreement.get('primary_tracer')
            marker = " (OVERRIDE)" if selected and selected != primary else ""
            print(f"  Selected Tracer:     {selected}{marker}")
            if agreement.get('selection_reason'):
                print(f"    Reason: {agreement['selection_reason']}")
            if agreement.get('notes'):
                print(f"  Notes:")
                for note in agreement['notes']:
                    print(f"    - {note}")

        modality = scan_result.get('modality_guess', {})

        if not modality.get('window_fits_protocol', True):
            print("\n--- TRACER WINDOW FIT ---")
            print(f"  Tracer does not fit imaging window perfectly: {window_start_min_calc} - {window_end_min_calc}")
            print(f"  Expected imaging window for {modality.get('bids_tracer', 'unknown')}: {modality.get('tracer_begin_expected')} - {modality.get('tracer_end_expected')}")
            if modality.get('alternative_tracer_bids'):
                print(f"  Alternative tracer with perfect fit: {modality.get('alternative_tracer_bids')}")


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
        'README': "USE WITH CARE! AI generated code with only some human review.",
        'scans': []
    }

    for scan_result in results:
        tracer_info = scan_result['tracer_info']
        frames = scan_result['frames']

        scan_export = {
            'series_instance_uid': scan_result['series_instance_uid'],
            'dicom_path': scan_result['dicom_path'],
            'patient_name': tracer_info.get('patient_name'),
            'patient_id': tracer_info.get('patient_id'),
            'study_id': tracer_info.get('study_id'),
            'clinical_trial_series_id': tracer_info.get('clinical_trial_series_id'),
            'deidentification_method': tracer_info.get('deidentification_method'),
            'study_date': tracer_info.get('study_date'),
            'series_date': tracer_info.get('series_date'),
            'acquisition_date': tracer_info.get('acquisition_date'),
            'content_date': tracer_info.get('content_date'),
            'study_time': tracer_info.get('study_time'),
            'series_time': tracer_info.get('series_time'),
            'manufacturer': tracer_info['manufacturer'],
            'model_name': tracer_info['model_name'],
            'series_description': tracer_info['series_description'],
            'protocol_name': tracer_info['protocol_name'],
            'study_description': tracer_info.get('study_description'),
            'tracer': {
                'name': tracer_info['tracer_name'],
                'standardized_name': tracer_info.get('tracer_code'),
                'radionuclide': tracer_info['radionuclide'],
                'half_life_seconds': tracer_info['half_life_seconds'],
                'injected_dose_MBq': tracer_info['injected_dose_bq'] / 1e6 if tracer_info['injected_dose_bq'] else None,
                'injection_time': tracer_info['injection_time'],
            },
            'imaging_window_raw': {},
            'imaging_window_withCorrection': {},
            'frames': []
        }

        if frames:
            first_frame = frames[0]
            last_frame = frames[-1]

            scan_export['imaging_window_raw'] = {
                'start_minutes': format_time_ms_to_min(first_frame['frame_start_time_ms']),
                'end_minutes': format_time_ms_to_min(last_frame['frame_end_time_ms']),
                'total_duration_minutes': format_time_ms_to_min((last_frame.get('frame_end_time_ms') or np.nan) - (first_frame.get('frame_start_time_ms') or np.nan)),
                'total_frames': len(frames)
            }

            scan_export['imaging_window_withCorrection'] = {
                'start_minutes': format_time_ms_to_min(first_frame['frame_start_time_ms_WithCorrections']),
                'end_minutes': format_time_ms_to_min(last_frame['frame_end_time_ms_WithCorrections']),
                'total_duration': format_time_ms_to_min((last_frame.get('frame_end_time_ms_WithCorrections') or np.nan) - (first_frame.get('frame_start_time_ms_WithCorrections') or np.nan)),
                'total_frames': len(frames)
            }

            for i, frame in enumerate(frames, 1):
                frame_export = {
                    'frame_number': i,
                    'start_minutes_raw': format_time_ms_to_min(frame['frame_start_time_ms']),
                    'end_minutes_raw': format_time_ms_to_min(frame['frame_end_time_ms']),
                    'duration_seconds': format_duration_ms_to_sec(frame['actual_frame_duration_ms']),
                    'mid_frame_minutes_raw': format_time_ms_to_min(frame['frame_reference_time_ms']),
                    'offset_correction_seconds': frame.get('offset_correction_time') / 1000.0 if frame.get('offset_correction_time') is not None else None,
                    'start_minutes_withCorrection': format_time_ms_to_min(frame['frame_start_time_ms_WithCorrections']),
                    'end_minutes_withCorrection': format_time_ms_to_min(frame['frame_end_time_ms_WithCorrections']),
                    'mid_frame_minutes_withCorrection': format_time_ms_to_min(frame.get('frame_mid_time_ms_WithCorrections')),
                }
                # Add calculated clock times if available
                if frame.get('calculated_start_time'):
                    frame_export['clock_start_time_raw'] = frame['calculated_start_time']
                    frame_export['clock_mid_time_raw'] = frame.get('calculated_mid_time')
                    frame_export['clock_end_time_raw'] = frame.get('calculated_end_time')

                if frame.get('calculated_start_clock_WithCorrections'):
                    frame_export['clock_start_time_WithCorrections'] = ms_to_time_string(frame['calculated_start_clock_WithCorrections'])
                    frame_export['clock_mid_time_WithCorrections'] = ms_to_time_string(frame.get('calculated_mid_clock_WithCorrections'))
                    frame_export['clock_end_time_WithCorrections'] = ms_to_time_string(frame.get('calculated_end_clock_WithCorrections'))

                scan_export['frames'].append(frame_export)

        # Add timing reference info
        scan_export['timing_reference'] = {
            'injection_time_raw': tracer_info.get('injection_time'),
            'series_time_raw': tracer_info.get('series_time'),
            'series_injection_diff_minutes_raw': format_time_ms_to_min(tracer_info.get('injection_to_scan_diff_ms_raw')),
        }

        modality = scan_result.get('modality_guess', {})

        # Add tracer label vs. free-text cross-check
        agreement = scan_result.get('tracer_agreement', {}) or {}
        scan_export['tracer_agreement'] = {
            'primary_tracer': agreement.get('primary_tracer'),
            'freetext_tracers': agreement.get('freetext_tracers', []),
            'freetext_tracers_by_field': agreement.get('freetext_tracers_by_field', {}),
            'agreement': agreement.get('agreement'),
            'disagreement': agreement.get('disagreement', False),
            'scan_window_minutes': agreement.get('scan_window_minutes'),
            'timing_scores': {
                cand: {
                    'score': round(info.get('score', 0.0), 3),
                    'best_protocol': (info.get('best_protocol') or {}).get('name'),
                    'per_protocol': info.get('per_protocol', []),
                }
                for cand, info in (agreement.get('timing_scores') or {}).items()
            },
            'selected_tracer': agreement.get('selected_tracer'),
            'selection_reason': agreement.get('selection_reason'),
            'tracer_begin_expected': modality.get('tracer_begin_expected'),
            'tracer_end_expected': modality.get('tracer_end_expected'),
            'alternative_tracer_bids': modality.get('alternative_tracer_bids'),
            ' ': modality.get('window_fits_protocol'),
            'notes': agreement.get('notes', []),
        }
        # Top-level convenience flags:
        # - tracer_disagreement: True if primary and free-text hints diverge
        # - tracer_overridden: True if the frame-timing arbitration replaced the primary
        scan_export['tracer_disagreement'] = bool(agreement.get('disagreement'))
        scan_export['tracer_overridden'] = bool(
            agreement.get('selected_tracer')
            and agreement.get('primary_tracer')
            and agreement.get('selected_tracer') != agreement.get('primary_tracer')
        )

        # Add modality guess

        scan_export['modality_guess'] = {
            'protocol_name': modality.get('protocol_name'),
            'scan_type': modality.get('scan_type'),
            'description': modality.get('description'),
            'confidence': modality.get('confidence'),
            'bids_tracer': modality.get('bids_tracer'),
            'bids_filename_suggestion': modality.get('bids_filename_suggestion'),
            'notes': modality.get('notes', []),
        }

        #Add warnings:
        scan_export['warnings'] = []
        if scan_export['imaging_window_raw'].get('total_duration_minutes') != scan_export['imaging_window_withCorrection'].get('total_duration'):
            scan_export['warnings'].append('Raw and corrected imaging window duration do not match.')
        for warning in tracer_info.get('warnings'):
            scan_export['warnings'].append(warning)


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
    parser.add_argument('dicom_dir', type=str, nargs='+',
                        help='Path to directory containing PET DICOM files')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='Output JSON file path (optional)')

    args = parser.parse_args()
    for dir in args.dicom_dir:
        if not os.path.isdir(dir):
            print(f"Error: Directory not found: {dir}")
            return 1

    results = analyze_pet_dicoms(args.dicom_dir)

    if results:
        print_results(results)

        if args.output:
            export_to_json(results, args.output)

    return 0


if __name__ == "__main__":
    exit(main())


