"""Rebuild HC3-robust multivariable regressions for Airbnb Promise Gap.

The main predictor is the model-derived negative_promise_share.
A sensitivity predictor, verified_negative_share, is calculated only from
evidence_valid=True positive/negative/mixed promise rows.

Requires: numpy, pandas, scipy.
Run from the project root or invoke this file directly.
"""
from __future__ import annotations

import ast
import csv
import json
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
from scipy.stats import t as student_t
from scipy.stats import spearmanr


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "project" else SCRIPT_DIR
OUTPUT = ROOT / "project" / "analysis_outputs"
LISTING_FILE = OUTPUT / "listing_level_analysis_2000.csv"
FIRST_PROMISES = ROOT / "results" / "batches" / "qwen35_4b_1000" / "promises_all_1000_corrected.csv"
NEXT_BATCHES = ROOT / "results" / "batches" / "qwen35_4b_next"
MIN_CATEGORY_N = 20
OUTCOMES = (
    "review_scores_rating",
    "review_scores_accuracy",
    "review_scores_cleanliness",
    "review_scores_checkin",
    "review_scores_communication",
    "review_scores_location",
    "review_scores_value",
)


def read_promise_files() -> pd.DataFrame:
    files = [FIRST_PROMISES, *sorted(NEXT_BATCHES.glob("part_*/promises.csv"))]
    missing = [str(path) for path in files if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing promise files: " + ", ".join(missing))
    frames = [pd.read_csv(path, dtype=str, encoding="utf-8-sig") for path in files]
    promises = pd.concat(frames, ignore_index=True)
    promises["promise_norm"] = promises["promise"].fillna("").str.casefold().str.strip()
    promises = promises[~promises["promise_norm"].isin({"short claim", "..."})].copy()
    promises["evidence_valid_bool"] = promises["evidence_valid"].fillna("").str.casefold().eq("true")
    return promises


def attach_verified_share(listings: pd.DataFrame, promises: pd.DataFrame) -> pd.DataFrame:
    valid = promises[
        promises["evidence_valid_bool"]
        & promises["label"].isin({"positive", "negative", "mixed"})
    ]
    counts = valid.groupby(["listing_id", "label"]).size().unstack(fill_value=0)
    for label in ("positive", "negative", "mixed"):
        if label not in counts:
            counts[label] = 0
    denominator = counts["positive"] + counts["negative"] + counts["mixed"]
    counts["verified_negative_share"] = counts["negative"] / denominator.replace(0, np.nan)
    counts["verified_negative_count"] = counts["negative"]
    counts["verified_valid_label_count"] = denominator
    counts.index = counts.index.astype(str)

    listings = listings.copy()
    listings["listing_id"] = listings["listing_id"].astype(str)
    listings = listings.drop(
        columns=["verified_negative_share", "verified_negative_count", "verified_valid_label_count"],
        errors="ignore",
    )
    return listings.merge(
        counts[["verified_negative_share", "verified_negative_count", "verified_valid_label_count"]],
        left_on="listing_id",
        right_index=True,
        how="left",
    )


def pool_rare(series: pd.Series) -> pd.Series:
    counts = series.value_counts(dropna=False)
    return series.where(series.map(counts) >= MIN_CATEGORY_N, "Other (<20)")


def design_matrix(frame: pd.DataFrame, outcome: str, predictor: str):
    columns = [
        np.ones(len(frame)),
        frame[predictor].astype(float).to_numpy(),
        np.log1p(frame["number_of_reviews"].astype(float).to_numpy()),
    ]
    names = ["intercept", predictor, "log1p(number_of_reviews)"]
    for category_column in (
        "room_type_pooled",
        "property_type_pooled",
        "neighbourhood_cleansed_pooled",
    ):
        levels = sorted(frame[category_column].dropna().unique().tolist())
        for level in levels[1:]:
            columns.append((frame[category_column].to_numpy() == level).astype(float))
            names.append(f"{category_column}={level}")
    return np.column_stack(columns), frame[outcome].astype(float).to_numpy(), names


def fit_hc3(frame: pd.DataFrame, outcome: str, predictor: str) -> dict:
    x, y, names = design_matrix(frame, outcome, predictor)
    rank = int(np.linalg.matrix_rank(x))
    if rank != x.shape[1]:
        raise ValueError(
            f"Rank-deficient design for {outcome}/{predictor}: "
            f"rank={rank}, columns={x.shape[1]}"
        )

    xtx_inverse = np.linalg.inv(x.T @ x)
    beta = xtx_inverse @ x.T @ y
    residuals = y - x @ beta
    leverage = np.einsum("ij,jk,ik->i", x, xtx_inverse, x)
    if np.max(leverage) >= 1:
        raise ValueError(
            f"HC3 undefined because max leverage >= 1 for {outcome}/{predictor}: "
            f"{np.max(leverage)}"
        )

    meat = x.T @ (((residuals / (1 - leverage)) ** 2)[:, None] * x)
    covariance = xtx_inverse @ meat @ xtx_inverse
    standard_errors = np.sqrt(np.diag(covariance))
    df_resid = len(y) - rank
    t_values = beta / standard_errors
    p_values = 2 * student_t.sf(np.abs(t_values), df=df_resid)
    critical = student_t.ppf(0.975, df=df_resid)

    coefficients = []
    for name, estimate, se, t_value, p_value in zip(
        names, beta, standard_errors, t_values, p_values
    ):
        coefficients.append({
            "term": name,
            "estimate": float(estimate),
            "hc3_se": float(se),
            "t_value": float(t_value),
            "p_value": float(p_value),
            "ci95_low": float(estimate - critical * se),
            "ci95_high": float(estimate + critical * se),
        })

    return {
        "n": int(len(y)),
        "df_resid": int(df_resid),
        "rank": rank,
        "n_columns": int(x.shape[1]),
        "r_squared": float(1 - np.sum(residuals ** 2) / np.sum((y - y.mean()) ** 2)),
        "max_leverage": float(np.max(leverage)),
        "coefficients": coefficients,
    }


def holm_adjust(p_values: list[float]) -> list[float]:
    order = np.argsort(p_values)
    adjusted = np.empty(len(p_values), dtype=float)
    running = 0.0
    m = len(p_values)
    for rank, idx in enumerate(order):
        value = min(1.0, (m - rank) * p_values[idx])
        running = max(running, value)
        adjusted[idx] = running
    return adjusted.tolist()


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    listings = pd.read_csv(LISTING_FILE, dtype={"listing_id": str})
    promises = read_promise_files()
    listings = attach_verified_share(listings, promises)
    listings.to_csv(LISTING_FILE, index=False, encoding="utf-8-sig")

    completed = listings.dropna(
        subset=["negative_promise_share", "review_scores_rating"]
    ).copy()
    for column in ("room_type", "property_type", "neighbourhood_cleansed"):
        completed[column + "_pooled"] = pool_rare(completed[column])

    results = {}
    summary_rows = []
    for predictor in ("negative_promise_share", "verified_negative_share"):
        usable = completed.dropna(subset=[predictor]).copy()
        model_results = {}
        for outcome in OUTCOMES:
            model_results[outcome] = fit_hc3(usable, outcome, predictor)

        p_values = [
            next(c["p_value"] for c in model_results[outcome]["coefficients"]
                 if c["term"] == predictor)
            for outcome in OUTCOMES
        ]
        adjusted = holm_adjust(p_values)

        for outcome, adjusted_p in zip(OUTCOMES, adjusted):
            result = model_results[outcome]
            coefficient = next(
                c for c in result["coefficients"] if c["term"] == predictor
            )
            coefficient["p_holm_7_outcomes"] = float(adjusted_p)
            result["predictor"] = predictor
            result["formula"] = (
                f"{outcome} ~ {predictor} + log1p(number_of_reviews) + "
                "room_type_pooled + property_type_pooled + neighbourhood_cleansed_pooled"
            )
            summary_rows.append({
                "predictor": predictor,
                "outcome": outcome,
                "n": result["n"],
                "r_squared": result["r_squared"],
                "coefficient": coefficient["estimate"],
                "hc3_se": coefficient["hc3_se"],
                "ci95_low": coefficient["ci95_low"],
                "ci95_high": coefficient["ci95_high"],
                "p_value": coefficient["p_value"],
                "p_holm_7_outcomes": adjusted_p,
                "max_leverage": result["max_leverage"],
                "n_parameters": result["n_columns"],
                "rank": result["rank"],
            })
        results[predictor] = model_results

    (OUTPUT / "multivariable_regression_2000.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    pd.DataFrame(summary_rows).to_csv(
        OUTPUT / "multivariable_regression_summary.csv",
        index=False, encoding="utf-8-sig"
    )
    print("Updated listing-level verified metrics and HC3 regression outputs.")
    print(f"Main sample n={results['negative_promise_share'][OUTCOMES[0]]['n']}")
    print(f"Verified sample n={results['verified_negative_share'][OUTCOMES[0]]['n']}")


if __name__ == "__main__":
    main()
