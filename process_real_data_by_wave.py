#!/usr/bin/env python3
"""
Process real CHIP50 survey data by wave for BigQuery upload.

This script:
1. Loads each CSV file separately (CSP_W35.csv, CSP_W35.1.csv, etc.)
2. Splits data into demographics and survey responses
3. Removes identifying information per privacy requirements
4. Saves separate files for each wave

Each wave gets its own output files:
- chip50_demographics_w35_TIMESTAMP.csv
- chip50_survey_responses_w35_TIMESTAMP.csv
- chip50_demographics_w35_1_TIMESTAMP.csv
- chip50_survey_responses_w35_1_TIMESTAMP.csv
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime
from typing import Tuple


class CHIP50WaveProcessor:
    """Process individual CHIP50 wave data with privacy protections."""

    # Demographic variables to keep (safe, non-identifying)
    DEMOGRAPHIC_VARS = [
        'id',
        'wave',
        'age_cat_4',
        'age_cat_6',
        'age_cat_8',
        'gender',
        'gender_full',
        'female',
        'male',
        'race_asian',
        'race_black',
        'race_natam',
        'race_pac',
        'race_white',
        'race_other',
        'race_hisp',
        'race_cat_4',
        'education',
        'education_cat',
        'income_cat_10',
        'income_cat_5',
        'income_cat_4',
        'relation',
        'kids_n',
        'parent',
        'party7',
        'party3',
        'democrat',
        'republican',
        'independent',
        'state_code',
        'region',
        'urbanicity',
        'urban_type',
        'year',
        'month',
        'weight',
        'weight_state',
        'weight_vote',
        'weight_vote_state'
    ]

    # Variables to EXCLUDE (identifying information)
    IDENTIFYING_VARS = [
        'StartDate',
        'EndDate',
        'RecordedDate',
        'IPAddress',
        'LocationLatitude',
        'LocationLongitude',
        'ResponseId',
        'ExternalReference',
        'zip',
        'county',
        'zip_state',
        'state_id',
        'state',
        'fips',
        'county_pop',
        'supplier_resp_id',
        'supplier_survey_id',
        'vsid',
        'vs_source',
        'source',
        'psid',
        'transaction_id',
        'supplier_id',
        'ip_state',
        'ip_zip',
        'Q_RecaptchaScore',
        'Q_RelevantIDDuplicate',
        'Q_RelevantIDDuplicateScore',
        'Q_RelevantIDFraudScore',
        'Q_RelevantIDLastStartDate',
        'dur_end',
        'loi_seconds',
        'loi_minutes',
        'gender_s_6_TEXT',
        'party_4_TEXT',
        'voted24_3_TEXT',
        'support24_3_TEXT',
        'voted20_3_TEXT',
        'support20_3_TEXT',
        'race_other_TEXT',
        'gender_full_TEXT',
        'religion_23_TEXT',
        'religion_24_TEXT',
        'jewish_den_4_TEXT'
    ]

    DO_PATTERN = '_DO_'
    FL_PATTERN = 'FL_'

    def __init__(self, output_dir: Path = None):
        """Initialize the wave processor."""
        self.output_dir = Path(output_dir) if output_dir else Path("data/processed")
        self.output_dir.mkdir(exist_ok=True)

    def is_metadata_column(self, col: str) -> bool:
        """Check if column is Qualtrics metadata that should be removed."""
        return (
            self.DO_PATTERN in col or
            self.FL_PATTERN in col or
            col.startswith('Q_') or
            col.startswith('timer_')
        )

    def normalize_wave_for_filename(self, wave: str) -> str:
        """Convert wave number to filename-safe format."""
        return wave.replace('.', '_')

    def extract_demographics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract demographic variables from full dataset."""
        available_demo_vars = [col for col in self.DEMOGRAPHIC_VARS if col in df.columns]
        print(f"  Extracting {len(available_demo_vars)} demographic variables")
        demo_df = df[available_demo_vars].copy()

        # Handle missingness codes: replace -99 with empty string (will become NULL in BigQuery)
        demo_df = demo_df.replace('-99', '')

        return demo_df

    def extract_survey_responses(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract survey response variables (non-demographic, non-identifying)."""
        all_cols = set(df.columns)
        remaining_cols = all_cols - set(self.DEMOGRAPHIC_VARS)
        remaining_cols = remaining_cols - set(self.IDENTIFYING_VARS)
        remaining_cols = {col for col in remaining_cols if not self.is_metadata_column(col)}

        final_cols = ['id', 'wave'] + sorted(list(remaining_cols - {'id', 'wave'}))
        available_cols = [col for col in final_cols if col in df.columns]

        print(f"  Extracting {len(available_cols)} survey response variables")
        survey_df = df[available_cols].copy()

        # Handle missingness codes: replace -99 with empty string (will become NULL in BigQuery)
        survey_df = survey_df.replace('-99', '')

        return survey_df

    def process_wave_file(self, wave_file: Path) -> Tuple[pd.DataFrame, pd.DataFrame, str]:
        """
        Process a single wave file.

        Returns:
            Tuple of (demographics_df, survey_responses_df, wave_number)
        """
        print(f"\n{'='*70}")
        print(f"Processing: {wave_file.name}")
        print(f"{'='*70}")

        # Extract wave number from filename
        match = re.search(r'CSP_W([\d.]+)\.csv', wave_file.name)
        if not match:
            raise ValueError(f"Cannot extract wave number from {wave_file.name}")

        wave_num = match.group(1)
        print(f"Wave number: {wave_num}")

        # Load data
        print(f"Loading CSV file...")
        df = pd.read_csv(wave_file, dtype=str, low_memory=False)
        print(f"  Loaded {len(df)} rows, {len(df.columns)} columns")

        # Ensure wave column exists
        if 'wave' not in df.columns:
            df['wave'] = wave_num
            print(f"  Added wave column with value: {wave_num}")

        # Split into demographics and survey responses
        demographics = self.extract_demographics(df)
        survey_responses = self.extract_survey_responses(df)

        # Remove rows with missing id or wave
        initial_demo_count = len(demographics)
        initial_survey_count = len(survey_responses)

        demographics = demographics.dropna(subset=['id', 'wave'])
        survey_responses = survey_responses.dropna(subset=['id', 'wave'])

        if len(demographics) < initial_demo_count:
            print(f"  Removed {initial_demo_count - len(demographics)} rows with missing id/wave from demographics")

        if len(survey_responses) < initial_survey_count:
            print(f"  Removed {initial_survey_count - len(survey_responses)} rows with missing id/wave from survey responses")

        print(f"\nProcessed data:")
        print(f"  Demographics: {len(demographics)} rows, {len(demographics.columns)} columns")
        print(f"  Survey responses: {len(survey_responses)} rows, {len(survey_responses.columns)} columns")

        return demographics, survey_responses, wave_num

    def save_wave_data(
        self,
        demographics: pd.DataFrame,
        survey_responses: pd.DataFrame,
        wave_num: str
    ) -> Tuple[Path, Path]:
        """
        Save processed wave data to CSV files.

        Args:
            demographics: Demographics DataFrame
            survey_responses: Survey responses DataFrame
            wave_num: Wave number (e.g., "35" or "35.1")

        Returns:
            Tuple of (demographics_path, survey_responses_path)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        wave_suffix = self.normalize_wave_for_filename(wave_num)

        demo_path = self.output_dir / f"chip50_demographics_w{wave_suffix}_{timestamp}.csv"
        survey_path = self.output_dir / f"chip50_survey_responses_w{wave_suffix}_{timestamp}.csv"

        print(f"\nSaving processed wave {wave_num} data...")
        print(f"  Demographics: {demo_path}")
        demographics.to_csv(demo_path, index=False)

        print(f"  Survey responses: {survey_path}")
        survey_responses.to_csv(survey_path, index=False)

        return demo_path, survey_path


def main():
    """Main processing function."""
    # Configuration
    data_dir = Path(__file__).parent / "data"

    print("CHIP50 Wave-by-Wave Data Processor")
    print("=" * 70)
    print(f"Data directory: {data_dir}")

    # Find all wave files
    wave_files = sorted(data_dir.glob("CSP_W*.csv"))

    if not wave_files:
        print(f"\n✗ Error: No wave files found in {data_dir}")
        print("Expected files like: CSP_W35.csv, CSP_W35.1.csv")
        return

    print(f"\nFound {len(wave_files)} wave file(s):")
    for f in wave_files:
        print(f"  - {f.name}")

    # Initialize processor
    processor = CHIP50WaveProcessor()

    # Process each wave
    processed_files = []
    for wave_file in wave_files:
        try:
            demographics, survey_responses, wave_num = processor.process_wave_file(wave_file)
            demo_path, survey_path = processor.save_wave_data(demographics, survey_responses, wave_num)
            processed_files.append({
                'wave': wave_num,
                'demo_path': demo_path,
                'survey_path': survey_path
            })
        except Exception as e:
            print(f"\n✗ Error processing {wave_file.name}: {e}")
            continue

    # Print summary
    print("\n" + "=" * 70)
    print("PROCESSING COMPLETE")
    print("=" * 70)

    if processed_files:
        print(f"\n✓ Successfully processed {len(processed_files)} wave(s):")
        for pf in processed_files:
            print(f"\n  Wave {pf['wave']}:")
            print(f"    Demographics:      {pf['demo_path'].name}")
            print(f"    Survey responses:  {pf['survey_path'].name}")

        print("\n" + "=" * 70)
        print("NEXT STEPS")
        print("=" * 70)
        print("""
1. Upload to BigQuery (each wave gets its own tables):
   python upload_real_data_by_wave.py

2. Create protected views for each wave:
   bq query --project_id=chip50 < sql/create_demographics_protected_w35.sql
   bq query --project_id=chip50 < sql/create_survey_responses_protected_w35.sql
   bq query --project_id=chip50 < sql/create_demographics_protected_w35_1.sql
   bq query --project_id=chip50 < sql/create_survey_responses_protected_w35_1.sql

3. Test the data:
   python test_bigquery_crosstab.py
""")
    else:
        print("\n✗ No waves were processed successfully")


if __name__ == "__main__":
    main()
