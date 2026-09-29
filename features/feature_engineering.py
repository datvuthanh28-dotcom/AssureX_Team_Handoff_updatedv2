from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd
PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = PROJECT_ROOT / "data" / "cleaned" / "assurex_clean.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "engineered"
AUDIT_DIR = PROJECT_ROOT / "data" / "audit"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "assurex_engineered.csv"
REPORT_PATH = AUDIT_DIR / "feature_engineering_report.csv"
MISSING_PATH = AUDIT_DIR / "feature_engineering_missingness.csv"
MANIFEST_PATH = AUDIT_DIR / "feature_engineering_manifest.json"
TARGET = "ClaimClass"
DATE_COLUMNS = [
    "PurchaseDate",
    "ClaimDate",
    "FaultDate",
]
DOCUMENT_COLUMNS = [
    "ReceiptAvailable",
    "WarrantyCardAvailable",
    "ProductImageAvailable",
    "SerialEvidenceAvailable",
    "FaultEvidenceAvailable",
]
CORE_REQUIRED_DOCUMENT_COLUMNS = [
    "ReceiptAvailable",
    "ProductImageAvailable",
    "SerialEvidenceAvailable",
    "FaultEvidenceAvailable",
]
COVERED_DAMAGE_TYPES = {
    "Manufacturing Defect",
    "Electrical Failure",
    "Internal Component Failure",
}
EXCLUDED_DAMAGE_TYPES = {
    "Accidental Damage",
    "Water Damage",
    "Physical Damage",
    "Normal Wear",
    "Misuse",
}


def read_clean_data(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        keep_default_na=False,
        na_values=[""],
    )


def canonical_yes_no(value):
    if pd.isna(value):
        return np.nan
    text = str(value).strip()
    if text in {"Yes", "No", "Unknown", "Not Applicable"}:
        return text
    lower = text.lower()
    mapping = {
        "yes": "Yes",
        "y": "Yes",
        "no": "No",
        "n": "No",
        "unknown": "Unknown",
        "unk": "Unknown",
        "not applicable": "Not Applicable",
        "n/a": "Not Applicable",
        "na": "Not Applicable",
    }
    return mapping.get(lower, text)


def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for column in DATE_COLUMNS:
        if column in out.columns:
            out[column] = pd.to_datetime(
                out[column],
                errors="coerce",
            )
    return out


def compute_warranty_expiry(row) -> pd.Timestamp | pd.NaT:
    purchase_date = row.get("PurchaseDate")
    duration = row.get("WarrantyDurationMonths")
    extended = row.get("ExtendedWarranty")
    if pd.isna(purchase_date) or pd.isna(duration):
        return pd.NaT
    try:
        months = int(float(duration))
    except (TypeError, ValueError):
        return pd.NaT
    if months <= 0:
        return pd.NaT
    extension_months = 12 if extended == "Yes" else 0
    return purchase_date + pd.DateOffset(
        months=months + extension_months
    )


def derive_fault_covered(value):
    if pd.isna(value):
        return np.nan
    value = str(value).strip()
    if value in COVERED_DAMAGE_TYPES:
        return "Yes"
    if value in EXCLUDED_DAMAGE_TYPES:
        return "No"
    return "Unknown"


def count_missing_documents(row) -> float:
    values = []
    for column in DOCUMENT_COLUMNS:
        if column not in row.index:
            continue
        value = row[column]
        if pd.isna(value):
            continue
        values.append(value)
    if not values and all(
        pd.isna(row.get(c, np.nan))
        for c in DOCUMENT_COLUMNS
    ):
        return np.nan
    return float(sum(value != "Yes" for value in values))


def count_available_documents(row) -> float:
    observed = [
        row.get(c, np.nan)
        for c in DOCUMENT_COLUMNS
    ]
    if all(pd.isna(v) for v in observed):
        return np.nan
    return float(sum(v == "Yes" for v in observed))


def required_documents_complete(row):
    values = [
        row.get(column, np.nan)
        for column in CORE_REQUIRED_DOCUMENT_COLUMNS
    ]
    if any(pd.isna(v) for v in values):
        return "Unknown"
    return "Yes" if all(v == "Yes" for v in values) else "No"


def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    out = df.copy()
    categorical_candidates = [
        "ExtendedWarranty",
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
    ]
    for column in categorical_candidates:
        if column in out.columns:
            out[column] = out[column].map(canonical_yes_no)
    out = parse_dates(out)
    engineered_columns = []
    if {"PurchaseDate", "ClaimDate"}.issubset(out.columns):
        out["ProductAgeDays"] = (
            out["ClaimDate"] - out["PurchaseDate"]
        ).dt.days.astype("float")
        engineered_columns.append("ProductAgeDays")
    if {"FaultDate", "ClaimDate"}.issubset(out.columns):
        out["ClaimReportingDelayDays"] = (
            out["ClaimDate"] - out["FaultDate"]
        ).dt.days.astype("float")
        engineered_columns.append("ClaimReportingDelayDays")
    if {"PurchaseDate", "WarrantyDurationMonths", "ExtendedWarranty"}.issubset(out.columns):
        out["WarrantyExpiryDate"] = out.apply(
            compute_warranty_expiry,
            axis=1,
        )
        engineered_columns.append("WarrantyExpiryDate")
    if {"WarrantyExpiryDate", "ClaimDate"}.issubset(out.columns):
        out["WarrantyRemainingDays"] = (
            out["WarrantyExpiryDate"] - out["ClaimDate"]
        ).dt.days.astype("float")
        engineered_columns.append("WarrantyRemainingDays")
        out["WarrantyStatus"] = np.select(
            [
                out["WarrantyRemainingDays"].isna(),
                out["WarrantyRemainingDays"] >= 0,
            ],
            [
                "Unknown",
                "Active",
            ],
            default="Expired",
        )
        engineered_columns.append("WarrantyStatus")
    if "ClaimReportingDelayDays" in out.columns:
        out["ClaimReportingWithinPeriod"] = np.select(
            [
                out["ClaimReportingDelayDays"].isna(),
                out["ClaimReportingDelayDays"] <= 30,
            ],
            [
                "Unknown",
                "Yes",
            ],
            default="No",
        )
        engineered_columns.append("ClaimReportingWithinPeriod")
    if "DamageType" in out.columns:
        out["FaultCovered"] = out["DamageType"].map(
            derive_fault_covered
        )
        engineered_columns.append("FaultCovered")
    if any(c in out.columns for c in DOCUMENT_COLUMNS):
        out["MissingDocumentCount"] = out.apply(
            count_missing_documents,
            axis=1,
        )
        engineered_columns.append("MissingDocumentCount")
        out["AvailableDocumentCount"] = out.apply(
            count_available_documents,
            axis=1,
        )
        engineered_columns.append("AvailableDocumentCount")
        out["RequiredDocumentsComplete"] = out.apply(
            required_documents_complete,
            axis=1,
        )
        engineered_columns.append("RequiredDocumentsComplete")
    if "ReceiptAvailable" in out.columns:
        out["PurchaseProofAvailable"] = out["ReceiptAvailable"]
        engineered_columns.append("PurchaseProofAvailable")
    if "PreviousRepair" in out.columns:
        out["HasRepairHistory"] = np.where(
            out["PreviousRepair"].isna(),
            "Unknown",
            np.where(
                out["PreviousRepair"] == "Yes",
                "Yes",
                "No",
            ),
        )
        engineered_columns.append("HasRepairHistory")
    if "PreviousReplacement" in out.columns:
        out["HasPreviousReplacement"] = np.where(
            out["PreviousReplacement"].isna(),
            "Unknown",
            np.where(
                out["PreviousReplacement"] == "Yes",
                "Yes",
                "No",
            ),
        )
        engineered_columns.append("HasPreviousReplacement")
    if "OCRConfidence" in out.columns:
        ocr = pd.to_numeric(
            out["OCRConfidence"],
            errors="coerce",
        )
        out["OCRQualityBand"] = pd.cut(
            ocr,
            bins=[-np.inf, 0.70, 0.85, np.inf],
            labels=["Low", "Medium", "High"],
            right=False,
        ).astype(object)
        out.loc[ocr.isna(), "OCRQualityBand"] = "Unknown"
        engineered_columns.append("OCRQualityBand")
    if "ClaimDate" in out.columns:
        out["ClaimMonth"] = out["ClaimDate"].dt.month.astype("float")
        out["ClaimDayOfWeek"] = out["ClaimDate"].dt.dayofweek.astype("float")
        engineered_columns.extend([
            "ClaimMonth",
            "ClaimDayOfWeek",
        ])
    return out, engineered_columns


def make_report(
    before: pd.DataFrame,
    after: pd.DataFrame,
    engineered_columns: list[str],
) -> pd.DataFrame:
    rows = []
    rows.append({
        "Metric": "InputRows",
        "Value": len(before),
    })
    rows.append({
        "Metric": "OutputRows",
        "Value": len(after),
    })
    rows.append({
        "Metric": "InputColumns",
        "Value": before.shape[1],
    })
    rows.append({
        "Metric": "OutputColumns",
        "Value": after.shape[1],
    })
    rows.append({
        "Metric": "EngineeredFeatureCount",
        "Value": len(engineered_columns),
    })
    rows.append({
        "Metric": "EngineeredFeatures",
        "Value": " | ".join(engineered_columns),
    })
    rows.append({
        "Metric": "TargetUsedForEngineering",
        "Value": "NO",
    })
    rows.append({
        "Metric": "ImputationPerformed",
        "Value": "NO",
    })
    rows.append({
        "Metric": "FeatureSelectionPerformed",
        "Value": "NO",
    })
    rows.append({
        "Metric": "RowsRemoved",
        "Value": len(before) - len(after),
    })
    return pd.DataFrame(rows)


def feature_missingness(
    df: pd.DataFrame,
    engineered_columns: list[str],
) -> pd.DataFrame:
    rows = []
    n = len(df)
    for column in engineered_columns:
        if column not in df.columns:
            continue
        missing = int(df[column].isna().sum())
        unknown = (
            int((df[column] == "Unknown").sum())
            if df[column].dtype == object
            else 0
        )
        rows.append({
            "Feature": column,
            "MissingCount": missing,
            "MissingPercent": round(
                missing / n * 100.0 if n else 0.0,
                4,
            ),
            "UnknownCount": unknown,
        })
    return pd.DataFrame(rows)


def format_dates_for_output(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    date_columns = [
        "PurchaseDate",
        "ClaimDate",
        "FaultDate",
        "WarrantyExpiryDate",
    ]
    for column in date_columns:
        if column in out.columns:
            out[column] = out[column].dt.strftime("%Y-%m-%d")
    return out


def main():
    print("=" * 72)
    print("ASSUREX - FEATURE ENGINEERING")
    print("=" * 72)
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Clean dataset not found:\n{INPUT_PATH}\n"
            "Run preprocessing/clean_data.py first."
        )
    before = read_clean_data(INPUT_PATH)
    if before.empty:
        raise ValueError("Clean dataset is empty.")
    if TARGET not in before.columns:
        raise ValueError(
            f"Target column '{TARGET}' is missing."
        )
    if "ClaimID" in before.columns and before["ClaimID"].duplicated().any():
        raise ValueError(
            "Duplicate ClaimID values found. "
            "Resolve cleaning before feature engineering."
        )
    original_target = before[TARGET].copy()
    engineered, engineered_columns = build_features(
        before
    )
    if not engineered[TARGET].equals(original_target):
        raise RuntimeError(
            "ClaimClass changed during feature engineering."
        )
    if len(engineered) != len(before):
        raise RuntimeError(
            "Feature engineering changed row count."
        )
    report = make_report(
        before,
        engineered,
        engineered_columns,
    )
    missingness = feature_missingness(
        engineered,
        engineered_columns,
    )
    output_df = format_dates_for_output(
        engineered
    )
    output_df.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )
    report.to_csv(
        REPORT_PATH,
        index=False,
        encoding="utf-8-sig",
    )
    missingness.to_csv(
        MISSING_PATH,
        index=False,
        encoding="utf-8-sig",
    )
    manifest = {
        "input": str(INPUT_PATH),
        "output": str(OUTPUT_PATH),
        "input_rows": int(len(before)),
        "output_rows": int(len(output_df)),
        "input_columns": int(before.shape[1]),
        "output_columns": int(output_df.shape[1]),
        "engineered_features": engineered_columns,
        "rules": {
            "target_used_to_create_features": False,
            "target_modified": False,
            "rows_removed": False,
            "imputation_performed": False,
            "scaling_performed": False,
            "encoding_performed": False,
            "feature_filtering_performed": False,
            "feature_selection_performed": False,
            "training_performed": False,
        },
    }
    MANIFEST_PATH.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Input rows                   : {len(before)}")
    print(f"Output rows                  : {len(output_df)}")
    print(f"Input columns                : {before.shape[1]}")
    print(f"Output columns               : {output_df.shape[1]}")
    print(f"Engineered features          : {len(engineered_columns)}")
    print("Target used for engineering  : NO")
    print("Rows removed                 : NO")
    print("Imputation performed         : NO")
    print("Feature selection performed  : NO")
    print("\nEngineered features:")
    for feature in engineered_columns:
        print(f" - {feature}")
    print("\nCreated:")
    for path in [
        OUTPUT_PATH,
        REPORT_PATH,
        MISSING_PATH,
        MANIFEST_PATH,
    ]:
        print(f" - {path}")
    print("\nIMPORTANT:")
    print(" - Feature engineering is deterministic and target-independent.")
    print(" - Missing values remain missing/Unknown where evidence is unavailable.")
    print(" - No feature has been removed yet.")
    print(" - Next stage: INITIAL FEATURE FILTER.")
if __name__ == "__main__":
    main()
