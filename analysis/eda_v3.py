from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLEAN_PATH = PROJECT_ROOT / "data" / "cleaned" / "assurex_v3_clean.csv"
EDA_DIR = PROJECT_ROOT / "data" / "eda_v3"
EDA_DIR.mkdir(parents=True, exist_ok=True)
SUMMARY_PATH = EDA_DIR / "eda_summary.csv"
COLUMN_PROFILE_PATH = EDA_DIR / "column_profile.csv"
NUMERIC_PATH = EDA_DIR / "numeric_summary.csv"
CATEGORICAL_PATH = EDA_DIR / "categorical_summary.csv"
MISSING_PATH = EDA_DIR / "missing_summary.csv"
CLASS_PATH = EDA_DIR / "class_distribution.csv"
OUTLIER_PATH = EDA_DIR / "numeric_outlier_summary.csv"
EDA_MANIFEST_PATH = EDA_DIR / "eda_manifest.json"
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


def read_clean_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        keep_default_na=False,
        na_values=[""],
    )


def infer_role(column: str, series: pd.Series) -> str:
    if column == TARGET:
        return "Target"
    if column in IDENTIFIER_COLUMNS:
        return "Identifier"
    if column in DATE_COLUMNS:
        return "Date"
    if column in KNOWN_NOISE_COLUMNS:
        return "KnownNoise"
    numeric = pd.to_numeric(series, errors="coerce")
    non_missing = series.notna().sum()
    if non_missing > 0 and numeric.notna().sum() / non_missing >= 0.95:
        return "Numeric"
    return "Categorical"


def build_column_profile(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    n = len(df)
    for column in df.columns:
        series = df[column]
        role = infer_role(column, series)
        missing_count = int(series.isna().sum())
        unique_count = int(series.nunique(dropna=True))
        rows.append({
            "Column": column,
            "Role": role,
            "Dtype": str(series.dtype),
            "Rows": n,
            "MissingCount": missing_count,
            "MissingPercent": round((missing_count / n * 100.0) if n else 0.0, 4),
            "UniqueCount": unique_count,
            "UniquePercent": round((unique_count / n * 100.0) if n else 0.0, 4),
            "IsConstant": bool(unique_count <= 1),
            "IsNearUnique": bool(n > 0 and unique_count / n >= 0.95),
        })
    return pd.DataFrame(rows)


def build_numeric_summary(df: pd.DataFrame, profile: pd.DataFrame) -> pd.DataFrame:
    rows = []
    numeric_columns = profile.loc[
        profile["Role"].isin(["Numeric", "KnownNoise"]),
        "Column"
    ].tolist()
    for column in numeric_columns:
        numeric = pd.to_numeric(df[column], errors="coerce")
        valid = numeric.dropna()
        if valid.empty:
            continue
        rows.append({
            "Column": column,
            "Count": int(valid.count()),
            "MissingCount": int(numeric.isna().sum()),
            "Mean": valid.mean(),
            "Std": valid.std(ddof=1),
            "Min": valid.min(),
            "P01": valid.quantile(0.01),
            "P05": valid.quantile(0.05),
            "Q1": valid.quantile(0.25),
            "Median": valid.median(),
            "Q3": valid.quantile(0.75),
            "P95": valid.quantile(0.95),
            "P99": valid.quantile(0.99),
            "Max": valid.max(),
            "IQR": valid.quantile(0.75) - valid.quantile(0.25),
            "Skew": valid.skew(),
        })
    if not rows:
        return pd.DataFrame(columns=[
            "Column", "Count", "MissingCount", "Mean", "Std", "Min",
            "P01", "P05", "Q1", "Median", "Q3", "P95", "P99", "Max",
            "IQR", "Skew"
        ])
    return pd.DataFrame(rows).sort_values("Column").reset_index(drop=True)


def build_categorical_summary(df: pd.DataFrame, profile: pd.DataFrame) -> pd.DataFrame:
    rows = []
    categorical_columns = profile.loc[
        profile["Role"].isin(["Categorical", "KnownNoise"]),
        "Column"
    ].tolist()
    for column in categorical_columns:
        numeric = pd.to_numeric(df[column], errors="coerce")
        non_missing_count = int(df[column].notna().sum())
        if non_missing_count and numeric.notna().sum() / non_missing_count >= 0.95:
            continue
        value_counts = df[column].value_counts(dropna=False)
        total = len(df)
        if value_counts.empty:
            rows.append({
                "Column": column,
                "UniqueCount": 0,
                "MostFrequentValue": "",
                "MostFrequentCount": 0,
                "MostFrequentPercent": 0.0,
                "TopValues": "",
            })
            continue
        top_value = value_counts.index[0]
        top_count = int(value_counts.iloc[0])
        top_pairs = []
        for value, count in value_counts.head(10).items():
            display = "<MISSING>" if pd.isna(value) else str(value)
            top_pairs.append(f"{display}:{int(count)}")
        rows.append({
            "Column": column,
            "UniqueCount": int(df[column].nunique(dropna=True)),
            "MostFrequentValue": "<MISSING>" if pd.isna(top_value) else str(top_value),
            "MostFrequentCount": top_count,
            "MostFrequentPercent": round((top_count / total * 100.0) if total else 0.0, 4),
            "TopValues": " | ".join(top_pairs),
        })
    if not rows:
        return pd.DataFrame(columns=[
            "Column", "UniqueCount", "MostFrequentValue",
            "MostFrequentCount", "MostFrequentPercent", "TopValues"
        ])
    return pd.DataFrame(rows).sort_values("Column").reset_index(drop=True)


def build_missing_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    n = len(df)
    for column in df.columns:
        missing_count = int(df[column].isna().sum())
        rows.append({
            "Column": column,
            "MissingCount": missing_count,
            "MissingPercent": round((missing_count / n * 100.0) if n else 0.0, 4),
        })
    return pd.DataFrame(rows).sort_values(
        ["MissingCount", "Column"],
        ascending=[False, True],
    ).reset_index(drop=True)


def build_class_distribution(df: pd.DataFrame) -> pd.DataFrame:
    if TARGET not in df.columns:
        return pd.DataFrame(columns=["Class", "Count", "Percent"])
    counts = df[TARGET].value_counts(dropna=False)
    total = len(df)
    rows = []
    for label, count in counts.items():
        rows.append({
            "Class": "<MISSING>" if pd.isna(label) else str(label),
            "Count": int(count),
            "Percent": round((int(count) / total * 100.0) if total else 0.0, 4),
        })
    return pd.DataFrame(rows)


def build_outlier_summary(df: pd.DataFrame, numeric_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in numeric_summary["Column"].tolist():
        numeric = pd.to_numeric(df[column], errors="coerce")
        valid = numeric.dropna()
        if len(valid) < 10:
            continue
        q1 = valid.quantile(0.25)
        q3 = valid.quantile(0.75)
        iqr = q3 - q1
        if not np.isfinite(iqr) or iqr <= 0:
            rows.append({
                "Column": column,
                "LowerFence": np.nan,
                "UpperFence": np.nan,
                "OutlierCount": 0,
                "OutlierPercent": 0.0,
                "Note": "IQR unavailable or zero",
            })
            continue
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        mask = numeric.notna() & ((numeric < lower) | (numeric > upper))
        count = int(mask.sum())
        rows.append({
            "Column": column,
            "LowerFence": lower,
            "UpperFence": upper,
            "OutlierCount": count,
            "OutlierPercent": round(count / len(df) * 100.0, 4),
            "Note": "Descriptive flag only; not an automatic deletion rule",
        })
    return pd.DataFrame(rows).sort_values(
        ["OutlierCount", "Column"],
        ascending=[False, True],
    ).reset_index(drop=True)


def build_summary(
    df: pd.DataFrame,
    profile: pd.DataFrame,
    class_distribution: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    rows.append({"Metric": "Rows", "Value": len(df)})
    rows.append({"Metric": "Columns", "Value": df.shape[1]})
    rows.append({"Metric": "UniqueClaimIDs", "Value": int(df["ClaimID"].nunique()) if "ClaimID" in df.columns else ""})
    rows.append({"Metric": "TotalMissingCells", "Value": int(df.isna().sum().sum())})
    rows.append({"Metric": "ColumnsWithMissing", "Value": int((df.isna().sum() > 0).sum())})
    rows.append({"Metric": "ConstantColumns", "Value": int(profile["IsConstant"].sum())})
    rows.append({"Metric": "NearUniqueColumns", "Value": int(profile["IsNearUnique"].sum())})
    rows.append({"Metric": "IdentifierColumns", "Value": int((profile["Role"] == "Identifier").sum())})
    rows.append({"Metric": "KnownNoiseColumns", "Value": int((profile["Role"] == "KnownNoise").sum())})
    if not class_distribution.empty:
        rows.append({
            "Metric": "ClassDistribution",
            "Value": json.dumps(
                dict(zip(class_distribution["Class"], class_distribution["Count"])),
                ensure_ascii=False,
            )
        })
    return pd.DataFrame(rows)


def main():
    print("=" * 72)
    print("ASSUREX - EDA")
    print("=" * 72)
    if not CLEAN_PATH.exists():
        raise FileNotFoundError(
            f"Clean dataset not found:\n{CLEAN_PATH}\n"
            "Run preprocessing/clean_data.py first."
        )
    df = read_clean_csv(CLEAN_PATH)
    if df.empty:
        raise ValueError("Clean dataset is empty.")
    if df.columns.duplicated().any():
        raise ValueError("Duplicate column names found.")
    if "ClaimID" in df.columns and df["ClaimID"].duplicated().any():
        raise ValueError(
            "Clean data still contains duplicated ClaimID values. "
            "Resolve cleaning before EDA."
        )
    profile = build_column_profile(df)
    numeric_summary = build_numeric_summary(df, profile)
    categorical_summary = build_categorical_summary(df, profile)
    missing_summary = build_missing_summary(df)
    class_distribution = build_class_distribution(df)
    outlier_summary = build_outlier_summary(df, numeric_summary)
    summary = build_summary(df, profile, class_distribution)
    summary.to_csv(SUMMARY_PATH, index=False, encoding="utf-8-sig")
    profile.to_csv(COLUMN_PROFILE_PATH, index=False, encoding="utf-8-sig")
    numeric_summary.to_csv(NUMERIC_PATH, index=False, encoding="utf-8-sig")
    categorical_summary.to_csv(CATEGORICAL_PATH, index=False, encoding="utf-8-sig")
    missing_summary.to_csv(MISSING_PATH, index=False, encoding="utf-8-sig")
    class_distribution.to_csv(CLASS_PATH, index=False, encoding="utf-8-sig")
    outlier_summary.to_csv(OUTLIER_PATH, index=False, encoding="utf-8-sig")
    manifest = {
        "input": str(CLEAN_PATH),
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "outputs": {
            "eda_summary": str(SUMMARY_PATH),
            "column_profile": str(COLUMN_PROFILE_PATH),
            "numeric_summary": str(NUMERIC_PATH),
            "categorical_summary": str(CATEGORICAL_PATH),
            "missing_summary": str(MISSING_PATH),
            "class_distribution": str(CLASS_PATH),
            "numeric_outlier_summary": str(OUTLIER_PATH),
        },
        "rules": {
            "dataset_modified": False,
            "correlation_performed": False,
            "feature_engineering_performed": False,
            "feature_selection_performed": False,
            "imputation_performed": False,
            "training_performed": False,
            "target_used_for_feature_decisions": False,
        },
    }
    EDA_MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Rows                         : {len(df)}")
    print(f"Columns                      : {df.shape[1]}")
    print(f"Unique ClaimIDs              : {df['ClaimID'].nunique() if 'ClaimID' in df.columns else 'N/A'}")
    print(f"Missing cells                : {int(df.isna().sum().sum())}")
    print(f"Columns with missing         : {int((df.isna().sum() > 0).sum())}")
    print(f"Constant columns             : {int(profile['IsConstant'].sum())}")
    print(f"Near-unique columns          : {int(profile['IsNearUnique'].sum())}")
    if not class_distribution.empty:
        class_counts = dict(
            zip(class_distribution["Class"], class_distribution["Count"])
        )
        print(f"Class counts                  : {class_counts}")
    print("\nCreated:")
    for path in [
        SUMMARY_PATH,
        COLUMN_PROFILE_PATH,
        NUMERIC_PATH,
        CATEGORICAL_PATH,
        MISSING_PATH,
        CLASS_PATH,
        OUTLIER_PATH,
        EDA_MANIFEST_PATH,
    ]:
        print(f" - {path}")
    print("\nIMPORTANT:")
    print(" - EDA is descriptive only.")
    print(" - No correlation analysis yet.")
    print(" - No feature engineering or feature selection yet.")
    print(" - No imputation/scaling/encoding/training performed.")
    print(" - Target was not used to choose features.")
if __name__ == "__main__":
    main()
