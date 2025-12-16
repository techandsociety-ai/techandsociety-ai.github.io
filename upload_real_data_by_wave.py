#!/usr/bin/env python3
"""
Upload processed CHIP50 data to BigQuery with separate tables per wave.

This script uploads each wave to its own table:
- CSP_W35 → chip50.raw.demographics_w35 and chip50.raw.survey_responses_w35
- CSP_W35.1 → chip50.raw.demographics_w35_1 and chip50.raw.survey_responses_w35_1

Usage:
    python upload_real_data_by_wave.py [--project PROJECT_ID] [--dataset DATASET_ID]
"""

import argparse
import re
from pathlib import Path
from google.cloud import bigquery
from typing import List, Dict


def normalize_wave_for_table_name(wave: str) -> str:
    """
    Convert wave identifier to valid BigQuery table suffix.

    Examples:
        "35" -> "w35"
        "35.1" -> "w35_1"
    """
    # Replace dots with underscores and ensure it starts with 'w'
    normalized = wave.replace('.', '_')
    if not normalized.startswith('w'):
        normalized = f'w{normalized}'
    return normalized


def find_wave_file(data_dir: Path, wave_pattern: str) -> Path:
    """Find the CSV file for a specific wave."""
    files = list(data_dir.glob(wave_pattern))
    if files:
        return files[0]
    return None


def upload_csv_to_bigquery(
    project_id: str,
    dataset_id: str,
    table_id: str,
    csv_path: Path,
    write_disposition: str = "WRITE_TRUNCATE"
) -> None:
    """
    Upload a CSV file to BigQuery with schema auto-detection.

    Args:
        project_id: GCP project ID
        dataset_id: BigQuery dataset ID
        table_id: BigQuery table ID
        csv_path: Path to the CSV file
        write_disposition: Write disposition (WRITE_TRUNCATE, WRITE_APPEND, WRITE_EMPTY)
    """
    # Initialize BigQuery client
    client = bigquery.Client(project=project_id)

    # Construct full table ID
    table_ref = f"{project_id}.{dataset_id}.{table_id}"

    # Configure the load job
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,  # Skip header row
        autodetect=True,  # Auto-detect schema
        write_disposition=write_disposition,
        allow_quoted_newlines=True,
        max_bad_records=100,
    )

    # Only add schema update options for WRITE_APPEND
    # (WRITE_TRUNCATE replaces the table, so schema updates aren't needed)
    if write_disposition == "WRITE_APPEND":
        job_config.schema_update_options = [
            bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION,
            bigquery.SchemaUpdateOption.ALLOW_FIELD_RELAXATION,
        ]

    # Load the CSV file
    print(f"\nUploading {csv_path.name} to {table_ref}...")
    print(f"  File size: {csv_path.stat().st_size / (1024*1024):.2f} MB")

    with open(csv_path, "rb") as source_file:
        job = client.load_table_from_file(
            source_file,
            table_ref,
            job_config=job_config
        )

    # Wait for the job to complete
    print("  Uploading...")
    job.result()

    # Get the loaded table
    table = client.get_table(table_ref)

    print(f"✓ Successfully loaded {table.num_rows:,} rows into {table_ref}")
    print(f"  Schema: {len(table.schema)} columns")


def process_wave_file(
    wave_file: Path,
    project_id: str,
    dataset_id: str
) -> Dict[str, str]:
    """
    Process a single wave CSV file.

    Args:
        wave_file: Path to the wave CSV file
        project_id: GCP project ID
        dataset_id: BigQuery dataset ID

    Returns:
        Dict with table names created
    """
    # Extract wave number from filename (e.g., "CSP_W35.csv" -> "35")
    match = re.search(r'CSP_W([\d.]+)\.csv', wave_file.name)
    if not match:
        raise ValueError(f"Cannot extract wave number from {wave_file.name}")

    wave_num = match.group(1)
    wave_suffix = normalize_wave_for_table_name(wave_num)

    print(f"\n{'='*70}")
    print(f"Processing Wave {wave_num} ({wave_file.name})")
    print(f"{'='*70}")

    # Table names for this wave
    demo_table = f"demographics_{wave_suffix}"
    survey_table = f"survey_responses_{wave_suffix}"

    # For now, we expect processed files in data/processed/
    # In a full pipeline, we would process the raw file here
    processed_dir = wave_file.parent / "processed"

    # Look for processed files for this wave
    # Use wave_suffix (normalized with underscores) instead of wave_num (which may have dots)
    # E.g., wave 35.1 → files named chip50_demographics_w35_1_*.csv
    wave_file_pattern = wave_suffix.replace('w', '')  # Remove 'w' prefix for file pattern
    demo_file = find_wave_file(processed_dir, f"*demographics*w{wave_file_pattern}_*.csv")
    survey_file = find_wave_file(processed_dir, f"*survey_responses*w{wave_file_pattern}_*.csv")

    if not demo_file or not survey_file:
        print(f"⚠ Warning: Processed files not found for wave {wave_num}")
        print(f"  Looking in: {processed_dir}")
        print(f"  Expected patterns: *demographics*w{wave_file_pattern}_*.csv, *survey_responses*w{wave_file_pattern}_*.csv")
        return None

    print(f"\nUsing processed files:")
    print(f"  Demographics: {demo_file.name}")
    print(f"  Survey: {survey_file.name}")

    # Upload demographics
    upload_csv_to_bigquery(
        project_id=project_id,
        dataset_id=dataset_id,
        table_id=demo_table,
        csv_path=demo_file
    )

    # Upload survey responses
    upload_csv_to_bigquery(
        project_id=project_id,
        dataset_id=dataset_id,
        table_id=survey_table,
        csv_path=survey_file
    )

    return {
        'wave': wave_num,
        'demo_table': f"{project_id}.{dataset_id}.{demo_table}",
        'survey_table': f"{project_id}.{dataset_id}.{survey_table}"
    }


def main():
    """Main upload function."""
    parser = argparse.ArgumentParser(
        description="Upload CHIP50 data to BigQuery with separate tables per wave"
    )
    parser.add_argument(
        "--project",
        default="chip50",
        help="GCP project ID (default: chip50)"
    )
    parser.add_argument(
        "--dataset",
        default="raw",
        help="BigQuery dataset ID (default: raw)"
    )
    parser.add_argument(
        "--waves",
        nargs="+",
        help="Specific waves to upload (e.g., --waves 35 35.1)"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("CHIP50 Wave-Specific Data Upload to BigQuery")
    print("=" * 70)
    print(f"Project: {args.project}")
    print(f"Dataset: {args.dataset}")

    # Find wave files
    data_dir = Path(__file__).parent / "data"

    if args.waves:
        # Upload specific waves
        wave_files = []
        for wave in args.waves:
            pattern = f"CSP_W{wave}.csv"
            found = list(data_dir.glob(pattern))
            if found:
                wave_files.extend(found)
            else:
                print(f"⚠ Warning: No file found for wave {wave} (pattern: {pattern})")
    else:
        # Upload all waves
        wave_files = sorted(data_dir.glob("CSP_W*.csv"))

    if not wave_files:
        print("\n✗ Error: No wave files found")
        print(f"  Looking in: {data_dir}")
        print(f"  Pattern: CSP_W*.csv")
        return

    print(f"\nFound {len(wave_files)} wave file(s) to upload:")
    for f in wave_files:
        print(f"  - {f.name}")

    # Process each wave
    results = []
    for wave_file in wave_files:
        try:
            result = process_wave_file(wave_file, args.project, args.dataset)
            if result:
                results.append(result)
        except Exception as e:
            print(f"\n✗ Error processing {wave_file.name}: {e}")
            continue

    # Print summary
    print("\n" + "=" * 70)
    print("UPLOAD COMPLETE")
    print("=" * 70)

    if results:
        print(f"\n✓ Successfully uploaded {len(results)} wave(s):")
        for r in results:
            print(f"\n  Wave {r['wave']}:")
            print(f"    - {r['demo_table']}")
            print(f"    - {r['survey_table']}")

        print("\n" + "=" * 70)
        print("NEXT STEPS")
        print("=" * 70)
        print("\n1. Create protected views for each wave:")
        for r in results:
            wave_suffix = normalize_wave_for_table_name(r['wave'])
            print(f"\n   Wave {r['wave']}:")
            print(f"     bq query --project_id={args.project} < sql/create_demographics_protected_{wave_suffix}.sql")
            print(f"     bq query --project_id={args.project} < sql/create_survey_responses_protected_{wave_suffix}.sql")

        print("\n2. View your data in BigQuery console:")
        print(f"   https://console.cloud.google.com/bigquery?project={args.project}&d={args.dataset}")

        print("\n3. Test queries:")
        print("   python test_bigquery_crosstab.py")
    else:
        print("\n✗ No waves were uploaded successfully")


if __name__ == "__main__":
    main()
