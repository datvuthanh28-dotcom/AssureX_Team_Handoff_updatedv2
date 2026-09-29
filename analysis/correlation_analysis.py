from __future__ import annotations
from pathlib import Path
import json
import math
import numpy as np
import pandas as pd
try:
    from scipy.stats import chi2_contingency, spearmanr, pearsonr
except ImportError as exc:
    raise ImportError(
        "scipy is required for correlation analysis. "
        "Install it with: python3 -m pip install scipy"
    ) from exc
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLEAN_PATH = PROJECT_ROOT / "data" / "cleaned" / "assurex_clean.csv"
OUT_DIR = PROJECT_ROOT / "data" / "correlation"
OUT_DIR.mkdir(parents=True, exist_ok=True)
NUMERIC_PAIR_PATH = OUT_DIR / "numeric_pairwise_correlation.csv"
NUMERIC_MATRIX_PATH = OUT_DIR / "pearson_matrix.csv"
SPEARMAN_MATRIX_PATH = OUT_DIR / "spearman_matrix.csv"
CATEGORICAL_PAIR_PATH = OUT_DIR / "categorical_cramers_v.csv"
REDUNDANCY_PATH = OUT_DIR / "redundancy_candidates.csv"
SUMMARY_PATH = OUT_DIR / "correlation_summary.csv"
MANIFEST_PATH = OUT_DIR / "correlation_manifest.json"
TARGET = "ClaimClass"
IDENTIFIER_COLUMNS = {
    "RecordID",
    "ClaimID",
    "CustomerID",
    "ProductID",
    "ModelNumber",
    "SerialNumber",
    "InternalBatchCode",
}
DATE_COLUMNS = {
    "PurchaseDate",
    "ClaimDate",
    "FaultDate",
}
KNOWN_NOISE_COLUMNS = {
    "BrowserFamily",
    "SubmissionMinute",
    "UiTheme",
    "RandomScore",
    "InternalBatchCode",
}
STRONG_NUMERIC_THRESHOLD = 0.80
VERY_STRONG_NUMERIC_THRESHOLD = 0.90
STRONG_CATEGORICAL_THRESHOLD = 0.70
VERY_STRONG_CATEGORICAL_THRESHOLD = 0.85
MIN_PAIR_OBSERVATIONS = 30


def read_clean_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        keep_default_na=False,
        na_values=[""],
    )


def safe_numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def infer_feature_types(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    numeric_columns: list[str] = []
    categorical_columns: list[str] = []
    excluded = IDENTIFIER_COLUMNS | DATE_COLUMNS | {TARGET}
    for column in df.columns:
        if column in excluded:
            continue
        series = df[column]
        non_missing = int(series.notna().sum())
        if non_missing == 0:
            continue
        numeric = safe_numeric_series(series)
        numeric_ratio = float(numeric.notna().sum()) / float(non_missing)
        if numeric_ratio >= 0.95:
            numeric_columns.append(column)
        else:
            categorical_columns.append(column)
    return numeric_columns, categorical_columns


def safe_corr_pair(
    x: pd.Series,
    y: pd.Series,
    method: str,
) -> tuple[float, float, int]:
    pair = pd.DataFrame({"x": x, "y": y}).dropna()
    n = len(pair)
    if n < MIN_PAIR_OBSERVATIONS:
        return np.nan, np.nan, n
    if pair["x"].nunique() <= 1 or pair["y"].nunique() <= 1:
        return np.nan, np.nan, n
    try:
        if method == "pearson":
            r, p = pearsonr(pair["x"], pair["y"])
        elif method == "spearman":
            result = spearmanr(pair["x"], pair["y"])
            r = result.statistic
            p = result.pvalue
        else:
            raise ValueError(f"Unsupported method: {method}")
    except Exception:
        return np.nan, np.nan, n
    return float(r), float(p), n


def numeric_pairwise_report(
    df: pd.DataFrame,
    numeric_columns: list[str],
) -> pd.DataFrame:
    rows = []
    for i, col_a in enumerate(numeric_columns):
        for col_b in numeric_columns[i + 1:]:
            a = safe_numeric_series(df[col_a])
            b = safe_numeric_series(df[col_b])
            pearson_r, pearson_p, n_pearson = safe_corr_pair(
                a, b, "pearson"
            )
            spearman_r, spearman_p, n_spearman = safe_corr_pair(
                a, b, "spearman"
            )
            n = min(n_pearson, n_spearman)
            abs_pearson = abs(pearson_r) if np.isfinite(pearson_r) else np.nan
            abs_spearman = abs(spearman_r) if np.isfinite(spearman_r) else np.nan
            strongest = np.nanmax(
                [abs_pearson, abs_spearman]
            ) if (
                np.isfinite(abs_pearson)
                or np.isfinite(abs_spearman)
            ) else np.nan
            if np.isfinite(strongest) and strongest >= VERY_STRONG_NUMERIC_THRESHOLD:
                strength = "Very strong"
            elif np.isfinite(strongest) and strongest >= STRONG_NUMERIC_THRESHOLD:
                strength = "Strong"
            elif np.isfinite(strongest) and strongest >= 0.50:
                strength = "Moderate"
            elif np.isfinite(strongest):
                strength = "Weak"
            else:
                strength = "Insufficient"
            rows.append({
                "FeatureA": col_a,
                "FeatureB": col_b,
                "N": n,
                "PearsonR": pearson_r,
                "PearsonPValue": pearson_p,
                "AbsPearsonR": abs_pearson,
                "SpearmanRho": spearman_r,
                "SpearmanPValue": spearman_p,
                "AbsSpearmanRho": abs_spearman,
                "MaxAbsoluteAssociation": strongest,
                "Strength": strength,
                "RedundancyCandidate": bool(
                    np.isfinite(strongest)
                    and strongest >= STRONG_NUMERIC_THRESHOLD
                ),
            })
    if not rows:
        return pd.DataFrame(columns=[
            "FeatureA",
            "FeatureB",
            "N",
            "PearsonR",
            "PearsonPValue",
            "AbsPearsonR",
            "SpearmanRho",
            "SpearmanPValue",
            "AbsSpearmanRho",
            "MaxAbsoluteAssociation",
            "Strength",
            "RedundancyCandidate",
        ])
    return (
        pd.DataFrame(rows)
        .sort_values(
            ["MaxAbsoluteAssociation", "FeatureA", "FeatureB"],
            ascending=[False, True, True],
        )
        .reset_index(drop=True)
    )


def cramers_v_corrected(
    x: pd.Series,
    y: pd.Series,
) -> tuple[float, float, int, int, int]:
    pair = pd.DataFrame({"x": x, "y": y}).dropna()
    n = len(pair)
    if n < MIN_PAIR_OBSERVATIONS:
        return np.nan, np.nan, n, 0, 0
    table = pd.crosstab(pair["x"], pair["y"])
    r, k = table.shape
    if r <= 1 or k <= 1:
        return np.nan, np.nan, n, r, k
    try:
        chi2, p_value, _, _ = chi2_contingency(
            table,
            correction=False,
        )
    except ValueError:
        return np.nan, np.nan, n, r, k
    phi2 = chi2 / n
    phi2_corr = max(
        0.0,
        phi2 - ((k - 1) * (r - 1)) / max(n - 1, 1),
    )
    r_corr = r - ((r - 1) ** 2) / max(n - 1, 1)
    k_corr = k - ((k - 1) ** 2) / max(n - 1, 1)
    denominator = min(k_corr - 1, r_corr - 1)
    if denominator <= 0:
        return np.nan, float(p_value), n, r, k
    v = math.sqrt(phi2_corr / denominator)
    return float(v), float(p_value), n, r, k


def categorical_pairwise_report(
    df: pd.DataFrame,
    categorical_columns: list[str],
) -> pd.DataFrame:
    rows = []
    for i, col_a in enumerate(categorical_columns):
        for col_b in categorical_columns[i + 1:]:
            v, p_value, n, levels_a, levels_b = cramers_v_corrected(
                df[col_a],
                df[col_b],
            )
            if np.isfinite(v) and v >= VERY_STRONG_CATEGORICAL_THRESHOLD:
                strength = "Very strong"
            elif np.isfinite(v) and v >= STRONG_CATEGORICAL_THRESHOLD:
                strength = "Strong"
            elif np.isfinite(v) and v >= 0.40:
                strength = "Moderate"
            elif np.isfinite(v):
                strength = "Weak"
            else:
                strength = "Insufficient"
            rows.append({
                "FeatureA": col_a,
                "FeatureB": col_b,
                "N": n,
                "LevelsA": levels_a,
                "LevelsB": levels_b,
                "CramersV": v,
                "ChiSquarePValue": p_value,
                "Strength": strength,
                "RedundancyCandidate": bool(
                    np.isfinite(v)
                    and v >= STRONG_CATEGORICAL_THRESHOLD
                ),
            })
    if not rows:
        return pd.DataFrame(columns=[
            "FeatureA",
            "FeatureB",
            "N",
            "LevelsA",
            "LevelsB",
            "CramersV",
            "ChiSquarePValue",
            "Strength",
            "RedundancyCandidate",
        ])
    return (
        pd.DataFrame(rows)
        .sort_values(
            ["CramersV", "FeatureA", "FeatureB"],
            ascending=[False, True, True],
        )
        .reset_index(drop=True)
    )


def correlation_matrix(
    df: pd.DataFrame,
    numeric_columns: list[str],
    method: str,
) -> pd.DataFrame:
    if not numeric_columns:
        return pd.DataFrame()
    numeric_df = pd.DataFrame({
        c: safe_numeric_series(df[c])
        for c in numeric_columns
    })
    return numeric_df.corr(
        method=method,
        min_periods=MIN_PAIR_OBSERVATIONS,
    )


def build_redundancy_candidates(
    numeric_pairs: pd.DataFrame,
    categorical_pairs: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    if not numeric_pairs.empty:
        selected = numeric_pairs[
            numeric_pairs["RedundancyCandidate"] == True
        ]
        for _, row in selected.iterrows():
            rows.append({
                "AssociationType": "Numeric-Numeric",
                "FeatureA": row["FeatureA"],
                "FeatureB": row["FeatureB"],
                "PrimaryMeasure": row["MaxAbsoluteAssociation"],
                "MeasureName": "max(|Pearson|, |Spearman|)",
                "Strength": row["Strength"],
                "Action": "Review later; do not drop automatically",
            })
    if not categorical_pairs.empty:
        selected = categorical_pairs[
            categorical_pairs["RedundancyCandidate"] == True
        ]
        for _, row in selected.iterrows():
            rows.append({
                "AssociationType": "Categorical-Categorical",
                "FeatureA": row["FeatureA"],
                "FeatureB": row["FeatureB"],
                "PrimaryMeasure": row["CramersV"],
                "MeasureName": "CramersV",
                "Strength": row["Strength"],
                "Action": "Review later; do not drop automatically",
            })
    if not rows:
        return pd.DataFrame(columns=[
            "AssociationType",
            "FeatureA",
            "FeatureB",
            "PrimaryMeasure",
            "MeasureName",
            "Strength",
            "Action",
        ])
    return (
        pd.DataFrame(rows)
        .sort_values(
            ["PrimaryMeasure", "FeatureA", "FeatureB"],
            ascending=[False, True, True],
        )
        .reset_index(drop=True)
    )


def main():
    print("=" * 72)
    print("ASSUREX - CORRELATION ANALYSIS")
    print("=" * 72)
    if not CLEAN_PATH.exists():
        raise FileNotFoundError(
            f"Clean dataset not found:\n{CLEAN_PATH}\n"
            "Run preprocessing/clean_data.py first."
        )
    df = read_clean_csv(CLEAN_PATH)
    if df.empty:
        raise ValueError("Clean dataset is empty.")
    if "ClaimID" in df.columns and df["ClaimID"].duplicated().any():
        raise ValueError(
            "Duplicate ClaimID values found. Resolve cleaning before "
            "correlation analysis."
        )
    numeric_columns, categorical_columns = infer_feature_types(df)
    numeric_pairs = numeric_pairwise_report(
        df,
        numeric_columns,
    )
    categorical_pairs = categorical_pairwise_report(
        df,
        categorical_columns,
    )
    pearson_matrix = correlation_matrix(
        df,
        numeric_columns,
        "pearson",
    )
    spearman_matrix = correlation_matrix(
        df,
        numeric_columns,
        "spearman",
    )
    redundancy = build_redundancy_candidates(
        numeric_pairs,
        categorical_pairs,
    )
    numeric_pairs.to_csv(
        NUMERIC_PAIR_PATH,
        index=False,
        encoding="utf-8-sig",
    )
    categorical_pairs.to_csv(
        CATEGORICAL_PAIR_PATH,
        index=False,
        encoding="utf-8-sig",
    )
    pearson_matrix.to_csv(
        NUMERIC_MATRIX_PATH,
        encoding="utf-8-sig",
    )
    spearman_matrix.to_csv(
        SPEARMAN_MATRIX_PATH,
        encoding="utf-8-sig",
    )
    redundancy.to_csv(
        REDUNDANCY_PATH,
        index=False,
        encoding="utf-8-sig",
    )
    strong_numeric = (
        int(numeric_pairs["RedundancyCandidate"].sum())
        if not numeric_pairs.empty
        else 0
    )
    strong_categorical = (
        int(categorical_pairs["RedundancyCandidate"].sum())
        if not categorical_pairs.empty
        else 0
    )
    summary = pd.DataFrame([
        {"Metric": "Rows", "Value": len(df)},
        {"Metric": "NumericFeaturesAnalyzed", "Value": len(numeric_columns)},
        {"Metric": "CategoricalFeaturesAnalyzed", "Value": len(categorical_columns)},
        {"Metric": "NumericPairsAnalyzed", "Value": len(numeric_pairs)},
        {"Metric": "CategoricalPairsAnalyzed", "Value": len(categorical_pairs)},
        {"Metric": "StrongNumericRedundancyCandidates", "Value": strong_numeric},
        {"Metric": "StrongCategoricalRedundancyCandidates", "Value": strong_categorical},
        {"Metric": "TotalRedundancyCandidates", "Value": len(redundancy)},
        {"Metric": "TargetUsed", "Value": "NO"},
        {"Metric": "FeaturesRemoved", "Value": "NO"},
    ])
    summary.to_csv(
        SUMMARY_PATH,
        index=False,
        encoding="utf-8-sig",
    )
    manifest = {
        "input": str(CLEAN_PATH),
        "rows": int(len(df)),
        "numeric_features": numeric_columns,
        "categorical_features": categorical_columns,
        "excluded_identifiers": sorted(
            [c for c in IDENTIFIER_COLUMNS if c in df.columns]
        ),
        "excluded_dates": sorted(
            [c for c in DATE_COLUMNS if c in df.columns]
        ),
        "target": TARGET,
        "target_used": False,
        "thresholds": {
            "strong_numeric": STRONG_NUMERIC_THRESHOLD,
            "very_strong_numeric": VERY_STRONG_NUMERIC_THRESHOLD,
            "strong_categorical_cramers_v": STRONG_CATEGORICAL_THRESHOLD,
            "very_strong_categorical_cramers_v": VERY_STRONG_CATEGORICAL_THRESHOLD,
        },
        "rules": {
            "features_removed": False,
            "feature_engineering_performed": False,
            "feature_selection_performed": False,
            "training_performed": False,
        },
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Rows                         : {len(df)}")
    print(f"Numeric features analyzed    : {len(numeric_columns)}")
    print(f"Categorical features analyzed: {len(categorical_columns)}")
    print(f"Numeric pairs analyzed       : {len(numeric_pairs)}")
    print(f"Categorical pairs analyzed   : {len(categorical_pairs)}")
    print(f"Strong numeric candidates    : {strong_numeric}")
    print(f"Strong categorical candidates: {strong_categorical}")
    print(f"Total redundancy candidates  : {len(redundancy)}")
    print("Target used                   : NO")
    print("Features removed              : NO")
    if not redundancy.empty:
        print("\nTop redundancy candidates:")
        for _, row in redundancy.head(10).iterrows():
            print(
                f" - {row['FeatureA']} <-> {row['FeatureB']}: "
                f"{row['MeasureName']}={row['PrimaryMeasure']:.4f}"
            )
    else:
        print("\nNo strong redundancy candidates at configured thresholds.")
    print("\nCreated:")
    for path in [
        SUMMARY_PATH,
        NUMERIC_PAIR_PATH,
        NUMERIC_MATRIX_PATH,
        SPEARMAN_MATRIX_PATH,
        CATEGORICAL_PAIR_PATH,
        REDUNDANCY_PATH,
        MANIFEST_PATH,
    ]:
        print(f" - {path}")
    print("\nIMPORTANT:")
    print(" - This stage only identifies feature-feature associations.")
    print(" - ClaimClass was excluded from correlation calculations.")
    print(" - Correlation does not imply causation.")
    print(" - Strong association is only a redundancy candidate.")
    print(" - Do not remove features yet.")
    print(" - Next stage: FEATURE ENGINEERING.")
if __name__ == "__main__":
    main()
