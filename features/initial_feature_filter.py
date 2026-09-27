from __future__ import annotations

from pathlib import Path
import json

import pandas as pd


# ============================================================
# ASSUREX CLAIM ENGINE - INITIAL FEATURE FILTER
# ============================================================
# Purpose:
# - Apply ONLY structural / schema-based filtering.
# - Remove identifiers and raw date fields that should not be model predictors.
# - Keep weak/noise/redundant features for the later FEATURE SELECTION LOOP.
#
# Leakage rule:
# - ClaimClass is NOT used to decide which features to keep/drop.
# - No imputation, encoding, scaling, correlation-based removal, importance,
#   model training, or validation occurs here.
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_PATH = PROJECT_ROOT / "data" / "engineered" / "assurex_engineered.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "filtered"
AUDIT_DIR = PROJECT_ROOT / "data" / "audit"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PATH = OUTPUT_DIR / "assurex_initial_filtered.csv"
FEATURE_SET_PATH = OUTPUT_DIR / "initial_feature_set.csv"
REPORT_PATH = AUDIT_DIR / "initial_feature_filter_report.csv"
MANIFEST_PATH = AUDIT_DIR / "initial_feature_filter_manifest.json"


TARGET = "ClaimClass"

# ClaimID is retained in the dataset only for split alignment and later
# Python-vs-GTM comparison, but is explicitly NOT an ML predictor.
ALIGNMENT_COLUMNS = ["ClaimID"]

# Structural columns that must never be model predictors.
DROP_IDENTIFIER_COLUMNS = [
    "RecordID",
    "CustomerID",
    "ProductID",
    "ModelNumber",
    "SerialNumber",
    "InternalBatchCode",
]

# Raw calendar fields are dropped from predictor candidates because deterministic
# engineered representations already exist (age, delay, warranty remaining,
# claim month/day-of-week).
DROP_RAW_DATE_COLUMNS = [
    "PurchaseDate",
    "ClaimDate",
    "FaultDate",
    "WarrantyExpiryDate",
]

# Deliberate noise features that are intentionally KEPT so the later
# feature-selection loop has to prove they are weak/noisy.
KNOWN_NOISE_TO_KEEP = [
    "BrowserFamily",
    "SubmissionMinute",
    "UiTheme",
    "RandomScore",
]

# Engineered aliases / redundant features are intentionally KEPT.
# The iterative selection loop will decide whether removing them changes
# validation performance.
KNOWN_REDUNDANT_TO_KEEP = [
    "ReceiptAvailable",
    "PurchaseProofAvailable",
    "PreviousRepair",
    "HasRepairHistory",
    "PreviousReplacement",
    "HasPreviousReplacement",
    "RepairCount",
    "PreviousRepairCost",
    "RepairReportAvailable",
    "RepairAuthorized",
    "ReplacementWithinWarranty",
]


def read_engineered(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        keep_default_na=False,
        na_values=[""],
    )


def validate_input(df: pd.DataFrame) -> None:
    if df.empty:
        raise ValueError("Engineered dataset is empty.")

    if TARGET not in df.columns:
        raise ValueError(f"Missing target column: {TARGET}")

    if "ClaimID" not in df.columns:
        raise ValueError("ClaimID is required for split alignment.")

    if df["ClaimID"].duplicated().any():
        raise ValueError(
            "Duplicate ClaimID values found. "
            "Resolve cleaning before initial feature filtering."
        )

    if not df.columns.is_unique:
        raise ValueError("Duplicate column names found.")


def build_feature_decisions(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for column in df.columns:
        if column == TARGET:
            role = "Target"
            keep = True
            predictor = False
            reason = "Target label; preserved but never used as predictor."

        elif column in ALIGNMENT_COLUMNS:
            role = "AlignmentID"
            keep = True
            predictor = False
            reason = (
                "Retained for split alignment and Python-vs-GTM claim matching; "
                "excluded from ML predictors."
            )

        elif column in DROP_IDENTIFIER_COLUMNS:
            role = "Identifier"
            keep = False
            predictor = False
            reason = "Identifier / ingestion metadata; not a valid predictor."

        elif column in DROP_RAW_DATE_COLUMNS:
            role = "RawDate"
            keep = False
            predictor = False
            reason = (
                "Raw date removed after deterministic date-based engineered "
                "features were created."
            )

        elif column in KNOWN_NOISE_TO_KEEP:
            role = "KnownNoise"
            keep = True
            predictor = True
            reason = (
                "Intentionally retained so the later feature-selection loop "
                "can demonstrate that noise contributes little."
            )

        elif column in KNOWN_REDUNDANT_TO_KEEP:
            role = "RedundancyCandidate"
            keep = True
            predictor = True
            reason = (
                "Intentionally retained; later removal must be justified by "
                "importance + validation performance."
            )

        else:
            role = "CandidatePredictor"
            keep = True
            predictor = True
            reason = "Retained as initial ML candidate feature."

        rows.append({
            "Feature": column,
            "Role": role,
            "KeepInFilteredDataset": keep,
            "UseAsPredictor": predictor,
            "Reason": reason,
        })

    return pd.DataFrame(rows)


def main():
    print("=" * 72)
    print("ASSUREX - INITIAL FEATURE FILTER")
    print("=" * 72)

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Engineered dataset not found:\n{INPUT_PATH}\n"
            "Run features/feature_engineering.py first."
        )

    df = read_engineered(INPUT_PATH)
    validate_input(df)

    decisions = build_feature_decisions(df)

    drop_columns = decisions.loc[
        decisions["KeepInFilteredDataset"] == False,
        "Feature",
    ].tolist()

    predictor_columns = decisions.loc[
        decisions["UseAsPredictor"] == True,
        "Feature",
    ].tolist()

    alignment_columns = [
        c for c in ALIGNMENT_COLUMNS if c in df.columns
    ]

    keep_columns = (
        alignment_columns
        + predictor_columns
        + [TARGET]
    )

    # Preserve original order, remove accidental duplicates.
    seen = set()
    keep_columns = [
        c for c in keep_columns
        if c in df.columns and not (c in seen or seen.add(c))
    ]

    filtered = df[keep_columns].copy()

    # Safety: filtering must not alter rows, IDs, or target labels.
    if len(filtered) != len(df):
        raise RuntimeError("Initial filtering changed row count.")

    if not filtered["ClaimID"].equals(df["ClaimID"]):
        raise RuntimeError("ClaimID order changed during filtering.")

    if not filtered[TARGET].equals(df[TARGET]):
        raise RuntimeError("ClaimClass changed during filtering.")

    filtered.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    decisions.to_csv(
        FEATURE_SET_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    report = pd.DataFrame([
        {"Metric": "InputRows", "Value": len(df)},
        {"Metric": "OutputRows", "Value": len(filtered)},
        {"Metric": "InputColumns", "Value": df.shape[1]},
        {"Metric": "OutputColumns", "Value": filtered.shape[1]},
        {"Metric": "PredictorCandidates", "Value": len(predictor_columns)},
        {"Metric": "StructuralColumnsRemoved", "Value": len(drop_columns)},
        {"Metric": "DroppedColumns", "Value": " | ".join(drop_columns)},
        {"Metric": "KnownNoiseRetained", "Value": " | ".join(
            [c for c in KNOWN_NOISE_TO_KEEP if c in predictor_columns]
        )},
        {"Metric": "TargetUsedForFiltering", "Value": "NO"},
        {"Metric": "CorrelationBasedRemoval", "Value": "NO"},
        {"Metric": "ImportanceBasedRemoval", "Value": "NO"},
        {"Metric": "ModelTrainingPerformed", "Value": "NO"},
    ])

    report.to_csv(
        REPORT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    manifest = {
        "input": str(INPUT_PATH),
        "output": str(OUTPUT_PATH),
        "feature_set": str(FEATURE_SET_PATH),
        "rows": int(len(filtered)),
        "input_columns": int(df.shape[1]),
        "output_columns": int(filtered.shape[1]),
        "predictor_candidates": predictor_columns,
        "alignment_columns": alignment_columns,
        "target": TARGET,
        "dropped_structural_columns": drop_columns,
        "known_noise_retained": [
            c for c in KNOWN_NOISE_TO_KEEP
            if c in predictor_columns
        ],
        "known_redundancy_candidates_retained": [
            c for c in KNOWN_REDUNDANT_TO_KEEP
            if c in predictor_columns
        ],
        "rules": {
            "target_used_for_filtering": False,
            "correlation_based_removal": False,
            "importance_based_removal": False,
            "missing_value_imputation": False,
            "encoding": False,
            "scaling": False,
            "training": False,
        },
    }

    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Input rows                   : {len(df)}")
    print(f"Output rows                  : {len(filtered)}")
    print(f"Input columns                : {df.shape[1]}")
    print(f"Output columns               : {filtered.shape[1]}")
    print(f"Predictor candidates         : {len(predictor_columns)}")
    print(f"Structural columns removed   : {len(drop_columns)}")
    print("Target used for filtering    : NO")
    print("Correlation-based removal    : NO")
    print("Importance-based removal     : NO")
    print("Training performed           : NO")

    print("\nRemoved structural columns:")
    for column in drop_columns:
        print(f" - {column}")

    print("\nKnown noise deliberately retained:")
    for column in KNOWN_NOISE_TO_KEEP:
        if column in predictor_columns:
            print(f" - {column}")

    print("\nCreated:")
    for path in [
        OUTPUT_PATH,
        FEATURE_SET_PATH,
        REPORT_PATH,
        MANIFEST_PATH,
    ]:
        print(f" - {path}")

    print("\nIMPORTANT:")
    print(" - ClaimID is retained only for alignment, never as predictor.")
    print(" - Weak/noise/redundant features are intentionally still present.")
    print(" - No model-based feature decision has been made yet.")
    print(" - Before the feature-selection loop, train/validation/test must be locked.")


if __name__ == "__main__":
    main()
