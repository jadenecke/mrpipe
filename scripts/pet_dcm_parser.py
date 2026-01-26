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


def get_dicom_files(directory):
    """Recursively find all DICOM files in a directory."""
    dicom_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            filepath = os.path.join(root, file)
            try:
                # Try to read as DICOM
                ds = pydicom.dcmread(filepath, stop_before_pixels=True, force=True)
                if hasattr(ds, 'Modality') and ds.Modality == 'PT':
                    dicom_files.append(filepath)
            except (InvalidDicomError, Exception):
                continue
    return dicom_files


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
        # Frame reference time is typically the mid-frame time
        frame_info['frame_start_time_ms'] = frame_info['frame_reference_time_ms']
        frame_info['frame_end_time_ms'] = frame_info['frame_reference_time_ms'] + frame_info['actual_frame_duration_ms']

    # Number of Time Slices (0054,0101)
    if hasattr(ds, 'NumberOfTimeSlices'):
        frame_info['number_of_time_slices'] = int(ds.NumberOfTimeSlices)

    # Try to get from Number of Frames
    if hasattr(ds, 'NumberOfFrames'):
        frame_info['number_of_frames'] = int(ds.NumberOfFrames)

    return frame_info


def analyze_pet_dicoms(dicom_dir):
    """Analyze PET DICOM files and extract tracer and timing information."""

    print(f"Scanning directory: {dicom_dir}")
    dicom_files = get_dicom_files(dicom_dir)

    if not dicom_files:
        print("No PET DICOM files found.")
        return None

    print(f"Found {len(dicom_files)} PET DICOM files")

    # Collect frame information from all files
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

    # Analyze unique frames based on timing
    unique_frames = {}
    for frame in frames:
        key = (frame['frame_reference_time_ms'], frame['actual_frame_duration_ms'])
        if key not in unique_frames:
            unique_frames[key] = frame

    # Sort frames by reference time
    sorted_frames = sorted(unique_frames.values(),
                           key=lambda x: x['frame_reference_time_ms'] if x['frame_reference_time_ms'] is not None else 0)

    return {
        'tracer_info': tracer_info,
        'frames': sorted_frames,
        'total_dicom_files': len(dicom_files)
    }


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


    # Tracer Information
    tracer = results['tracer_info']
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
    frames = results['frames']
    print("\n--- IMAGING WINDOW INFORMATION ---")
    print(f"  Total DICOM files:   {results['total_dicom_files']}")
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

    print("\n" + "=" * 70)


def export_to_json(results, output_path):
    """Export results to a JSON file."""
    import json

    # Prepare data for JSON export
    export_data = {
        'README' : "USE WITH CARE! AI generated code with only minimal human review.",
        'tracer': {
            'name': results['tracer_info']['tracer_name'],
            'standardized_name': results['tracer_info'].get('tracer_code'),
            'radionuclide': results['tracer_info']['radionuclide'],
            'half_life_seconds': results['tracer_info']['half_life_seconds'],
            'injected_dose_MBq': results['tracer_info']['injected_dose_bq'] / 1e6 if results['tracer_info']['injected_dose_bq'] else None,
            'injection_time': results['tracer_info']['injection_time'],
        },
        'imaging_window': {},
        'frames': []
    }

    frames = results['frames']
    if frames:
        first_frame = frames[0]
        last_frame = frames[-1]

        export_data['imaging_window'] = {
            'start_minutes': format_time_ms_to_min(first_frame['frame_start_time_ms']),
            'end_minutes': format_time_ms_to_min(last_frame['frame_end_time_ms']),
            'total_frames': len(frames)
        }

        for i, frame in enumerate(frames, 1):
            export_data['frames'].append({
                'frame_number': i,
                'start_minutes': format_time_ms_to_min(frame['frame_start_time_ms']),
                'end_minutes': format_time_ms_to_min(frame['frame_end_time_ms']),
                'duration_seconds': format_duration_ms_to_sec(frame['actual_frame_duration_ms']),
                'mid_frame_minutes': format_time_ms_to_min(frame['frame_reference_time_ms'])
            })

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
