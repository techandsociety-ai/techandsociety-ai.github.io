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
    from unittest.mock import MagicMock
    bq_mod = types.ModuleType("google.cloud.bigquery")
    bq_mod.Client = MagicMock()
    gcs_mod = types.ModuleType("google.cloud.storage")
    gcs_mod.Client = MagicMock()
    google_mod = types.ModuleType("google")
    cloud_mod = types.ModuleType("google.cloud")
    google_mod.cloud = cloud_mod
    cloud_mod.bigquery = bq_mod
    cloud_mod.storage = gcs_mod
    sys.modules.setdefault("google", google_mod)
    sys.modules.setdefault("google.cloud", cloud_mod)
    sys.modules.setdefault("google.cloud.bigquery", bq_mod)
    sys.modules.setdefault("google.cloud.storage", gcs_mod)

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
        "fastmcp.server.auth.oauth_proxy",
        "fastmcp.server.auth.oauth_proxy.models",
    ]:
        m = types.ModuleType(mod_name)
        m.GoogleProvider = MagicMock()
        m.ProxyDCRClient = MagicMock()
        sys.modules.setdefault(mod_name, m)

    for mod_name in [
        "key_value",
        "key_value.aio",
        "key_value.aio.stores",
        "key_value.aio.stores.firestore",
    ]:
        m = types.ModuleType(mod_name)
        m.FirestoreStore = MagicMock()
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

wave_clause              = _server.wave_clause
_resolve_reference_level = _server._resolve_reference_level
_encode_predictors       = _server._encode_predictors
_CATEGORICAL_COLUMNS     = _server._CATEGORICAL_COLUMNS
run_ols_regression       = _server.run_ols_regression
run_logistic_regression  = _server.run_logistic_regression
create_recoded_variable  = _server.create_recoded_variable
delete_recoded_variable  = _server.delete_recoded_variable
_generate_crosstab_impl  = _server._generate_crosstab_impl
generate_crosstab_multi  = _server.generate_crosstab_multi


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


# ===========================================================================
# 6. _build_binary_recode_sql — SQL output contracts
# ===========================================================================

class TestBuildBinaryRecodeSql:
    _fn = staticmethod(_server._build_binary_recode_sql)

    def test_vaccine_get_mapping_produces_correct_sql(self):
        """vaccine_get: 1/2/4/5 → 1 (vaccinated), 3 → 0 (not)."""
        sql = self._fn("vaccine_get", {"1": "1", "2": "1", "4": "1", "5": "1", "3": "0"})
        assert "THEN 1" in sql
        assert "THEN 0" in sql
        # 1 must appear before 0 in the clause order
        assert sql.index("THEN 1") < sql.index("THEN 0")

    def test_output_is_unquoted_integers_not_strings(self):
        """Numeric 0/1 must appear unquoted so BigQuery returns INT64, not STRING."""
        sql = self._fn("vaccine_get", {"1": "1", "3": "0"})
        assert "THEN '1'" not in sql
        assert "THEN '0'" not in sql
        assert "THEN 1" in sql
        assert "THEN 0" in sql

    def test_kff_vacc1_binary_sql(self):
        sql = self._fn("kff_vacc1", {"1": "1", "2": "0"})
        assert "kff_vacc1 IN (1)" in sql
        assert "kff_vacc1 IN (2)" in sql

    def test_raises_for_non_binary_mapping_values(self):
        with pytest.raises(ValueError, match="0.*1|must be"):
            self._fn("col", {"1": "vaccinated", "2": "not"})

    def test_raises_for_mixed_valid_and_invalid_values(self):
        with pytest.raises(ValueError):
            self._fn("col", {"1": "1", "2": "yes"})

    def test_else_null_is_present(self):
        sql = self._fn("vaccine_get", {"1": "1", "3": "0"})
        assert "ELSE NULL END" in sql

    def test_multiple_source_values_grouped_in_one_in_clause(self):
        """Source values mapping to the same label must be IN (...) not separate WHENs."""
        sql = self._fn("vaccine_get", {"1": "1", "2": "1", "4": "1", "5": "1", "3": "0"})
        # The four vaccinated values (1,2,4,5) must share one WHEN ... IN clause
        when_1_clause = [c for c in sql.split("WHEN") if "THEN 1" in c]
        assert len(when_1_clause) == 1
        in_values = when_1_clause[0]
        for v in ("1", "2", "4", "5"):
            assert v in in_values


# ===========================================================================
# 7. create_recoded_variable(binary=True) — registration contracts
# ===========================================================================

class TestCreateRecodedVariableBinary:
    """Tests that create/delete keep the five server-side sets consistent."""

    VACC_MAPPING = {"1": "1", "2": "1", "4": "1", "5": "1", "3": "0"}

    def setup_method(self):
        # Clean up any leftover from a prior test
        if "test_vaccinated" in _server._RECODED_VARIABLE_NAMES:
            _run(delete_recoded_variable("test_vaccinated"))

    def teardown_method(self):
        if "test_vaccinated" in _server._RECODED_VARIABLE_NAMES:
            _run(delete_recoded_variable("test_vaccinated"))

    def _create(self, **kwargs):
        return json.loads(_run(create_recoded_variable(
            name="test_vaccinated",
            source_column="vaccine_get",
            mapping=self.VACC_MAPPING,
            binary=True,
            **kwargs,
        )))

    def test_creation_succeeds_and_returns_binary_true(self):
        result = self._create()
        assert result["binary"] is True

    def test_added_to_binary_columns(self):
        self._create()
        assert "test_vaccinated" in _server._BINARY_COLUMNS

    def test_not_added_to_categorical_columns(self):
        self._create()
        assert "test_vaccinated" not in _server._CATEGORICAL_COLUMNS

    def test_added_to_all_regression_columns(self):
        self._create()
        assert "test_vaccinated" in _server._ALL_REGRESSION_COLUMNS

    def test_added_to_ordinal_tool_columns(self):
        self._create()
        assert "test_vaccinated" in _server._ORDINAL_TOOL_COLUMNS

    def test_added_to_recoded_variable_names(self):
        self._create()
        assert "test_vaccinated" in _server._RECODED_VARIABLE_NAMES

    def test_derived_columns_entry_has_binary_true(self):
        self._create()
        assert _server._DERIVED_COLUMNS["test_vaccinated"]["binary"] is True

    def test_derived_sql_contains_then_1_and_then_0(self):
        self._create()
        sql = _server._DERIVED_COLUMNS["test_vaccinated"]["sql"]
        assert "THEN 1" in sql
        assert "THEN 0" in sql

    def test_delete_removes_from_binary_columns(self):
        self._create()
        _run(delete_recoded_variable("test_vaccinated"))
        assert "test_vaccinated" not in _server._BINARY_COLUMNS

    def test_delete_removes_from_ordinal_tool_columns(self):
        self._create()
        _run(delete_recoded_variable("test_vaccinated"))
        assert "test_vaccinated" not in _server._ORDINAL_TOOL_COLUMNS

    def test_delete_removes_from_all_regression_columns(self):
        self._create()
        _run(delete_recoded_variable("test_vaccinated"))
        assert "test_vaccinated" not in _server._ALL_REGRESSION_COLUMNS

    def test_raises_for_binary_with_ranges(self):
        with pytest.raises((ValueError, Exception)):
            _run(create_recoded_variable(
                name="test_vaccinated",
                source_column="running_water_pct",
                ranges=[{"label": "Low", "min": 0, "max": 50}],
                binary=True,
            ))

    def test_raises_for_non_binary_mapping_values(self):
        with pytest.raises((ValueError, Exception)):
            _run(create_recoded_variable(
                name="test_vaccinated",
                source_column="vaccine_get",
                mapping={"1": "vaccinated", "3": "not"},
                binary=True,
            ))


# ===========================================================================
# 8. run_logistic_regression accepts user-defined binary recodes as outcome
# ===========================================================================

def _vacc_df():
    """
    100 rows: vaccine_get source → vaccinated 0/1 already recoded.
    60 vaccinated (1), 40 not (0).  Female more vaccinated than Male.
    """
    female = pd.DataFrame({
        "test_vaccinated": [1.0] * 35 + [0.0] * 15,
        "gender":          ["Female"] * 50,
        "weight":          [1.0] * 50,
    })
    male = pd.DataFrame({
        "test_vaccinated": [1.0] * 25 + [0.0] * 25,
        "gender":          ["Male"] * 50,
        "weight":          [1.0] * 50,
    })
    return pd.concat([female, male], ignore_index=True)


class TestLogisticRegressionWithBinaryRecode:

    def setup_method(self):
        if "test_vaccinated" not in _server._BINARY_COLUMNS:
            _run(create_recoded_variable(
                name="test_vaccinated",
                source_column="vaccine_get",
                mapping={"1": "1", "2": "1", "4": "1", "5": "1", "3": "0"},
                binary=True,
            ))

    def teardown_method(self):
        if "test_vaccinated" in _server._RECODED_VARIABLE_NAMES:
            _run(delete_recoded_variable("test_vaccinated"))

    def _call(self, df, **kwargs):
        with patch.object(_server, "_fetch_regression_data", return_value=df):
            return json.loads(_run(run_logistic_regression(**kwargs)))

    def test_binary_recode_accepted_as_outcome(self):
        data = self._call(
            _vacc_df(),
            outcome="test_vaccinated",
            predictors=["gender"],
            use_weights=False,
        )
        assert "error" not in data

    def test_female_positive_coefficient_when_more_vaccinated(self):
        """Female is more vaccinated (35/50 vs 25/50) → gender_Male log_odds should be negative."""
        data = self._call(
            _vacc_df(),
            outcome="test_vaccinated",
            predictors=["gender"],
            use_weights=False,
        )
        coefs = {c["term"]: c["log_odds"] for c in data["coefficients"]}
        assert coefs["gender_Male"] < 0

    def test_non_binary_recode_still_rejected_as_outcome(self):
        """A normal (non-binary) recode must not be accepted as a logistic outcome."""
        _run(create_recoded_variable(
            name="test_age_3",
            source_column="age_cat_8",
            mapping={"18-24": "young", "25-34": "young", "35-64": "mid", "65+": "old"},
        ))
        try:
            data = self._call(
                _vacc_df(),
                outcome="test_age_3",
                predictors=["gender"],
            )
            assert "error" in data
        finally:
            if "test_age_3" in _server._RECODED_VARIABLE_NAMES:
                _run(delete_recoded_variable("test_age_3"))


# ===========================================================================
# 9. _generate_crosstab_impl / generate_crosstab_multi accept binary recodes
# ===========================================================================

def _crosstab_vacc_df():
    """
    Fake crosstab result: 3 water-decile buckets × vaccinated rate.
    Returned by the mocked run_query.
    """
    return pd.DataFrame({
        "demographic_value": ["Low", "Medium", "High"],
        "unweighted_n":      [120, 130, 110],
        "weighted_n":        [120.0, 130.0, 110.0],
        "weighted_users":    [60.0, 78.0, 88.0],
        "weighted_non_users":[60.0, 52.0, 22.0],
        "user_rate_pct":     [50.0, 60.0, 80.0],
        "suppressed":        [False, False, False],
    })


class TestCrosstabWithBinaryRecode:

    def setup_method(self):
        # Create binary recode for vaccination
        if "test_vaccinated" not in _server._BINARY_COLUMNS:
            _run(create_recoded_variable(
                name="test_vaccinated",
                source_column="vaccine_get",
                mapping={"1": "1", "2": "1", "4": "1", "5": "1", "3": "0"},
                binary=True,
            ))
        # Create categorical recode for water decile
        if "test_water_band" not in _server._RECODED_VARIABLE_NAMES:
            _run(create_recoded_variable(
                name="test_water_band",
                source_column="running_water_pct",
                ranges=[
                    {"label": "Low",    "min": 0,  "max": 50},
                    {"label": "Medium", "min": 50, "max": 80},
                    {"label": "High",   "min": 80, "max": 101},
                ],
            ))

    def teardown_method(self):
        for name in ("test_vaccinated", "test_water_band"):
            if name in _server._RECODED_VARIABLE_NAMES:
                _run(delete_recoded_variable(name))

    def test_generate_crosstab_accepts_binary_recode_as_platform(self):
        with patch.object(_server, "run_query", return_value=_crosstab_vacc_df()):
            result = json.loads(_run(_generate_crosstab_impl(
                platform="test_vaccinated",
                demographic="test_water_band",
            )))
        assert "error" not in result
        assert result["platform"] == "test_vaccinated"

    def test_generate_crosstab_returns_user_rate_pct(self):
        with patch.object(_server, "run_query", return_value=_crosstab_vacc_df()):
            result = json.loads(_run(_generate_crosstab_impl(
                platform="test_vaccinated",
                demographic="test_water_band",
            )))
        rates = [row["user_rate_pct"] for row in result["data"]]
        assert rates == [50.0, 60.0, 80.0]

    def test_generate_crosstab_still_rejects_unknown_platform(self):
        with pytest.raises((ValueError, Exception)):
            _run(_generate_crosstab_impl(
                platform="not_a_real_variable",
                demographic="gender",
            ))

    def test_generate_crosstab_still_rejects_ordinal_as_platform(self):
        """freq_facebook is ordinal, not binary — must be rejected."""
        with pytest.raises((ValueError, Exception)):
            _run(_generate_crosstab_impl(
                platform="freq_facebook",
                demographic="gender",
            ))

    def test_generate_crosstab_multi_accepts_binary_recode_as_variable(self):
        multi_df = _crosstab_vacc_df().rename(columns={"demographic_value": "gender"})
        multi_df["party3"] = "Democrat"
        with patch.object(_server, "run_query", return_value=multi_df):
            result = json.loads(_run(generate_crosstab_multi(
                variable="test_vaccinated",
                demographics=["gender", "party3"],
            )))
        assert "error" not in result
        assert result["result_type"] == "adoption_rate"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
