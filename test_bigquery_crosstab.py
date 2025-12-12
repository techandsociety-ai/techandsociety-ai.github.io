#!/usr/bin/env python3
"""
Test script for BigQuery crosstab functionality.

This demonstrates the BigQuery-based weighted tabulation that joins
demographics and survey_responses tables.
"""

from google.cloud import bigquery
import pandas as pd


def test_bigquery_crosstab():
    """Test the BigQuery crosstab query."""

    # Configuration
    project_id = "nanocentury"
    dataset_id = "chip50"
    demographics_table = "demographics"
    survey_table = "survey_responses"

    # Example: Trust in Congress by Party
    survey_variable = "trust_congress"
    demographic_variable = "party_7"

    client = bigquery.Client(project=project_id)

    # Build the query
    base_join = f"""
    SELECT
        d.{demographic_variable},
        s.{survey_variable},
        d.weight
    FROM `{project_id}.{dataset_id}.{demographics_table}` d
    INNER JOIN `{project_id}.{dataset_id}.{survey_table}` s
        ON d.id = s.id AND d.wave = s.wave
    WHERE d.{demographic_variable} IS NOT NULL
        AND s.{survey_variable} IS NOT NULL
    """

    # Weighted crosstab query
    query = f"""
    WITH joined_data AS ({base_join})
    SELECT
        {demographic_variable},
        {survey_variable},
        SUM(weight) as weighted_count,
        SUM(SUM(weight)) OVER (PARTITION BY {demographic_variable}) as demographic_total
    FROM joined_data
    GROUP BY {demographic_variable}, {survey_variable}
    ORDER BY {demographic_variable}, {survey_variable}
    """

    print("Executing query:")
    print(query)
    print("\n" + "="*80 + "\n")

    # Execute query
    query_job = client.query(query)
    results = query_job.result()

    # Convert to DataFrame
    df = results.to_dataframe()

    # Calculate percentages
    df['percentage'] = (df['weighted_count'] / df['demographic_total'] * 100).round(2)

    print("Raw results:")
    print(df.to_string())
    print("\n" + "="*80 + "\n")

    # Create pivot table for display
    pivot_counts = df.pivot(
        index=demographic_variable,
        columns=survey_variable,
        values='weighted_count'
    ).fillna(0)

    pivot_percentages = df.pivot(
        index=demographic_variable,
        columns=survey_variable,
        values='percentage'
    ).fillna(0)

    print(f"\n{survey_variable} by {demographic_variable} (Weighted Counts):")
    print(pivot_counts.to_string())

    print(f"\n{survey_variable} by {demographic_variable} (Percentages):")
    print(pivot_percentages.to_string())

    # Combined display
    print(f"\n{survey_variable} by {demographic_variable} (Combined):")
    for demo_cat in pivot_counts.index:
        print(f"\n{demographic_variable} = {demo_cat}:")
        for survey_cat in pivot_counts.columns:
            count_val = pivot_counts.loc[demo_cat, survey_cat]
            pct_val = pivot_percentages.loc[demo_cat, survey_cat]
            print(f"  {survey_variable} = {survey_cat}: {count_val:.1f} ({pct_val:.1f}%)")

    # Calculate total N
    total_n_query = f"""
    WITH joined_data AS ({base_join})
    SELECT COUNT(*) as total_n
    FROM joined_data
    """
    total_n_job = client.query(total_n_query)
    total_n_result = list(total_n_job.result())[0]

    print(f"\n\nTotal respondents: {total_n_result['total_n']}")

    # Marginal totals
    print(f"\nMarginal totals by {demographic_variable}:")
    marginal_totals = df.groupby(demographic_variable)['weighted_count'].sum()
    for cat, total in marginal_totals.items():
        print(f"  {cat}: {total:.1f}")


if __name__ == "__main__":
    print("Testing BigQuery Crosstab Functionality")
    print("="*80)
    print()

    try:
        test_bigquery_crosstab()
        print("\n✓ Test completed successfully!")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
