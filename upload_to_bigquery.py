#!/usr/bin/env python3
"""
Upload synthetic data CSV files to BigQuery dataset.

This script uploads:
- synthetic_demographics.csv -> chip50.raw.demographics
- synthetic_survey_responses.csv -> chip50.raw.survey_responses
"""

import os
from google.cloud import bigquery
from pathlib import Path


def upload_csv_to_bigquery(
    project_id: str,
    dataset_id: str,
    table_id: str,
    csv_path: str,
    write_disposition: str = "WRITE_TRUNCATE"
) -> None:
    """
    Upload a CSV file to BigQuery.

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
    )

    # Load the CSV file
    print(f"Uploading {csv_path} to {table_ref}...")

    with open(csv_path, "rb") as source_file:
        job = client.load_table_from_file(
            source_file,
            table_ref,
            job_config=job_config
        )

    # Wait for the job to complete
    job.result()

    # Get the loaded table
    table = client.get_table(table_ref)

    print(f"✓ Loaded {table.num_rows} rows into {table_ref}")
    print(f"  Schema: {len(table.schema)} columns")
    for field in table.schema:
        print(f"    - {field.name}: {field.field_type}")


def main():
    """Main function to upload all CSV files."""

    # Configuration
    PROJECT_ID = "chip50"
    DATASET_ID = "raw"

    # Get the script directory
    script_dir = Path(__file__).parent
    data_dir = script_dir / "synthetic_data"

    # Define the files to upload
    uploads = [
        {
            "csv_path": data_dir / "synthetic_demographics.csv",
            "table_id": "demographics",
            "description": "Demographic information for survey respondents"
        },
        {
            "csv_path": data_dir / "synthetic_survey_responses.csv",
            "table_id": "survey_responses",
            "description": "Survey response data"
        }
    ]

    print(f"Starting upload to BigQuery dataset: {PROJECT_ID}.{DATASET_ID}\n")

    # Upload each file
    for upload_config in uploads:
        csv_path = upload_config["csv_path"]
        table_id = upload_config["table_id"]

        if not csv_path.exists():
            print(f"✗ Error: {csv_path} not found!")
            continue

        try:
            upload_csv_to_bigquery(
                project_id=PROJECT_ID,
                dataset_id=DATASET_ID,
                table_id=table_id,
                csv_path=str(csv_path)
            )
            print()
        except Exception as e:
            print(f"✗ Error uploading {csv_path}: {e}\n")

    print("Upload complete!")
    print(f"\nYou can query your tables at:")
    print(f"https://console.cloud.google.com/bigquery?project={PROJECT_ID}&d={DATASET_ID}&p={PROJECT_ID}")


if __name__ == "__main__":
    main()
