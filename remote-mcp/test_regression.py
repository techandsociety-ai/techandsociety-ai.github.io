"""Unit + integration tests for regression helpers and MCP tools.

Tests are written around mathematical invariants and explicit behavioral
contracts — not surface-level checks like "returns JSON" or "R² ∈ [0,1]".

Run with:
    cd remote-mcp && .venv/bin/python -m pytest test_regression.py -v
"""

import asyncio
import json
import sys
import types
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Import server with BigQuery / auth patched out
# ---------------------------------------------------------------------------

def _import_server():
    bq_mod = types.ModuleType("google.cloud.bigquery")
    from unittest.mock import MagicMock
    bq_mod.Client = MagicMock()
    google_mod = types.ModuleType("google")
    cloud_mod = types.ModuleType("google.cloud")
    google_mod.cloud = cloud_mod
    cloud_mod.bigquery = bq_mod
    sys.modules.setdefault("google", google_mod)
    sys.modules.setdefault("google.cloud", cloud_mod)
    sys.modules.setdefault("google.cloud.bigquery", bq_mod)

    fastmcp_mod = types.ModuleType("fastmcp")
    class _NoOpMCP:
        def __init__(self, *args, **kwargs):
            pass
        def tool(self):
            return lambda f: f
    fastmcp_mod.FastMCP = _NoOpMCP
    sys.modules.setdefault("fastmcp", fastmcp_mod)

    for mod_name in [
        "fastmcp.server.auth",
        "fastmcp.server.auth.providers",
        "fastmcp.server.auth.providers.google",
    ]:
        m = types.ModuleType(mod_name)
        m.GoogleProvider = MagicMock()
        sys.modules.setdefault(mod_name, m)

    import importlib.util, pathlib, os
    orig_getenv = os.getenv

    def _disable_auth(k, default=None):
        if k == "DISABLE_AUTH":
            return "1"
        return orig_getenv(k, default)

    with patch("os.getenv", side_effect=_disable_auth):
        spec = importlib.util.spec_from_file_location(
            "server",
            pathlib.Path(__file__).parent / "server.py",
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

    return module


_server = _import_server()

wave_clause             = _server.wave_clause
_resolve_reference_level = _server._resolve_reference_level
_encode_predictors      = _server._encode_predictors
_CATEGORICAL_COLUMNS    = _server._CATEGORICAL_COLUMNS
run_ols_regression      = _server.run_ols_regression
run_logistic_regression = _server.run_logistic_regression


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ===========================================================================
# 1. wave_clause — SQL output contracts
# ===========================================================================

class TestWaveClause:
    def test_none_produces_empty_string(self):
        assert wave_clause(None) == ""

    def test_empty_string_produces_empty_string(self):
        assert wave_clause("") == ""

    def test_integer_wave_uses_float_cast_and_correct_value(self):
        sql = wave_clause("35")
        # Must use FLOAT64 cast (not bare equality on integer) to handle both
        # integer- and float-stored wave columns.
        assert "CAST(wave AS FLOAT64)" in sql
        assert "= 35.0" in sql

    def test_float_wave_preserves_decimal(self):
        sql = wave_clause("35.1")
        assert "CAST(wave AS FLOAT64)" in sql
        assert "35.1" in sql

    def test_sql_injection_string_raises_value_error(self):
        with pytest.raises(ValueError, match="must be a number"):
            wave_clause("35; DROP TABLE respondents")

    def test_alphabetic_string_raises_value_error(self):
        with pytest.raises(ValueError, match="must be a number"):
            wave_clause("wave35")

    def test_output_starts_with_and(self):
        # Fragment must be safe to append directly to WHERE … {wave_clause(w)}
        assert wave_clause("35").startswith("AND ")


# ===========================================================================
# 2. _resolve_reference_level — pure-logic contracts
# ===========================================================================

class TestResolveReferenceLevel:
    CATS = ["Democrat", "Independent", "Republican"]

    def test_valid_requested_level_is_returned_unchanged(self):
        assert _resolve_reference_level("party3", self.CATS, "Republican") == "Republican"

    def test_no_request_returns_first_alphabetical_element(self):
        # sorted CATS → Democrat first
        assert _resolve_reference_level("party3", self.CATS, None) == "Democrat"

    def test_unknown_request_falls_back_to_first_not_to_requested(self):
        result = _resolve_reference_level("party3", self.CATS, "Libertarian")
        assert result == "Democrat"   # NOT "Libertarian"

    def test_empty_available_with_no_request_returns_sentinel_string(self):
        # Guard against empty-column edge case
        assert _resolve_reference_level("party3", [], None) == "first"

    def test_empty_available_with_bad_request_returns_sentinel_string(self):
        assert _resolve_reference_level("party3", [], "Democrat") == "first"

    def test_single_category_available_is_returned(self):
        assert _resolve_reference_level("gender", ["Female"], "Female") == "Female"


# ===========================================================================
# 3. _encode_predictors — encoding correctness contracts
# ===========================================================================

# Controlled fixture: 3 gender values, uniform distribution, no noise
GENDER_CATS = ["Female", "Male", "Non-binary"]
PARTY_CATS  = ["Democrat", "Independent", "Republican"]

def _fixture_df():
    """Deterministic 30-row frame with gender (cat), party3 (cat), ideology (num)."""
    n_per_cat = 10
    gender  = GENDER_CATS * n_per_cat
    party3  = (PARTY_CATS * n_per_cat)[:30]
    ideology = list(range(1, 8)) * 4 + [1, 2]     # 30 values
    weight   = [1.0] * 30
    return pd.DataFrame({
        "gender":   gender,
        "party3":   party3,
        "ideology": [float(i) for i in ideology],
        "weight":   weight,
    })


class TestEncodePredicators:
    def setup_method(self):
        self.df = _fixture_df()

    # -- Column set with default reference (alphabetically first) ---------------

    def test_default_ref_is_dropped_female_for_gender(self):
        X, _, _ = _encode_predictors(self.df, ["gender"])
        assert "gender_Female" not in X.columns, \
            "Female is alpha-first → must be dropped as reference"
        assert set(X.columns) == {"gender_Male", "gender_Non-binary"}

    def test_explicit_male_ref_drops_male_keeps_female_and_nonbinary(self):
        X, _, _ = _encode_predictors(self.df, ["gender"],
                                     reference_levels={"gender": "Male"})
        assert "gender_Male" not in X.columns
        assert set(X.columns) == {"gender_Female", "gender_Non-binary"}

    def test_explicit_nonbinary_ref_drops_nonbinary(self):
        X, _, _ = _encode_predictors(self.df, ["gender"],
                                     reference_levels={"gender": "Non-binary"})
        assert "gender_Non-binary" not in X.columns
        assert set(X.columns) == {"gender_Female", "gender_Male"}

    # -- Dummy values are 0/1 floats and correctly indicate membership ----------

    def test_dummy_values_are_only_0_and_1(self):
        X, _, _ = _encode_predictors(self.df, ["gender"])
        unique_vals = set(X.values.flatten())
        assert unique_vals == {0.0, 1.0}

    def test_male_dummy_equals_1_exactly_where_gender_is_male(self):
        X, _, _ = _encode_predictors(self.df, ["gender"])
        male_mask = (self.df["gender"] == "Male").values
        assert (X["gender_Male"].values == male_mask.astype(float)).all()

    # -- Index alignment after encoding ----------------------------------------

    def test_output_index_matches_input_index_after_slice(self):
        sub = self.df.iloc[5:20].copy()
        X, _, _ = _encode_predictors(sub, ["gender"])
        assert list(X.index) == list(sub.index)

    # -- Numeric pass-through --------------------------------------------------

    def test_numeric_column_values_are_unchanged(self):
        X, _, _ = _encode_predictors(self.df, ["ideology"])
        pd.testing.assert_series_equal(
            X["ideology"], self.df["ideology"], check_names=False
        )

    def test_numeric_column_is_cast_to_float(self):
        X, _, _ = _encode_predictors(self.df, ["ideology"])
        assert X["ideology"].dtype == float

    # -- Notes ------------------------------------------------------------------

    def test_note_records_chosen_reference_category(self):
        _, notes, _ = _encode_predictors(self.df, ["gender"],
                                         reference_levels={"gender": "Male"})
        assert any("Male" in n and "reference" in n for n in notes)

    def test_note_records_fallback_category_when_invalid_ref_given(self):
        _, notes, _ = _encode_predictors(self.df, ["gender"],
                                         reference_levels={"gender": "Robot"})
        # Falls back to Female; note must say Female
        assert any("Female" in n and "reference" in n for n in notes)

    # -- Warnings ---------------------------------------------------------------

    def test_no_warnings_when_valid_ref_provided(self):
        _, _, warns = _encode_predictors(self.df, ["gender"],
                                         reference_levels={"gender": "Male"})
        assert warns == []

    def test_no_warnings_when_no_ref_provided(self):
        _, _, warns = _encode_predictors(self.df, ["gender"])
        assert warns == []

    def test_warning_generated_for_unknown_ref(self):
        _, _, warns = _encode_predictors(self.df, ["gender"],
                                         reference_levels={"gender": "Robot"})
        assert len(warns) == 1

    def test_warning_names_the_bad_requested_level(self):
        _, _, warns = _encode_predictors(self.df, ["gender"],
                                         reference_levels={"gender": "Robot"})
        assert "Robot" in warns[0]

    def test_warning_names_the_fallback_level(self):
        _, _, warns = _encode_predictors(self.df, ["gender"],
                                         reference_levels={"gender": "Robot"})
        assert "Female" in warns[0]   # alpha-first fallback

    def test_warning_only_for_invalid_column_not_for_valid_sibling(self):
        # party3 gets a valid ref; gender gets a bad ref → only one warning
        _, _, warns = _encode_predictors(
            self.df, ["gender", "party3"],
            reference_levels={"gender": "Robot", "party3": "Republican"}
        )
        assert len(warns) == 1

    # -- Two predictors mixed type ---------------------------------------------

    def test_mixed_predictors_column_count(self):
        X, _, _ = _encode_predictors(self.df, ["gender", "ideology"])
        # gender: 3 cats − 1 ref = 2 dummies; ideology: 1 numeric → 3 total
        assert X.shape[1] == 3

    # -- Changing ref doesn't change R² (encoding invariant) ------------------

    def test_different_ref_levels_produce_identical_dummy_count(self):
        X_female, _, _ = _encode_predictors(self.df, ["gender"])
        X_male,   _, _ = _encode_predictors(self.df, ["gender"],
                                            reference_levels={"gender": "Male"})
        assert X_female.shape == X_male.shape


# ===========================================================================
# 4. Integration tests — run_ols_regression
#    These use controlled DataFrames; the assertions are mathematical,
#    not just "the field exists".
# ===========================================================================

# Hand-crafted frame: 100 observations, constant weight, exactly two genders,
# outcome is purely determined by gender so we can predict exact coefficients.
def _ols_gender_df():
    """
    50 Female (outcome=2.0) + 50 Male (outcome=5.0), weight=1.
    True OLS: intercept=2, gender_Male=3 (when Female is reference).
    """
    return pd.DataFrame({
        "gender":       ["Female"] * 50 + ["Male"] * 50,
        "freq_facebook": [2.0] * 50 + [5.0] * 50,
        "weight":        [1.0] * 100,
    })


def _ols_numeric_df():
    """
    outcome = 1 + 2*ideology exactly, weight=1, n=100.
    True OLS: intercept≈1, ideology≈2.
    """
    ideology = list(range(1, 8)) * 14 + [1, 2]   # 100 values
    return pd.DataFrame({
        "ideology":      [float(i) for i in ideology],
        "freq_facebook": [1.0 + 2.0 * i for i in ideology],
        "weight":        [1.0] * 100,
    })


class TestRunOLSRegression:

    def _call(self, df, **kwargs):
        with patch.object(_server, "_fetch_regression_data", return_value=df):
            return json.loads(_run(run_ols_regression(**kwargs)))

    # -- Coefficient correctness on hand-crafted data -------------------------

    def test_numeric_predictor_coefficient_exact(self):
        """ideology=2 slope must be recovered to 4 decimal places."""
        data = self._call(
            _ols_numeric_df(),
            outcome="freq_facebook",
            predictors=["ideology"],
            use_weights=False,
        )
        coefs = {c["term"]: c["estimate"] for c in data["coefficients"]}
        assert abs(coefs["ideology"] - 2.0) < 1e-4

    def test_gender_coefficient_exact_female_reference(self):
        """gender_Male coefficient must equal exactly 3.0 (5-2) when Female is ref."""
        data = self._call(
            _ols_gender_df(),
            outcome="freq_facebook",
            predictors=["gender"],
            use_weights=False,
        )
        coefs = {c["term"]: c["estimate"] for c in data["coefficients"]}
        assert "gender_Male" in coefs
        assert abs(coefs["gender_Male"] - 3.0) < 1e-4

    def test_gender_coefficient_exact_male_reference(self):
        """gender_Female coefficient must equal -3.0 when Male is reference."""
        data = self._call(
            _ols_gender_df(),
            outcome="freq_facebook",
            predictors=["gender"],
            reference_levels={"gender": "Male"},
            use_weights=False,
        )
        coefs = {c["term"]: c["estimate"] for c in data["coefficients"]}
        assert "gender_Female" in coefs
        assert abs(coefs["gender_Female"] - (-3.0)) < 1e-4

    def test_r_squared_is_1_for_perfect_fit(self):
        """outcome = 1 + 2*ideology with no noise → R² must be 1.0."""
        data = self._call(
            _ols_numeric_df(),
            outcome="freq_facebook",
            predictors=["ideology"],
            use_weights=False,
        )
        assert abs(data["model_fit"]["r_squared"] - 1.0) < 1e-6

    def test_changing_reference_level_preserves_r_squared(self):
        """R² is an invariant of the model space; it must not change when ref changes."""
        r2_female = self._call(
            _ols_gender_df(),
            outcome="freq_facebook",
            predictors=["gender"],
            use_weights=False,
        )["model_fit"]["r_squared"]

        r2_male = self._call(
            _ols_gender_df(),
            outcome="freq_facebook",
            predictors=["gender"],
            reference_levels={"gender": "Male"},
            use_weights=False,
        )["model_fit"]["r_squared"]

        assert abs(r2_female - r2_male) < 1e-6

    # -- Coefficient sign symmetry when ref flips (binary predictor) ----------

    def test_coefficient_sign_flips_when_reference_flips(self):
        """For binary gender (only Female/Male), coef(Male|ref=Female) == -coef(Female|ref=Male)."""
        df = pd.DataFrame({
            "gender":        ["Female"] * 50 + ["Male"] * 50,
            "freq_facebook": [2.0] * 50 + [5.0] * 50,
            "weight":        [1.0] * 100,
        })
        coef_male = self._call(
            df, outcome="freq_facebook", predictors=["gender"], use_weights=False
        )
        coef_female = self._call(
            df, outcome="freq_facebook", predictors=["gender"],
            reference_levels={"gender": "Male"}, use_weights=False
        )
        male_est   = {c["term"]: c["estimate"] for c in coef_male["coefficients"]}["gender_Male"]
        female_est = {c["term"]: c["estimate"] for c in coef_female["coefficients"]}["gender_Female"]
        assert abs(male_est + female_est) < 1e-4

    # -- reference_levels_requested is echoed ---------------------------------

    def test_reference_levels_echoed_in_response(self):
        data = self._call(
            _ols_gender_df(),
            outcome="freq_facebook",
            predictors=["gender"],
            reference_levels={"gender": "Male"},
            use_weights=False,
        )
        assert data["reference_levels_requested"] == {"gender": "Male"}

    def test_reference_levels_none_echoed_as_null(self):
        data = self._call(
            _ols_gender_df(),
            outcome="freq_facebook",
            predictors=["gender"],
            use_weights=False,
        )
        assert data["reference_levels_requested"] is None

    # -- Warning propagation into notes ----------------------------------------

    def test_fallback_warning_appears_in_notes_field(self):
        data = self._call(
            _ols_gender_df(),
            outcome="freq_facebook",
            predictors=["gender"],
            reference_levels={"gender": "Robot"},
            use_weights=False,
        )
        assert any("Robot" in n for n in data["notes"])

    def test_no_warning_in_notes_for_valid_reference_level(self):
        data = self._call(
            _ols_gender_df(),
            outcome="freq_facebook",
            predictors=["gender"],
            reference_levels={"gender": "Male"},
            use_weights=False,
        )
        assert not any("Falling back" in n for n in data["notes"])

    # -- use_weights label in notes --------------------------------------------

    def test_weighted_note_says_wls(self):
        data = self._call(
            _ols_gender_df(),
            outcome="freq_facebook",
            predictors=["gender"],
            use_weights=True,
        )
        assert any("Weighted Least Squares" in n for n in data["notes"])
        assert not any("NOT survey-weighted" in n for n in data["notes"])

    def test_unweighted_note_warns_not_population_representative(self):
        data = self._call(
            _ols_gender_df(),
            outcome="freq_facebook",
            predictors=["gender"],
            use_weights=False,
        )
        assert any("NOT survey-weighted" in n for n in data["notes"])

    # -- Guard rails: invalid inputs -------------------------------------------

    def test_unknown_column_returns_error_with_column_name(self):
        data = self._call(
            _ols_gender_df(),
            outcome="freq_facebook",
            predictors=["not_a_real_column"],
        )
        assert "error" in data
        assert "not_a_real_column" in data["error"]

    def test_categorical_outcome_returns_error(self):
        data = self._call(
            _ols_gender_df(),
            outcome="gender",
            predictors=["freq_facebook"],
        )
        assert "error" in data
        assert "gender" in data["error"]


# ===========================================================================
# 5. Integration tests — run_logistic_regression
# ===========================================================================

def _logit_gender_df():
    """
    50 Female all use_facebook=0, 50 Male all use_facebook=1.
    True log-odds: gender_Male = +inf, but the model should converge with a
    large positive coefficient.  We use 49/50 splits to keep it finite.
    Female: 2 use=1, 48 use=0   →  log(2/48) ≈ -3.18
    Male:  48 use=1, 2  use=0   →  log(48/2) ≈  3.18
    log-odds(Male vs Female) ≈ 6.36
    """
    female = pd.DataFrame({
        "gender":       ["Female"] * 50,
        "use_facebook": [1.0] * 2 + [0.0] * 48,
        "weight":       [1.0] * 50,
    })
    male = pd.DataFrame({
        "gender":       ["Male"] * 50,
        "use_facebook": [1.0] * 48 + [0.0] * 2,
        "weight":       [1.0] * 50,
    })
    return pd.concat([female, male], ignore_index=True)


class TestRunLogisticRegression:

    def _call(self, df, **kwargs):
        with patch.object(_server, "_fetch_regression_data", return_value=df):
            return json.loads(_run(run_logistic_regression(**kwargs)))

    # -- Coefficient sign and log-odds / OR relationship ----------------------

    def test_male_log_odds_is_positive_when_male_more_likely(self):
        data = self._call(
            _logit_gender_df(),
            outcome="use_facebook",
            predictors=["gender"],
            use_weights=False,
        )
        coefs = {c["term"]: c["log_odds"] for c in data["coefficients"]}
        assert coefs["gender_Male"] > 3.0   # log(48/2) - log(2/48) ≈ 6.36

    def test_odds_ratio_equals_exp_of_log_odds(self):
        """OR must equal exp(log_odds) within relative tolerance.

        Both values are independently rounded to 6 d.p. in the server, so for
        large ORs the absolute difference can exceed 1e-4 even when correct.
        Relative tolerance of 1e-4 (0.01%) is appropriate.
        """
        data = self._call(
            _logit_gender_df(),
            outcome="use_facebook",
            predictors=["gender"],
            use_weights=False,
        )
        for coef in data["coefficients"]:
            expected_or = float(np.exp(coef["log_odds"]))
            rel_err = abs(coef["odds_ratio"] - expected_or) / max(expected_or, 1e-9)
            assert rel_err < 1e-4, \
                f"OR relative error {rel_err:.2e} on term {coef['term']}"

    def test_changing_reference_level_preserves_aic(self):
        """AIC measures model fit and must not change when only the reference level changes."""
        aic_female = self._call(
            _logit_gender_df(),
            outcome="use_facebook",
            predictors=["gender"],
            use_weights=False,
        )["model_fit"]["aic"]

        aic_male = self._call(
            _logit_gender_df(),
            outcome="use_facebook",
            predictors=["gender"],
            reference_levels={"gender": "Male"},
            use_weights=False,
        )["model_fit"]["aic"]

        assert abs(aic_female - aic_male) < 0.01

    def test_log_odds_sign_flips_when_reference_flips(self):
        """For binary gender, log_odds(Male|ref=Female) == -log_odds(Female|ref=Male)."""
        lo_male = self._call(
            _logit_gender_df(),
            outcome="use_facebook",
            predictors=["gender"],
            use_weights=False,
        )
        lo_female = self._call(
            _logit_gender_df(),
            outcome="use_facebook",
            predictors=["gender"],
            reference_levels={"gender": "Male"},
            use_weights=False,
        )
        male_coef   = {c["term"]: c["log_odds"] for c in lo_male["coefficients"]}["gender_Male"]
        female_coef = {c["term"]: c["log_odds"] for c in lo_female["coefficients"]}["gender_Female"]
        assert abs(male_coef + female_coef) < 1e-3

    # -- reference_levels_requested echoed ------------------------------------

    def test_reference_levels_echoed_in_response(self):
        data = self._call(
            _logit_gender_df(),
            outcome="use_facebook",
            predictors=["gender"],
            reference_levels={"gender": "Male"},
            use_weights=False,
        )
        assert data["reference_levels_requested"] == {"gender": "Male"}

    # -- Warning propagation --------------------------------------------------

    def test_fallback_warning_appears_in_notes(self):
        data = self._call(
            _logit_gender_df(),
            outcome="use_facebook",
            predictors=["gender"],
            reference_levels={"gender": "Robot"},
            use_weights=False,
        )
        assert any("Robot" in n for n in data["notes"])

    def test_no_fallback_warning_for_valid_ref(self):
        data = self._call(
            _logit_gender_df(),
            outcome="use_facebook",
            predictors=["gender"],
            reference_levels={"gender": "Male"},
            use_weights=False,
        )
        assert not any("Falling back" in n for n in data["notes"])

    # -- use_weights label in notes -------------------------------------------

    def test_weighted_note_says_glm_freq_weights(self):
        data = self._call(
            _logit_gender_df(),
            outcome="use_facebook",
            predictors=["gender"],
            use_weights=True,
        )
        assert any("GLM freq_weights" in n for n in data["notes"])
        assert not any("NOT survey-weighted" in n for n in data["notes"])

    def test_unweighted_note_warns_not_population_representative(self):
        data = self._call(
            _logit_gender_df(),
            outcome="use_facebook",
            predictors=["gender"],
            use_weights=False,
        )
        assert any("NOT survey-weighted" in n for n in data["notes"])

    # -- Guard rails ----------------------------------------------------------

    def test_ordinal_outcome_returns_error(self):
        data = self._call(
            _logit_gender_df(),
            outcome="freq_facebook",
            predictors=["gender"],
        )
        assert "error" in data
        assert "binary" in data["error"].lower() or "logistic" in data["error"].lower()

    def test_unknown_column_returns_error_with_column_name(self):
        data = self._call(
            _logit_gender_df(),
            outcome="use_facebook",
            predictors=["not_a_real_column"],
        )
        assert "error" in data
        assert "not_a_real_column" in data["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
