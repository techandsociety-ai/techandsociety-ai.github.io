#!/usr/bin/env python3
"""
Load Wave to Dates.xlsx into BigQuery as social_media_demographics.wave_dates.

Creates/replaces the table:
  chip50.social_media_demographics.wave_dates
  Columns: wave (STRING), start_date (DATE), end_date (DATE),
           midpoint_date (DATE), n (INT64), size (STRING)

Usage:
  cd remote-mcp
  source ../.env        # or export GCP_PROJECT=chip50
  python3 load_wave_dates.py [--xlsx "../data/Wave to Dates.xlsx"]
"""

import argparse
import os
import sys
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, timedelta

from google.cloud import bigquery

GCP_PROJECT  = os.getenv("GCP_PROJECT",  "chip50")
DATASET_NAME = os.getenv("DATASET_NAME", "social_media_demographics")
TABLE_ID     = f"{GCP_PROJECT}.{DATASET_NAME}.wave_dates"

EXCEL_EPOCH = date(1899, 12, 30)
NS = {"ns": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

DEFAULT_XLSX = os.path.join(os.path.dirname(__file__), "..", "data", "Wave to Dates.xlsx")


def xl_to_date(serial: str) -> date:
    """Convert an Excel date serial number string to a Python date."""
    return EXCEL_EPOCH + timedelta(days=int(float(serial)))


def midpoint_date(start: date, end: date) -> date:
    """Return the midpoint date (rounded down if odd number of days)."""
    return start + (end - start) // 2


def parse_xlsx(path: str) -> list[dict]:
    """Parse Wave to Dates.xlsx and return list of row dicts."""
    with zipfile.ZipFile(path) as zf:
        # shared strings
        with zf.open("xl/sharedStrings.xml") as f:
            root = ET.parse(f).getroot()
        strings = [t.text or "" for t in root.findall(".//ns:t", NS)]

        # sheet1 rows
        with zf.open("xl/worksheets/sheet1.xml") as f:
            root = ET.parse(f).getroot()

    rows = []
    for row_el in root.findall(".//ns:row", NS):
        row = []
        for cell in row_el.findall("ns:c", NS):
            t = cell.get("t", "")
            v_el = cell.find("ns:v", NS)
            val = v_el.text if v_el is not None else None
            if t == "s" and val is not None:
                val = strings[int(val)]
            row.append(val)
        rows.append(row)

    if not rows:
        raise ValueError("No rows found in sheet1")

    header = rows[0]  # ['Wave', 'Start Date', 'End Date', 'Date', 'N', 'Size']
    records = []
    for row in rows[1:]:
        if len(row) < 6 or row[0] is None:
            continue
        wave_label = row[0]
        start = xl_to_date(row[1])
        end   = xl_to_date(row[2])
        mid   = midpoint_date(start, end)
        n     = int(float(row[4])) if row[4] else None
        size  = row[5]
        records.append({
            "wave":          wave_label,
            "wave_num":      float(wave_label),
            "start_date":    start.isoformat(),
            "end_date":      end.isoformat(),
            "midpoint_date": mid.isoformat(),
            "n":             n,
            "size":          size,
        })
    return records


SCHEMA = [
    bigquery.SchemaField("wave",          "STRING",  description="Wave label (e.g. '14', '35.1')"),
    bigquery.SchemaField("wave_num",      "FLOAT64", description="Numeric wave value for joining to panel_data_indexed.wave (INTEGER or FLOAT64)"),
    bigquery.SchemaField("start_date",    "DATE",    description="Field start date"),
    bigquery.SchemaField("end_date",      "DATE",    description="Field end date"),
    bigquery.SchemaField("midpoint_date", "DATE",    description="Midpoint date used for plotting"),
    bigquery.SchemaField("n",             "INT64",   description="Sample size"),
    bigquery.SchemaField("size",          "STRING",  description="Wave size category (full/medium/small)"),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--xlsx", default=DEFAULT_XLSX, help="Path to Wave to Dates.xlsx")
    args = parser.parse_args()

    xlsx_path = os.path.abspath(args.xlsx)
    if not os.path.exists(xlsx_path):
        sys.exit(f"Error: xlsx not found at {xlsx_path}")

    print(f"Parsing {xlsx_path} ...")
    records = parse_xlsx(xlsx_path)
    print(f"  {len(records)} waves found: {records[0]['wave']} – {records[-1]['wave']}")

    client = bigquery.Client(project=GCP_PROJECT)

    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    print(f"Loading into {TABLE_ID} ...")
    job = client.load_table_from_json(records, TABLE_ID, job_config=job_config)
    job.result()  # wait

    table = client.get_table(TABLE_ID)
    print(f"Done. {table.num_rows} rows in {TABLE_ID}")
    print()
    print(f"  wave  start_date   end_date     midpoint     n       size")
    for r in records:
        print(f"  {r['wave']:>5s}  {r['start_date']}  {r['end_date']}  {r['midpoint_date']}  {r['n']:>6,}  {r['size']}")


if __name__ == "__main__":
    main()
