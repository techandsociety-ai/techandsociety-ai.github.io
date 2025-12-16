#!/usr/bin/env python3
"""
Upload processed real CHIP50 data to BigQuery.

This script uploads the processed CSV files to BigQuery raw tables:
- chip50_demographics_*.csv -> chip50.raw.demographics
- chip50_survey_responses_*.csv -> chip50.raw.survey_responses

Usage:
    python upload_real_data_to_bigquery.py [--project PROJECT_ID] [--dataset DATASET_ID]
"""

import argparse
from pathlib import Path
from google.cloud import bigquery
from typing import Optional


def find_latest_processed_file(data_dir: Path, pattern: str) -> Optional[Path]:
    """
    Find the most recent processed file matching the pattern.

    Args:
        data_dir: Directory containing processed files
        pattern: Glob pattern to match files

    Returns:
        Path to the most recent file, or None if not found
    """
    files = sorted(data_dir.glob(pattern))
    return files[-1] if files else None


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

    # Configure the load job with comprehensive settings
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,  # Skip header row
        autodetect=True,  # Auto-detect schema
        write_disposition=write_disposition,
        # Allow for quoted newlines in data
        allow_quoted_newlines=True,
        # Set maximum bad records threshold
        max_bad_records=100,
        # Enable schema update options
        schema_update_options=[
            bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION,
            bigquery.SchemaUpdateOption.ALLOW_FIELD_RELAXATION,
        ],
    )

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
    print("  Uploading... (this may take a few minutes)")
    job.result()

    # Get the loaded table
    table = client.get_table(table_ref)

    print(f"✓ Successfully loaded {table.num_rows:,} rows into {table_ref}")
    print(f"  Schema: {len(table.schema)} columns")

    # Print first 10 columns
    print("  Sample columns:")
    for i, field in enumerate(table.schema[:10], 1):
        print(f"    {i:2d}. {field.name:30s} {field.field_type}")

    if len(table.schema) > 10:
        print(f"    ... and {len(table.schema) - 10} more columns")


def verify_table_data(project_id: str, dataset_id: str, table_id: str) -> None:
    """
    Verify uploaded data by running sample queries.

    Args:
        project_id: GCP project ID
        dataset_id: BigQuery dataset ID
        table_id: BigQuery table ID
    """
    client = bigquery.Client(project=project_id)
    table_ref = f"{project_id}.{dataset_id}.{table_id}"

    print(f"\nVerifying {table_ref}...")

    # Query 1: Count rows
    query = f"SELECT COUNT(*) as row_count FROM `{table_ref}`"
    result = client.query(query).result()
    for row in result:
        print(f"  Total rows: {row.row_count:,}")

    # Query 2: Count unique IDs
    query = f"SELECT COUNT(DISTINCT id) as unique_ids FROM `{table_ref}`"
    result = client.query(query).result()
    for row in result:
        print(f"  Unique IDs: {row.unique_ids:,}")

    # Query 3: Count by wave
    query = f"""
    SELECT
        wave,
        COUNT(*) as count
    FROM `{table_ref}`
    GROUP BY wave
    ORDER BY wave
    """
    result = client.query(query).result()
    print("  Rows by wave:")
    for row in result:
        print(f"    Wave {row.wave}: {row.count:,} rows")


def main():
    """Main upload function."""
    parser = argparse.ArgumentParser(
        description="Upload processed CHIP50 data to BigQuery"
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
        "--demographics",
        type=Path,
        help="Path to demographics CSV file (default: auto-detect latest)"
    )
    parser.add_argument(
        "--survey-responses",
        type=Path,
        help="Path to survey responses CSV file (default: auto-detect latest)"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Run verification queries after upload"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("CHIP50 Real Data Upload to BigQuery")
    print("=" * 70)
    print(f"Project: {args.project}")
    print(f"Dataset: {args.dataset}")

    # Find processed files
    data_dir = Path(__file__).parent / "data" / "processed"

    if args.demographics:
        demo_path = args.demographics
    else:
        demo_path = find_latest_processed_file(data_dir, "chip50_demographics_*.csv")
        if not demo_path:
            print("\nError: No demographics file found in data/processed/")
            print("Run process_real_data.py first, or specify --demographics path")
            return

    if args.survey_responses:
        survey_path = args.survey_responses
    else:
        survey_path = find_latest_processed_file(data_dir, "chip50_survey_responses_*.csv")
        if not survey_path:
            print("\nError: No survey responses file found in data/processed/")
            print("Run process_real_data.py first, or specify --survey-responses path")
            return

    print(f"\nUsing files:")
    print(f"  Demographics: {demo_path.name}")
    print(f"  Survey responses: {survey_path.name}")

    # Upload demographics
    try:
        upload_csv_to_bigquery(
            project_id=args.project,
            dataset_id=args.dataset,
            table_id="demographics",
            csv_path=demo_path
        )
    except Exception as e:
        print(f"\n✗ Error uploading demographics: {e}")
        return

    # Upload survey responses
    try:
        upload_csv_to_bigquery(
            project_id=args.project,
            dataset_id=args.dataset,
            table_id="survey_responses",
            csv_path=survey_path
        )
    except Exception as e:
        print(f"\n✗ Error uploading survey responses: {e}")
        return

    # Verify data if requested
    if args.verify:
        print("\n" + "=" * 70)
        print("VERIFICATION")
        print("=" * 70)

        verify_table_data(args.project, args.dataset, "demographics")
        verify_table_data(args.project, args.dataset, "survey_responses")

    # Print success message
    print("\n" + "=" * 70)
    print("SUCCESS! Data uploaded to BigQuery")
    print("=" * 70)
    print(f"""
Next steps:

1. View your data in BigQuery console:
   https://console.cloud.google.com/bigquery?project={args.project}&d={args.dataset}&p={args.project}

2. Update the protected views to match the new schema:
   - Review and update sql/create_demographics_protected.sql
   - Review and update sql/create_survey_responses_protected.sql

3. Create the protected views:
   ./test_views.sh

4. Test the MCP server with real data:
   python test_bigquery_crosstab.py
""")


if __name__ == "__main__":
    main()
