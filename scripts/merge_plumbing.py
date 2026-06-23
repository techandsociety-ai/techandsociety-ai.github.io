"""
Merge CHIP50 panel CSV with county-level plumbing (running water) data.

Join key: CHIP50.id == Plumbing.Id  (both sides strip dashes before comparing)
New columns added: fips, county, running_water_pct
"""

import csv
import sys
from pathlib import Path

CHIP50_CSV  = Path(__file__).parent.parent / "data" / "export_CHIP50_SocialMedia_vars_2026_06_20_17_20.csv"
PLUMBING_CSV = Path(__file__).parent.parent / "data" / "Plumbing_data_merged_with_CHIP50_respondents_v1_2026_06_18.csv"
OUT_CSV     = Path(__file__).parent.parent / "data" / "export_CHIP50_SocialMedia_vars_2026_06_20_plumbing.csv"

def strip_id(val):
    return val.replace("-", "").strip()

def main():
    print("Loading plumbing crosswalk...", flush=True)
    plumbing = {}
    with open(PLUMBING_CSV, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = strip_id(row["Id"])
            plumbing[key] = {
                "fips":              row["Fips"].strip(),
                "county":            row["County long name"].strip(),
                "running_water_pct": row["Running Water Pct"].strip(),
            }
    print(f"  {len(plumbing):,} plumbing records loaded.", flush=True)

    print("Merging with CHIP50 panel...", flush=True)
    matched = 0
    unmatched = 0

    with open(CHIP50_CSV, newline="", encoding="utf-8-sig") as fin, \
         open(OUT_CSV,    newline="", encoding="utf-8", mode="w") as fout:

        reader = csv.DictReader(fin)
        new_fields = reader.fieldnames + ["fips", "county", "running_water_pct"]
        writer = csv.DictWriter(fout, fieldnames=new_fields, extrasaction="ignore")
        writer.writeheader()

        for i, row in enumerate(reader, 1):
            key = strip_id(row.get("id", ""))
            match = plumbing.get(key)
            if match:
                row.update(match)
                matched += 1
            else:
                row["fips"] = ""
                row["county"] = ""
                row["running_water_pct"] = ""
                unmatched += 1
            writer.writerow(row)

            if i % 100_000 == 0:
                print(f"  {i:,} rows processed...", flush=True)

    total = matched + unmatched
    print(f"\nDone.")
    print(f"  Total rows:  {total:,}")
    print(f"  Matched:     {matched:,} ({matched/total*100:.1f}%)")
    print(f"  Unmatched:   {unmatched:,} ({unmatched/total*100:.1f}%)")
    print(f"  Output:      {OUT_CSV}")

if __name__ == "__main__":
    main()
