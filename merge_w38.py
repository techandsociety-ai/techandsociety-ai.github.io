#!/usr/bin/env python3
"""
One-time script to merge new W38 variables into the multi-wave export CSV.

New columns are:
  - SM new platforms: use/freq/post/trust for discord, telegram, twitch + sm_quit_*
  - Wave-38 content: iran, protest, university, thermometer, healthcare, etc.

All new columns will be NULL (empty) for non-W38 rows.
Join key: id (present in both files, 1-to-1 for wave 38).

Usage:
  python merge_w38.py
"""

import csv
import sys
import os

_HERE = os.path.dirname(os.path.abspath(__file__))

EXPORT_FILE = os.path.expanduser(
    "~/Downloads/export_CHIP50_SocialMedia_vars_2026_06_04_09_07.csv")
W38_FILE    = os.path.join(_HERE, "data", "CSP_W38.csv")
OUT_FILE    = os.path.join(_HERE, "data",
                           "export_CHIP50_SocialMedia_vars_2026_06_06_merged.csv")


def build_new_cols(export_cols_set, w38_all_cols):
    """Return ordered list of W38 raw columns to add (not already in export)."""

    def should_exclude(col):
        if col in export_cols_set:
            return True
        # Qualtrics metadata
        if col in ("StartDate", "EndDate", "Status", "Progress", "Finished",
                   "RecordedDate", "NIO", "Q_RecaptchaStatus", "version",
                   "false_terminate", "source", "vsid", "vs_source",
                   "consent", "mturk", "check1", "check2",
                   "llm_check1", "llm_check2"):
            return True
        if col.startswith("Q_"):
            return True
        # Respondent / panel tracking
        if col in ("psid", "transaction_id", "supplier_id", "mobile",
                   "ip_state", "ip_zip", "supplier", "supplier_resp_id",
                   "supplier_survey_id"):
            return True
        # Display order / flow logic
        if "_DO_" in col or col.startswith("FL_"):
            return True
        # Randomization / experimental
        if col in ("outparty", "past_alt", "rand_alt", "click_back_fn_vac",
                   "dur_end", "rand_blocks", "state_full", "month_day",
                   "month_n", "governor"):
            return True
        if col.startswith("rand_"):
            return True
        # Survey meta / admin
        if col.startswith("survey_") or col.startswith("timer_"):
            return True
        # Open-ended text
        if col.endswith("_TEXT"):
            return True
        # sm_quit_why: open-ended (no _TEXT suffix)
        if col.startswith("sm_quit_why_"):
            return True
        # Indexed multi-select (ambiguous without codebook)
        for prefix in ("sm_freq_mult", "sm_time_total",
                       "sm_post_mult", "sm_post_pol_mult"):
            if col.startswith(prefix):
                return True
        # Redundant / derived demographics already in export
        if col in ("age_cat_4", "age_cat_6", "gender_full", "female", "male",
                   "race_pac", "race_cat_4", "education", "income_cat_5",
                   "income_cat_4", "relation", "kids_n", "parent",
                   "democrat", "republican", "independent",
                   "phq_score", "depression",
                   "zip", "county", "zip_state", "state_id", "state",
                   "region", "fips", "ruca_usda", "urbanicity", "county_pop",
                   "year", "month", "loi_seconds", "loi_minutes",
                   "quality_flag", "return", "weight_state", "weight_vote",
                   "weight_vote_state", "born_us", "rur_urb", "cpi", "exp_cpi"):
            return True
        if col.startswith("house_") or col.startswith("religion_"):
            return True
        if col in ("employ", "employ3", "work_hybrid", "student",
                   "evang", "service", "jewish", "jewish_den", "hispanic",
                   "sex_or", "mena", "income", "trust",
                   "submarine", "submarine_DO_1", "submarine_DO_2"):
            return True
        return False

    return [c for c in w38_all_cols if not should_exclude(c)]


def main():
    print("Reading export file header...")
    with open(EXPORT_FILE, newline="", encoding="utf-8") as f:
        export_reader = csv.DictReader(f)
        export_cols = export_reader.fieldnames

    print("Reading W38 raw file...")
    with open(W38_FILE, newline="", encoding="utf-8") as f:
        w38_reader = csv.DictReader(f)
        w38_cols = w38_reader.fieldnames
        # Build id → row dict (all values kept as strings)
        w38_by_id = {row["id"]: row for row in w38_reader}

    export_cols_set = set(export_cols)
    new_cols = build_new_cols(export_cols_set, w38_cols)
    print(f"New columns to merge: {len(new_cols)}")

    out_cols = export_cols + new_cols
    print(f"Total output columns: {len(out_cols)}")
    print(f"Writing to {OUT_FILE} ...")

    matched = 0
    total  = 0
    with open(EXPORT_FILE, newline="", encoding="utf-8") as fin, \
         open(OUT_FILE, "w", newline="", encoding="utf-8") as fout:

        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=out_cols, extrasaction="ignore",
                                lineterminator="\n")
        writer.writeheader()

        for row in reader:
            total += 1
            # Merge W38 columns for wave-38 rows only
            if row["wave"] == "38":
                w38_row = w38_by_id.get(row["id"])
                if w38_row:
                    matched += 1
                    for col in new_cols:
                        row[col] = w38_row.get(col, "")
                else:
                    for col in new_cols:
                        row[col] = ""
            else:
                for col in new_cols:
                    row[col] = ""

            writer.writerow(row)

            if total % 100000 == 0:
                print(f"  Processed {total:,} rows, {matched:,} W38 matched...")

    print(f"\nDone. {total:,} total rows, {matched:,} W38 rows merged.")
    print(f"Output: {OUT_FILE}")


if __name__ == "__main__":
    main()
