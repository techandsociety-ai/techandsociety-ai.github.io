"""
Generate synthetic survey data for CHIP50 project.

This script creates realistic synthetic data matching the structure of the
actual survey data, including demographics and substantive questions.
"""

import pandas as pd
import numpy as np
import uuid
from pathlib import Path


class SyntheticDataGenerator:
    """Generate synthetic survey data with realistic distributions."""

    def __init__(self, n_respondents=500, waves=[7, 8, 9], random_seed=42):
        """
        Initialize the synthetic data generator.

        Args:
            n_respondents: Number of unique respondents to generate
            waves: List of wave numbers to include
            random_seed: Random seed for reproducibility
        """
        self.n_respondents = n_respondents
        self.waves = waves
        self.random_seed = random_seed
        np.random.seed(random_seed)

        # Define realistic distributions for demographic variables
        self.age_categories = [
            "18 to 25", "26 to 30", "31 to 40", "41 to 50",
            "51 to 60", "61 to 70", "71 to 80", "81+"
        ]
        self.age_probs = [0.10, 0.12, 0.18, 0.20, 0.20, 0.13, 0.06, 0.01]

        self.education_categories = [
            "Less than High School", "High School Graduate",
            "Some College", "College Degree", "Graduate Degree"
        ]
        self.education_probs = [0.08, 0.27, 0.30, 0.22, 0.13]

        self.income_categories = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]  # 10 income brackets
        self.income_probs = [0.08, 0.10, 0.12, 0.14, 0.16, 0.14, 0.12, 0.08, 0.04, 0.02]

        self.gender_categories = ["Male", "Female", "Non-binary", "Prefer not to say"]
        self.gender_probs = [0.48, 0.50, 0.015, 0.005]

        self.party_categories = [1, 2, 3, 4, 5, 6, 7]  # 7-point party scale
        self.party_probs = [0.25, 0.15, 0.12, 0.15, 0.13, 0.10, 0.10]

        self.race_categories = [
            "White", "Black or African American", "Hispanic or Latino",
            "Asian", "Native American", "Other", "Two or more races"
        ]
        self.race_probs = [0.60, 0.13, 0.13, 0.06, 0.02, 0.02, 0.04]

        self.urban_types = ["Urban", "Suburban", "Rural"]
        self.urban_probs = [0.31, 0.52, 0.17]

        # US state codes (abbreviated list for diversity)
        self.state_codes = [
            "AL", "AK", "AZ", "CA", "CO", "FL", "GA", "IL", "IN", "KS",
            "KY", "MA", "MI", "MN", "MO", "NC", "NY", "OH", "PA", "TX",
            "VA", "WA", "WI"
        ]
        # State probabilities normalized to sum to 1.0
        raw_state_probs = [
            0.015, 0.002, 0.022, 0.118, 0.017, 0.065, 0.032, 0.038, 0.020, 0.009,
            0.013, 0.021, 0.030, 0.017, 0.018, 0.032, 0.059, 0.035, 0.039, 0.087,
            0.026, 0.023, 0.018
        ]
        # Normalize to ensure sum = 1.0
        total = sum(raw_state_probs)
        self.state_probs = [p / total for p in raw_state_probs]

    def generate_respondent_ids(self):
        """Generate unique respondent IDs using UUIDs."""
        return [str(uuid.uuid4()) for _ in range(self.n_respondents)]

    def generate_demographic_data(self, respondent_ids=None):
        """
        Generate synthetic demographic dataset.

        Args:
            respondent_ids: Optional list of respondent IDs to use. If None, generates new ones.

        Returns:
            DataFrame with demographic variables for all respondents across all waves
        """
        if respondent_ids is None:
            respondent_ids = self.generate_respondent_ids()

        # Generate base demographics (mostly stable across waves)
        base_demographics = pd.DataFrame({
            'id': respondent_ids,
            'age_cat_8': np.random.choice(self.age_categories, size=self.n_respondents, p=self.age_probs),
            'education_cat': np.random.choice(self.education_categories, size=self.n_respondents, p=self.education_probs),
            'gender': np.random.choice(self.gender_categories, size=self.n_respondents, p=self.gender_probs),
            'race': np.random.choice(self.race_categories, size=self.n_respondents, p=self.race_probs),
            'urban_type': np.random.choice(self.urban_types, size=self.n_respondents, p=self.urban_probs),
            'state_code': np.random.choice(self.state_codes, size=self.n_respondents, p=self.state_probs)
        })

        # Create data for each wave
        wave_data = []
        for wave in self.waves:
            wave_df = base_demographics.copy()
            wave_df['wave'] = wave

            # Income can change slightly across waves
            wave_df['income_cat_10'] = np.random.choice(
                self.income_categories,
                size=self.n_respondents,
                p=self.income_probs
            )

            # Party affiliation can shift slightly across waves
            wave_df['party_7'] = np.random.choice(
                self.party_categories,
                size=self.n_respondents,
                p=self.party_probs
            )

            # Generate survey weights (realistic range: 0.2 to 3.0)
            # Weights compensate for sampling bias
            wave_df['weight'] = np.random.gamma(shape=2, scale=0.5, size=self.n_respondents)
            wave_df['weight'] = np.clip(wave_df['weight'], 0.2, 3.0)

            wave_data.append(wave_df)

        # Combine all waves
        demographic_df = pd.concat(wave_data, ignore_index=True)

        # Reorder columns to match specification
        demographic_df = demographic_df[[
            'id', 'age_cat_8', 'education_cat', 'income_cat_10',
            'gender', 'party_7', 'race', 'urban_type', 'state_code',
            'wave', 'weight'
        ]]

        return demographic_df

    def generate_substantive_survey_data(self, respondent_ids=None):
        """
        Generate synthetic substantive survey data with various question types.

        Args:
            respondent_ids: Optional list of respondent IDs to use. If None, generates new ones.

        Returns:
            DataFrame with survey responses for all respondents across all waves
        """
        if respondent_ids is None:
            respondent_ids = self.generate_respondent_ids()
        n_total = self.n_respondents * len(self.waves)

        # Create base dataframe with ID and wave
        survey_data = []
        for wave in self.waves:
            for resp_id in respondent_ids:
                survey_data.append({'id': resp_id, 'wave': wave})

        survey_df = pd.DataFrame(survey_data)

        # Trust in institutions (1-5 scale: strongly distrust to strongly trust)
        institutions = ['trust_congress', 'trust_courts', 'trust_media', 'trust_military']
        for inst in institutions:
            survey_df[inst] = np.random.choice([1, 2, 3, 4, 5], size=n_total, p=[0.25, 0.30, 0.25, 0.15, 0.05])

        # Political figure approval (1-7 scale)
        figures = ['approval_pres', 'approval_governor', 'approval_senator']
        for fig in figures:
            survey_df[fig] = np.random.choice([1, 2, 3, 4, 5, 6, 7], size=n_total,
                                             p=[0.20, 0.15, 0.12, 0.10, 0.13, 0.15, 0.15])

        # Issue importance (0-10 scale)
        survey_df['issue_economy'] = np.random.choice(range(11), size=n_total,
                                                       p=[0.02, 0.02, 0.03, 0.05, 0.07, 0.10, 0.12, 0.15, 0.18, 0.16, 0.10])
        survey_df['issue_healthcare'] = np.random.choice(range(11), size=n_total,
                                                          p=[0.02, 0.02, 0.03, 0.05, 0.07, 0.10, 0.12, 0.15, 0.18, 0.16, 0.10])

        # Categorical responses (string)
        vote_intentions = ['Definitely will vote', 'Probably will vote', 'Unsure',
                          'Probably will not vote', 'Definitely will not vote']
        survey_df['vote_intention'] = np.random.choice(vote_intentions, size=n_total,
                                                       p=[0.35, 0.30, 0.15, 0.12, 0.08])

        # Binary response
        survey_df['registered_voter'] = np.random.choice([1, 0], size=n_total, p=[0.78, 0.22])

        # Continuous variable (thermometer rating 0-100)
        survey_df['party_thermometer'] = np.random.beta(a=2, b=2, size=n_total) * 100

        return survey_df

    def save_data(self, output_dir='synthetic_data'):
        """
        Generate and save both demographic and substantive survey datasets.

        Args:
            output_dir: Directory to save the CSV files
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        print(f"Generating synthetic data for {self.n_respondents} respondents across waves {self.waves}...")

        # Generate respondent IDs once to use for both datasets
        respondent_ids = self.generate_respondent_ids()
        print(f"Generated {len(respondent_ids)} unique respondent IDs")

        # Generate demographic data
        print("Generating demographic dataset...")
        demographic_df = self.generate_demographic_data(respondent_ids)
        demo_file = output_path / 'synthetic_demographics.csv'
        demographic_df.to_csv(demo_file, index=False)
        print(f"  Saved: {demo_file} ({len(demographic_df)} rows)")

        # Generate substantive survey data
        print("Generating substantive survey dataset...")
        survey_df = self.generate_substantive_survey_data(respondent_ids)
        survey_file = output_path / 'synthetic_survey_responses.csv'
        survey_df.to_csv(survey_file, index=False)
        print(f"  Saved: {survey_file} ({len(survey_df)} rows)")

        # Display sample data
        print("\nSample demographic data:")
        print(demographic_df.head(4).to_string())
        print("\nSample survey response data:")
        print(survey_df.head(4).to_string())

        return demographic_df, survey_df


if __name__ == '__main__':
    # Generate synthetic data
    generator = SyntheticDataGenerator(n_respondents=500, waves=[7, 8, 9])
    demographic_df, survey_df = generator.save_data()

    print("\n" + "="*60)
    print("Synthetic data generation complete!")
    print("="*60)
    print(f"Demographics: {len(demographic_df)} rows")
    print(f"Survey responses: {len(survey_df)} rows")
    print(f"\nFiles saved in: synthetic_data/")
