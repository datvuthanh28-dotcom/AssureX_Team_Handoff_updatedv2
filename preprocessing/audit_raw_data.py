from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd


# ============================================================
# ASSUREX CLAIM ENGINE - STEP 2
# RAW DATA QUALITY AUDIT
# ============================================================
# IMPORTANT:
# - This script DOES NOT clean or modify the raw dataset.
# - It only profiles the raw data and writes audit reports.
# - Do not train a model from data/audit/*.
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "assurex_raw.csv"
AUDIT_DIR = PROJECT_ROOT / "data" / "audit"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

SUMMARY_PATH = AUDIT_DIR / "data_quality_summary.csv"
MISSING_PATH = AUDIT_DIR / "missing_value_report.csv"
DUPLICATE_PATH = AUDIT_DIR / "duplicate_report.csv"
INVALID_PATH = AUDIT_DIR / "invalid_value_report.csv"
CATEGORY_PATH = AUDIT_DIR / "category_quality_report.csv"
OUTLIER_PATH = AUDIT_DIR / "outlier_report.csv"
CARDINALITY_PATH = AUDIT_DIR / "cardinality_report.csv"


TARGET = "ClaimClass"

DATE_COLUMNS = [
    "PurchaseDate",
    "ClaimDate",
    "FaultDate",
    "WarrantyExpiryDate",
]

NUMERIC_RULES = {
    # column: (minimum, maximum, allowed_values_or_None)
    "OCRConfidence": (0.0, 1.0, None),
    "RepairCount": (0, 10, None),
    "PriorClaimCount": (0, 20, None),
    "ClaimAmount": (0.01, 100000.0, None),
    "PreviousRepairCost": (0.0, 20000.0, None),
    "WarrantyDurationMonths": (1, 60, {12, 24, 36}),
}

CATEGORICAL_COLUMNS = [
    "ProductCategory",
    "Brand",
    "WarrantyStatus",
    "ExtendedWarranty",
    "FaultCovered",
    "ClaimReportingWithinPeriod",
    "ReceiptAvailable",
    "WarrantyCardAvailable",
    "ProductImageAvailable",
    "SerialEvidenceAvailable",
    "FaultEvidenceAvailable",
    "RepairReportAvailable",
    "PreviousRepair",
    "RepairAuthorized",
    "PreviousReplacement",
    "ReplacementWithinWarranty",
    "SerialNumberMatch",
    "ProductModelConsistent",
    "DuplicateClaimIndicator",
    "DocumentDuplicateIndicator",
    "ContradictionIndicator",
    "RequiredDocumentsComplete",
    "PurchaseProofAvailable",
    "ClaimSubmissionChannel",
]

NOISE_COLUMNS = [
    "BrowserFamily",
    "SubmissionMinute",
    "UiTheme",
    "RandomScore",
    "InternalBatchCode",
]


def add_summary(rows, section, metric, value, status="INFO", notes=""):
    rows.append(
        {
            "Section": section,
            "Metric": metric,
            "Value": value,
            "Status": status,
            "Notes": notes,
        }
    )


def normalized_text(value):
    if pd.isna(value):
        return None
    return " ".join(str(value).strip().lower().split())


def audit_missing(df):
    rows = []
    total = len(df)

    for column in df.columns:
        missing_count = int(df[column].isna().sum())
        missing_pct = (missing_count / total * 100.0) if total else 0.0
        rows.append(
            {
                "Column": column,
                "MissingCount": missing_count,
                "MissingPercent": round(missing_pct, 4),
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values(["MissingCount", "Column"], ascending=[False, True])
        .reset_index(drop=True)
    )


def audit_duplicates(df):
    rows = []

    if "ClaimID" not in df.columns:
        return pd.DataFrame(
            columns=[
                "ClaimID",
                "RowCount",
                "RecordIDs",
                "DuplicateType",
                "ContentVariants",
            ]
        )

    compare_columns = [
        c for c in df.columns
        if c not in {"RecordID"}
    ]

    duplicate_groups = df[df.duplicated("ClaimID", keep=False)].groupby(
        "ClaimID", dropna=False
    )

    for claim_id, group in duplicate_groups:
        signatures = (
            group[compare_columns]
            .astype("string")
            .fillna("<NA>")
            .agg("||".join, axis=1)
        )
        variant_count = int(signatures.nunique())

        # Same ClaimID + identical content except RecordID = exact ingestion duplicate.
        duplicate_type = "Exact duplicate" if variant_count == 1 else "Near duplicate"

        rows.append(
            {
                "ClaimID": claim_id,
                "RowCount": len(group),
                "RecordIDs": " | ".join(group["RecordID"].astype(str).tolist())
                if "RecordID" in group.columns
                else "",
                "DuplicateType": duplicate_type,
                "ContentVariants": variant_count,
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "ClaimID",
                "RowCount",
                "RecordIDs",
                "DuplicateType",
                "ContentVariants",
            ]
        )

    return pd.DataFrame(rows).sort_values(
        ["DuplicateType", "ClaimID"]
    ).reset_index(drop=True)


def audit_invalid_values(df):
    issues = []

    # --------------------------------------------------------
    # Numeric rules
    # --------------------------------------------------------
    for column, (minimum, maximum, allowed_values) in NUMERIC_RULES.items():
        if column not in df.columns:
            continue

        numeric = pd.to_numeric(df[column], errors="coerce")

        for idx in df.index:
            raw_value = df.at[idx, column]

            if pd.isna(raw_value):
                continue

            value = numeric.at[idx]

            if pd.isna(value):
                issues.append(
                    {
                        "RecordID": df.at[idx, "RecordID"] if "RecordID" in df.columns else idx,
                        "ClaimID": df.at[idx, "ClaimID"] if "ClaimID" in df.columns else "",
                        "Column": column,
                        "Value": raw_value,
                        "IssueType": "Invalid numeric format",
                        "Rule": f"numeric in [{minimum}, {maximum}]",
                    }
                )
                continue

            if value < minimum or value > maximum:
                issues.append(
                    {
                        "RecordID": df.at[idx, "RecordID"] if "RecordID" in df.columns else idx,
                        "ClaimID": df.at[idx, "ClaimID"] if "ClaimID" in df.columns else "",
                        "Column": column,
                        "Value": raw_value,
                        "IssueType": "Out-of-range numeric",
                        "Rule": f"{minimum} <= value <= {maximum}",
                    }
                )
                continue

            if allowed_values is not None and value not in allowed_values:
                issues.append(
                    {
                        "RecordID": df.at[idx, "RecordID"] if "RecordID" in df.columns else idx,
                        "ClaimID": df.at[idx, "ClaimID"] if "ClaimID" in df.columns else "",
                        "Column": column,
                        "Value": raw_value,
                        "IssueType": "Unexpected domain value",
                        "Rule": f"allowed={sorted(allowed_values)}",
                    }
                )

    # --------------------------------------------------------
    # Date parsing
    # --------------------------------------------------------
    parsed_dates = {}

    for column in DATE_COLUMNS:
        if column not in df.columns:
            continue

        parsed = pd.to_datetime(df[column], errors="coerce")
        parsed_dates[column] = parsed

        invalid_mask = df[column].notna() & parsed.isna()

        for idx in df.index[invalid_mask]:
            issues.append(
                {
                    "RecordID": df.at[idx, "RecordID"] if "RecordID" in df.columns else idx,
                    "ClaimID": df.at[idx, "ClaimID"] if "ClaimID" in df.columns else "",
                    "Column": column,
                    "Value": df.at[idx, column],
                    "IssueType": "Invalid date format",
                    "Rule": "must parse as a valid date",
                }
            )

    # --------------------------------------------------------
    # Date logic
    # --------------------------------------------------------
    if all(c in parsed_dates for c in ["PurchaseDate", "ClaimDate"]):
        mask = (
            parsed_dates["PurchaseDate"].notna()
            & parsed_dates["ClaimDate"].notna()
            & (parsed_dates["ClaimDate"] < parsed_dates["PurchaseDate"])
        )
        for idx in df.index[mask]:
            issues.append(
                {
                    "RecordID": df.at[idx, "RecordID"] if "RecordID" in df.columns else idx,
                    "ClaimID": df.at[idx, "ClaimID"] if "ClaimID" in df.columns else "",
                    "Column": "ClaimDate",
                    "Value": df.at[idx, "ClaimDate"],
                    "IssueType": "Impossible date logic",
                    "Rule": "ClaimDate >= PurchaseDate",
                }
            )

    if all(c in parsed_dates for c in ["PurchaseDate", "FaultDate"]):
        mask = (
            parsed_dates["PurchaseDate"].notna()
            & parsed_dates["FaultDate"].notna()
            & (parsed_dates["FaultDate"] < parsed_dates["PurchaseDate"])
        )
        for idx in df.index[mask]:
            issues.append(
                {
                    "RecordID": df.at[idx, "RecordID"] if "RecordID" in df.columns else idx,
                    "ClaimID": df.at[idx, "ClaimID"] if "ClaimID" in df.columns else "",
                    "Column": "FaultDate",
                    "Value": df.at[idx, "FaultDate"],
                    "IssueType": "Impossible date logic",
                    "Rule": "FaultDate >= PurchaseDate",
                }
            )

    if all(c in parsed_dates for c in ["FaultDate", "ClaimDate"]):
        mask = (
            parsed_dates["FaultDate"].notna()
            & parsed_dates["ClaimDate"].notna()
            & (parsed_dates["FaultDate"] > parsed_dates["ClaimDate"])
        )
        for idx in df.index[mask]:
            issues.append(
                {
                    "RecordID": df.at[idx, "RecordID"] if "RecordID" in df.columns else idx,
                    "ClaimID": df.at[idx, "ClaimID"] if "ClaimID" in df.columns else "",
                    "Column": "FaultDate",
                    "Value": df.at[idx, "FaultDate"],
                    "IssueType": "Impossible date logic",
                    "Rule": "FaultDate <= ClaimDate",
                }
            )

    if all(c in parsed_dates for c in ["PurchaseDate", "WarrantyExpiryDate"]):
        mask = (
            parsed_dates["PurchaseDate"].notna()
            & parsed_dates["WarrantyExpiryDate"].notna()
            & (parsed_dates["WarrantyExpiryDate"] < parsed_dates["PurchaseDate"])
        )
        for idx in df.index[mask]:
            issues.append(
                {
                    "RecordID": df.at[idx, "RecordID"] if "RecordID" in df.columns else idx,
                    "ClaimID": df.at[idx, "ClaimID"] if "ClaimID" in df.columns else "",
                    "Column": "WarrantyExpiryDate",
                    "Value": df.at[idx, "WarrantyExpiryDate"],
                    "IssueType": "Impossible date logic",
                    "Rule": "WarrantyExpiryDate >= PurchaseDate",
                }
            )

    if not issues:
        return pd.DataFrame(
            columns=[
                "RecordID",
                "ClaimID",
                "Column",
                "Value",
                "IssueType",
                "Rule",
            ]
        )

    return pd.DataFrame(issues).sort_values(
        ["IssueType", "Column", "ClaimID"]
    ).reset_index(drop=True)


def audit_category_quality(df):
    rows = []

    for column in CATEGORICAL_COLUMNS:
        if column not in df.columns:
            continue

        non_missing = df[column].dropna()

        if non_missing.empty:
            rows.append(
                {
                    "Column": column,
                    "NormalizedValue": "",
                    "RawVariants": "",
                    "VariantCount": 0,
                    "RowCount": 0,
                    "FormattingIssue": False,
                }
            )
            continue

        temp = pd.DataFrame(
            {
                "Raw": non_missing.astype(str),
                "Normalized": non_missing.map(normalized_text),
            }
        )

        for normalized, group in temp.groupby("Normalized", dropna=False):
            variants = sorted(group["Raw"].unique().tolist())
            formatting_issue = len(variants) > 1 or any(v != v.strip() for v in variants)

            rows.append(
                {
                    "Column": column,
                    "NormalizedValue": normalized,
                    "RawVariants": json.dumps(variants, ensure_ascii=False),
                    "VariantCount": len(variants),
                    "RowCount": len(group),
                    "FormattingIssue": bool(formatting_issue),
                }
            )

    return (
        pd.DataFrame(rows)
        .sort_values(
            ["FormattingIssue", "Column", "RowCount"],
            ascending=[False, True, False],
        )
        .reset_index(drop=True)
    )


def audit_outliers(df):
    rows = []

    numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()

    for column in numeric_columns:
        numeric = pd.to_numeric(df[column], errors="coerce").dropna()

        if len(numeric) < 10:
            continue

        q1 = numeric.quantile(0.25)
        q3 = numeric.quantile(0.75)
        iqr = q3 - q1

        if not np.isfinite(iqr) or iqr <= 0:
            continue

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        mask = pd.to_numeric(df[column], errors="coerce").notna() & (
            (pd.to_numeric(df[column], errors="coerce") < lower)
            | (pd.to_numeric(df[column], errors="coerce") > upper)
        )

        for idx in df.index[mask]:
            rows.append(
                {
                    "RecordID": df.at[idx, "RecordID"] if "RecordID" in df.columns else idx,
                    "ClaimID": df.at[idx, "ClaimID"] if "ClaimID" in df.columns else "",
                    "Column": column,
                    "Value": df.at[idx, column],
                    "LowerFence": lower,
                    "UpperFence": upper,
                }
            )

    if not rows:
        return pd.DataFrame(
            columns=[
                "RecordID",
                "ClaimID",
                "Column",
                "Value",
                "LowerFence",
                "UpperFence",
            ]
        )

    return pd.DataFrame(rows).sort_values(
        ["Column", "ClaimID"]
    ).reset_index(drop=True)


def audit_cardinality(df):
    rows = []
    total = len(df)

    for column in df.columns:
        unique_count = int(df[column].nunique(dropna=True))
        unique_ratio = unique_count / total if total else 0.0

        if unique_count <= 1:
            flag = "Constant / near-useless"
        elif unique_ratio >= 0.95:
            flag = "Near-unique / possible identifier"
        elif unique_ratio >= 0.50:
            flag = "High cardinality"
        else:
            flag = ""

        rows.append(
            {
                "Column": column,
                "UniqueCount": unique_count,
                "UniqueRatio": round(unique_ratio, 6),
                "Flag": flag,
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values(["UniqueRatio", "Column"], ascending=[False, True])
        .reset_index(drop=True)
    )


def main():
    print("=" * 72)
    print("ASSUREX - STEP 2: RAW DATA QUALITY AUDIT")
    print("=" * 72)

    if not RAW_PATH.exists():
        raise FileNotFoundError(
            f"Raw dataset not found:\n{RAW_PATH}\n"
            "Run dataset_generator/generate_raw_dataset.py first."
        )

    df = pd.read_csv(
    RAW_PATH,
    keep_default_na=False,
    na_values=[""]
)
    summary_rows = []

    add_summary(summary_rows, "Dataset", "Raw rows", len(df))
    add_summary(summary_rows, "Dataset", "Columns", df.shape[1])

    unique_claims = int(df["ClaimID"].nunique()) if "ClaimID" in df.columns else 0
    add_summary(summary_rows, "Dataset", "Unique ClaimIDs", unique_claims)

    if TARGET in df.columns and "ClaimID" in df.columns:
        canonical = df.drop_duplicates("ClaimID")
        counts = canonical[TARGET].value_counts().to_dict()

        add_summary(
            summary_rows,
            "Target",
            "Unique-claim class distribution",
            json.dumps(counts, ensure_ascii=False),
            "PASS" if counts == {
                "Valid Claim": 500,
                "Invalid Claim": 500,
                "Manual Review": 500,
            } else "CHECK",
            "Calculated on one row per ClaimID.",
        )

    # --------------------------------------------------------
    # Missing values
    # --------------------------------------------------------
    missing_report = audit_missing(df)
    missing_report.to_csv(MISSING_PATH, index=False, encoding="utf-8-sig")

    total_missing = int(df.isna().sum().sum())
    columns_with_missing = int((df.isna().sum() > 0).sum())

    add_summary(summary_rows, "Missingness", "Missing cells", total_missing)
    add_summary(
        summary_rows,
        "Missingness",
        "Columns with missing values",
        columns_with_missing,
    )

    # --------------------------------------------------------
    # Duplicates
    # --------------------------------------------------------
    duplicate_report = audit_duplicates(df)
    duplicate_report.to_csv(DUPLICATE_PATH, index=False, encoding="utf-8-sig")

    duplicate_claim_groups = len(duplicate_report)
    duplicate_rows = int(df.duplicated("ClaimID", keep=False).sum()) if "ClaimID" in df.columns else 0
    exact_groups = int((duplicate_report["DuplicateType"] == "Exact duplicate").sum()) if not duplicate_report.empty else 0
    near_groups = int((duplicate_report["DuplicateType"] == "Near duplicate").sum()) if not duplicate_report.empty else 0

    add_summary(summary_rows, "Duplicates", "Duplicate ClaimID groups", duplicate_claim_groups)
    add_summary(summary_rows, "Duplicates", "Rows in duplicate ClaimID groups", duplicate_rows)
    add_summary(summary_rows, "Duplicates", "Exact duplicate groups", exact_groups)
    add_summary(summary_rows, "Duplicates", "Near duplicate groups", near_groups)

    # --------------------------------------------------------
    # Invalid values / date logic
    # --------------------------------------------------------
    invalid_report = audit_invalid_values(df)
    invalid_report.to_csv(INVALID_PATH, index=False, encoding="utf-8-sig")

    add_summary(summary_rows, "Invalid values", "Detected invalid cells/rules", len(invalid_report))

    if not invalid_report.empty:
        for issue_type, count in invalid_report["IssueType"].value_counts().items():
            add_summary(
                summary_rows,
                "Invalid values",
                issue_type,
                int(count),
            )

    # --------------------------------------------------------
    # Category consistency
    # --------------------------------------------------------
    category_report = audit_category_quality(df)
    category_report.to_csv(CATEGORY_PATH, index=False, encoding="utf-8-sig")

    formatting_groups = (
        int(category_report["FormattingIssue"].sum())
        if not category_report.empty
        else 0
    )
    add_summary(
        summary_rows,
        "Categorical quality",
        "Normalized groups with formatting variants",
        formatting_groups,
    )

    # --------------------------------------------------------
    # Statistical outliers
    # --------------------------------------------------------
    outlier_report = audit_outliers(df)
    outlier_report.to_csv(OUTLIER_PATH, index=False, encoding="utf-8-sig")

    add_summary(
        summary_rows,
        "Outliers",
        "IQR-flagged numeric cells",
        len(outlier_report),
        "INFO",
        "Outliers are not automatically errors. Review before cleaning.",
    )

    # --------------------------------------------------------
    # Cardinality
    # --------------------------------------------------------
    cardinality_report = audit_cardinality(df)
    cardinality_report.to_csv(
        CARDINALITY_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    near_unique_count = int(
        cardinality_report["Flag"]
        .eq("Near-unique / possible identifier")
        .sum()
    )
    add_summary(
        summary_rows,
        "Cardinality",
        "Near-unique possible identifiers",
        near_unique_count,
    )

    # --------------------------------------------------------
    # Deliberate noise columns
    # --------------------------------------------------------
    present_noise = [c for c in NOISE_COLUMNS if c in df.columns]
    add_summary(
        summary_rows,
        "Feature design",
        "Deliberate noise columns present",
        len(present_noise),
        "PASS" if len(present_noise) == len(NOISE_COLUMNS) else "CHECK",
        " | ".join(present_noise),
    )

    # --------------------------------------------------------
    # Save summary
    # --------------------------------------------------------
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(
        SUMMARY_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"Raw rows                    : {len(df)}")
    print(f"Unique ClaimIDs              : {unique_claims}")
    print(f"Missing cells                : {total_missing}")
    print(f"Duplicate ClaimID groups     : {duplicate_claim_groups}")
    print(f"Rows in duplicate groups     : {duplicate_rows}")
    print(f"  Exact duplicate groups     : {exact_groups}")
    print(f"  Near duplicate groups      : {near_groups}")
    print(f"Detected invalid cells/rules : {len(invalid_report)}")
    print(f"Category formatting groups   : {formatting_groups}")
    print(f"IQR outlier cells            : {len(outlier_report)}")
    print(f"Noise columns present        : {len(present_noise)}/{len(NOISE_COLUMNS)}")

    print("\nCreated:")
    for path in [
        SUMMARY_PATH,
        MISSING_PATH,
        DUPLICATE_PATH,
        INVALID_PATH,
        CATEGORY_PATH,
        OUTLIER_PATH,
        CARDINALITY_PATH,
    ]:
        print(f" - {path}")

    print("\nIMPORTANT:")
    print(" - Step 2 only audits the raw dataset.")
    print(" - No values were cleaned, imputed, deleted, or transformed.")
    print(" - Do not train a model yet.")
    print(" - Next step: define and apply cleaning rules.")


if __name__ == "__main__":
    main()
