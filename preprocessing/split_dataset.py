from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd


# ============================================================
# ASSUREX CLAIM ENGINE - LOCK TRAIN / VALIDATION / TEST SPLITS
# ============================================================
# Purpose:
# - Lock the dataset BEFORE the feature-selection loop.
# - Exact 70% / 15% / 15% split.
# - Exact class balance per split because each class has 500 claims:
#       Train      350 / class = 1050
#       Validation  75 / class = 225
#       Test        75 / class = 225
# - Preserve ClaimID for later Python-vs-GTM alignment.
#
# Important:
# - Test is LOCKED after this step.
# - Feature selection may use Train + Validation only.
# - Test may be opened only once after model/feature choices are frozen.
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "filtered"
    / "assurex_initial_filtered.csv"
)

TRAIN_DIR = PROJECT_ROOT / "data" / "train"
VALIDATION_DIR = PROJECT_ROOT / "data" / "validation"
TEST_DIR = PROJECT_ROOT / "data" / "test"
AUDIT_DIR = PROJECT_ROOT / "data" / "audit"

for folder in [
    TRAIN_DIR,
    VALIDATION_DIR,
    TEST_DIR,
    AUDIT_DIR,
]:
    folder.mkdir(parents=True, exist_ok=True)

TRAIN_PATH = TRAIN_DIR / "assurex_train.csv"
VALIDATION_PATH = VALIDATION_DIR / "assurex_validation.csv"
TEST_PATH = TEST_DIR / "assurex_test.csv"

ASSIGNMENTS_PATH = AUDIT_DIR / "split_assignments.csv"
SUMMARY_PATH = AUDIT_DIR / "split_summary.csv"
MANIFEST_PATH = AUDIT_DIR / "split_manifest.json"


TARGET = "ClaimClass"
ID_COLUMN = "ClaimID"

RANDOM_SEED = 20260925

TRAIN_RATIO = 0.70
VALIDATION_RATIO = 0.15
TEST_RATIO = 0.15

EXPECTED_TOTAL = 1500
EXPECTED_CLASS_COUNT = 500

EXPECTED_PER_CLASS = {
    "train": 350,
    "validation": 75,
    "test": 75,
}


def read_input(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        keep_default_na=False,
        na_values=[""],
    )


def validate_input(df: pd.DataFrame) -> None:
    if df.empty:
        raise ValueError("Input dataset is empty.")

    if TARGET not in df.columns:
        raise ValueError(f"Missing target column: {TARGET}")

    if ID_COLUMN not in df.columns:
        raise ValueError(f"Missing ID column: {ID_COLUMN}")

    if not df.columns.is_unique:
        raise ValueError("Duplicate column names found.")

    if df[ID_COLUMN].isna().any():
        raise ValueError("ClaimID contains missing values.")

    if df[ID_COLUMN].duplicated().any():
        raise ValueError(
            "ClaimID must be unique before splitting."
        )

    if len(df) != EXPECTED_TOTAL:
        raise ValueError(
            f"Expected {EXPECTED_TOTAL} claims, found {len(df)}."
        )

    class_counts = df[TARGET].value_counts().to_dict()

    expected_labels = {
        "Valid Claim",
        "Invalid Claim",
        "Manual Review",
    }

    if set(class_counts) != expected_labels:
        raise ValueError(
            "Unexpected target classes: "
            + ", ".join(sorted(class_counts))
        )

    for label in expected_labels:
        if class_counts.get(label, 0) != EXPECTED_CLASS_COUNT:
            raise ValueError(
                f"Expected {EXPECTED_CLASS_COUNT} rows for "
                f"{label}, found {class_counts.get(label, 0)}."
            )


def exact_stratified_split(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(RANDOM_SEED)

    train_indices = []
    validation_indices = []
    test_indices = []

    # Sort class names for deterministic class iteration.
    for label in sorted(df[TARGET].unique()):
        class_indices = df.index[
            df[TARGET] == label
        ].to_numpy()

        shuffled = rng.permutation(class_indices)

        train_end = EXPECTED_PER_CLASS["train"]
        validation_end = (
            train_end
            + EXPECTED_PER_CLASS["validation"]
        )

        train_indices.extend(
            shuffled[:train_end]
        )
        validation_indices.extend(
            shuffled[train_end:validation_end]
        )
        test_indices.extend(
            shuffled[validation_end:]
        )

    # Shuffle row order inside each split without changing membership.
    train_indices = rng.permutation(
        np.array(train_indices)
    )
    validation_indices = rng.permutation(
        np.array(validation_indices)
    )
    test_indices = rng.permutation(
        np.array(test_indices)
    )

    train = df.loc[train_indices].reset_index(drop=True)
    validation = df.loc[
        validation_indices
    ].reset_index(drop=True)
    test = df.loc[test_indices].reset_index(drop=True)

    return train, validation, test


def validate_split_integrity(
    source: pd.DataFrame,
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
) -> None:
    expected_sizes = {
        "train": 1050,
        "validation": 225,
        "test": 225,
    }

    actual_sizes = {
        "train": len(train),
        "validation": len(validation),
        "test": len(test),
    }

    if actual_sizes != expected_sizes:
        raise RuntimeError(
            f"Unexpected split sizes: {actual_sizes}"
        )

    for split_name, split_df in [
        ("train", train),
        ("validation", validation),
        ("test", test),
    ]:
        counts = split_df[TARGET].value_counts().to_dict()

        expected_count = EXPECTED_PER_CLASS[split_name]

        for label in [
            "Valid Claim",
            "Invalid Claim",
            "Manual Review",
        ]:
            if counts.get(label, 0) != expected_count:
                raise RuntimeError(
                    f"{split_name}: expected {expected_count} "
                    f"{label}, found {counts.get(label, 0)}."
                )

    train_ids = set(train[ID_COLUMN])
    validation_ids = set(validation[ID_COLUMN])
    test_ids = set(test[ID_COLUMN])

    if train_ids & validation_ids:
        raise RuntimeError(
            "ClaimID leakage between Train and Validation."
        )

    if train_ids & test_ids:
        raise RuntimeError(
            "ClaimID leakage between Train and Test."
        )

    if validation_ids & test_ids:
        raise RuntimeError(
            "ClaimID leakage between Validation and Test."
        )

    all_split_ids = (
        train_ids
        | validation_ids
        | test_ids
    )

    source_ids = set(source[ID_COLUMN])

    if all_split_ids != source_ids:
        missing = source_ids - all_split_ids
        unexpected = all_split_ids - source_ids

        raise RuntimeError(
            "Split membership does not exactly reproduce "
            f"source ClaimIDs. Missing={len(missing)}, "
            f"unexpected={len(unexpected)}."
        )

    # Verify every row is assigned exactly once.
    if (
        len(train)
        + len(validation)
        + len(test)
        != len(source)
    ):
        raise RuntimeError(
            "Split row totals do not match source rows."
        )


def build_assignments(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
) -> pd.DataFrame:
    parts = []

    for split_name, split_df in [
        ("Train", train),
        ("Validation", validation),
        ("Test", test),
    ]:
        part = split_df[
            [ID_COLUMN, TARGET]
        ].copy()

        part["Split"] = split_name

        parts.append(part)

    assignments = pd.concat(
        parts,
        ignore_index=True,
    )

    return assignments.sort_values(
        ID_COLUMN
    ).reset_index(drop=True)


def build_summary(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    total = (
        len(train)
        + len(validation)
        + len(test)
    )

    for split_name, split_df, expected_ratio in [
        ("Train", train, TRAIN_RATIO),
        (
            "Validation",
            validation,
            VALIDATION_RATIO,
        ),
        ("Test", test, TEST_RATIO),
    ]:
        counts = split_df[
            TARGET
        ].value_counts().to_dict()

        rows.append({
            "Split": split_name,
            "Rows": len(split_df),
            "Ratio": len(split_df) / total,
            "ExpectedRatio": expected_ratio,
            "ValidClaim": counts.get(
                "Valid Claim", 0
            ),
            "InvalidClaim": counts.get(
                "Invalid Claim", 0
            ),
            "ManualReview": counts.get(
                "Manual Review", 0
            ),
        })

    return pd.DataFrame(rows)


def main():
    print("=" * 72)
    print(
        "ASSUREX - LOCK TRAIN / VALIDATION / TEST"
    )
    print("=" * 72)

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Filtered dataset not found:\n"
            f"{INPUT_PATH}\n"
            "Run features/initial_feature_filter.py first."
        )

    df = read_input(INPUT_PATH)
    validate_input(df)

    train, validation, test = (
        exact_stratified_split(df)
    )

    validate_split_integrity(
        df,
        train,
        validation,
        test,
    )

    # Write the locked splits.
    train.to_csv(
        TRAIN_PATH,
        index=False,
        encoding="utf-8-sig",
    )
    validation.to_csv(
        VALIDATION_PATH,
        index=False,
        encoding="utf-8-sig",
    )
    test.to_csv(
        TEST_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    assignments = build_assignments(
        train,
        validation,
        test,
    )
    assignments.to_csv(
        ASSIGNMENTS_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    summary = build_summary(
        train,
        validation,
        test,
    )
    summary.to_csv(
        SUMMARY_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    manifest = {
        "input": str(INPUT_PATH),
        "random_seed": RANDOM_SEED,
        "split_ratios": {
            "train": TRAIN_RATIO,
            "validation": VALIDATION_RATIO,
            "test": TEST_RATIO,
        },
        "rows": {
            "source": int(len(df)),
            "train": int(len(train)),
            "validation": int(len(validation)),
            "test": int(len(test)),
        },
        "expected_per_class": EXPECTED_PER_CLASS,
        "id_column": ID_COLUMN,
        "target": TARGET,
        "rules": {
            "exact_stratification": True,
            "claimid_overlap": False,
            "test_locked": True,
            "test_allowed_for_feature_selection": False,
            "test_allowed_for_model_selection": False,
            "test_allowed_only_after_freeze": True,
        },
        "outputs": {
            "train": str(TRAIN_PATH),
            "validation": str(
                VALIDATION_PATH
            ),
            "test": str(TEST_PATH),
            "assignments": str(
                ASSIGNMENTS_PATH
            ),
            "summary": str(SUMMARY_PATH),
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

    train_counts = train[
        TARGET
    ].value_counts().to_dict()

    validation_counts = validation[
        TARGET
    ].value_counts().to_dict()

    test_counts = test[
        TARGET
    ].value_counts().to_dict()

    print(
        f"Source rows                   : {len(df)}"
    )
    print(
        f"Train rows                    : {len(train)}"
    )
    print(
        f"Validation rows               : {len(validation)}"
    )
    print(
        f"Test rows                     : {len(test)}"
    )

    print(
        f"Train class counts            : {train_counts}"
    )
    print(
        f"Validation class counts       : {validation_counts}"
    )
    print(
        f"Test class counts             : {test_counts}"
    )

    print(
        "ClaimID overlap               : NONE"
    )
    print(
        "Exact split ratio             : 70 / 15 / 15"
    )
    print(
        f"Random seed                   : {RANDOM_SEED}"
    )
    print(
        "Test status                   : LOCKED"
    )

    print("\nCreated:")
    for path in [
        TRAIN_PATH,
        VALIDATION_PATH,
        TEST_PATH,
        ASSIGNMENTS_PATH,
        SUMMARY_PATH,
        MANIFEST_PATH,
    ]:
        print(f" - {path}")

    print("\nIMPORTANT:")
    print(
        " - Feature selection may use Train + Validation only."
    )
    print(
        " - Do NOT inspect Test metrics during feature selection."
    )
    print(
        " - Do NOT use Test for hyperparameter/model selection."
    )
    print(
        " - These Test ClaimIDs must later be reused for GTM."
    )
    print(
        " - Final Test is opened only after the Python pipeline is frozen."
    )


if __name__ == "__main__":
    main()
