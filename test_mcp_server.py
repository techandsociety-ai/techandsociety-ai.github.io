#!/usr/bin/env python3
"""
Test script for CHIP50 Survey MCP Server

This script tests the MCP server tools using the synthetic data.
"""

import sys
import os
from pathlib import Path

# Add lib directory to path
lib_path = Path(__file__).parent / "mcp_server" / "lib"
sys.path.insert(0, str(lib_path))

import asyncio
import json


async def test_crosstab():
    """Test cross-tabulation functionality."""
    print("=" * 60)
    print("Testing: generate_crosstab")
    print("=" * 60)

    # Import server
    sys.path.insert(0, str(Path(__file__).parent / "mcp_server"))
    from server import SurveyAnalysisServer

    server = SurveyAnalysisServer()

    # Test case 1: Trust in Congress by Party
    print("\nTest 1: Trust in Congress by Party (weighted)")
    result = await server.generate_crosstab(
        demographics_csv="synthetic_data/synthetic_demographics.csv",
        survey_csv="synthetic_data/synthetic_survey_responses.csv",
        survey_variable="trust_congress",
        demographic_variable="party_7",
        waves=[7, 8, 9],
        use_weights=True,
        show_percentages=True
    )
    print(json.dumps(result, indent=2))

    # Test case 2: Approval by Education
    print("\n" + "-" * 60)
    print("Test 2: Presidential Approval by Education (unweighted)")
    result = await server.generate_crosstab(
        demographics_csv="synthetic_data/synthetic_demographics.csv",
        survey_csv="synthetic_data/synthetic_survey_responses.csv",
        survey_variable="approval_pres",
        demographic_variable="education_cat",
        use_weights=False,
        show_percentages=True
    )
    print(json.dumps(result, indent=2))

    # Test case 3: Vote Intention by Age
    print("\n" + "-" * 60)
    print("Test 3: Vote Intention by Age Category")
    result = await server.generate_crosstab(
        demographics_csv="synthetic_data/synthetic_demographics.csv",
        survey_csv="synthetic_data/synthetic_survey_responses.csv",
        survey_variable="vote_intention",
        demographic_variable="age_cat_8",
        waves=[9],  # Latest wave only
        use_weights=True,
        show_percentages=True
    )
    print(json.dumps(result, indent=2))


async def test_summary_stats():
    """Test summary statistics functionality."""
    print("\n" + "=" * 60)
    print("Testing: get_summary_statistics")
    print("=" * 60)

    sys.path.insert(0, str(Path(__file__).parent / "mcp_server"))
    from server import SurveyAnalysisServer

    server = SurveyAnalysisServer()

    # Test: Summary stats for trust variables
    print("\nTest: Summary statistics for trust variables")
    result = await server.get_summary_statistics(
        demographics_csv="synthetic_data/synthetic_demographics.csv",
        survey_csv="synthetic_data/synthetic_survey_responses.csv",
        survey_variables=[
            "trust_congress",
            "trust_courts",
            "trust_media",
            "trust_military"
        ],
        waves=[7, 8, 9],
        use_weights=True
    )
    print(json.dumps(result, indent=2))

    # Test: Summary stats for approval variables
    print("\n" + "-" * 60)
    print("Test: Summary statistics for approval ratings")
    result = await server.get_summary_statistics(
        demographics_csv="synthetic_data/synthetic_demographics.csv",
        survey_csv="synthetic_data/synthetic_survey_responses.csv",
        survey_variables=[
            "approval_pres",
            "approval_governor",
            "approval_senator"
        ],
        use_weights=True
    )
    print(json.dumps(result, indent=2))


def test_data_files():
    """Verify synthetic data files exist and are valid."""
    print("=" * 60)
    print("Testing: Data Files")
    print("=" * 60)

    demo_path = Path("synthetic_data/synthetic_demographics.csv")
    survey_path = Path("synthetic_data/synthetic_survey_responses.csv")

    print(f"\nChecking demographics file: {demo_path}")
    if demo_path.exists():
        import pandas as pd
        df = pd.read_csv(demo_path)
        print(f"  ✓ File exists: {len(df)} rows, {len(df.columns)} columns")
        print(f"  Columns: {', '.join(df.columns[:5])}...")
        print(f"  Waves: {sorted(df['wave'].unique())}")
        print(f"  Unique respondents: {df['id'].nunique()}")
    else:
        print(f"  ✗ File not found!")

    print(f"\nChecking survey file: {survey_path}")
    if survey_path.exists():
        import pandas as pd
        df = pd.read_csv(survey_path)
        print(f"  ✓ File exists: {len(df)} rows, {len(df.columns)} columns")
        print(f"  Question variables: {len(df.columns) - 2}")
        print(f"  Sample questions: {', '.join([c for c in df.columns if c not in ['id', 'wave']][:5])}")
        print(f"  Waves: {sorted(df['wave'].unique())}")
    else:
        print(f"  ✗ File not found!")


async def main():
    """Run all tests."""
    print("\n")
    print("=" * 60)
    print("CHIP50 MCP SERVER TEST SUITE")
    print("=" * 60)

    # Test 1: Verify data files
    test_data_files()

    # Test 2: Cross-tabulation
    await test_crosstab()

    # Test 3: Summary statistics
    await test_summary_stats()

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)
    print("\nNote: BigQuery upload test skipped (requires GCP credentials)")
    print("To test BigQuery upload, run:")
    print("  1. Set up GCP credentials: gcloud auth application-default login")
    print("  2. Create a test project and dataset")
    print("  3. Use the MCP tool: upload_csv_to_bigquery")


if __name__ == "__main__":
    asyncio.run(main())
