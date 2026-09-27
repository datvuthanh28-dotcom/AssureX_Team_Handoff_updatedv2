from __future__ import annotations

from pathlib import Path
import json

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


# ============================================================
# ASSUREX CLAIM ENGINE - FEATURE STABILITY CHECK
# ============================================================
# Purpose:
# - Re-check the remaining known-noise feature SubmissionMinute.
# - Compare:
#       A) current selected features
#       B) selected features WITHOUT SubmissionMinute
# - Use repeated CV on TRAIN only.
# - Then compare once on VALIDATION.
# - TEST IS NEVER LOADED.
#
# Decision:
# Remove SubmissionMinute if:
#   1) Mean repeated-CV Macro F1 drop is <= 0.2 percentage point, AND
#   2) Validation Macro F1 drop is <= 0.5 percentage point.
#
# This prevents a single 225-row validation split from preserving a
# deliberately injected noise feature due to chance correlation.
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

TRAIN_PATH = PROJECT_ROOT / "data" / "train" / "assurex_train.csv"
VALIDATION_PATH = PROJECT_ROOT / "data" / "validation" / "assurex_validation.csv"

SELECTED_INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "feature_selection"
    / "selected_features.csv"
)

OUT_DIR = PROJECT_ROOT / "data" / "feature_selection"
AUDIT_DIR = PROJECT_ROOT / "data" / "audit"

OUT_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_PATH = OUT_DIR / "feature_stability_report.csv"
FOLD_PATH = OUT_DIR / "feature_stability_cv_folds.csv"
FINAL_SELECTED_PATH = OUT_DIR / "selected_features_final.csv"
MANIFEST_PATH = AUDIT_DIR / "feature_stability_manifest.json"


TARGET = "ClaimClass"
ALIGNMENT_COLUMNS = {"ClaimID"}

FEATURE_TO_TEST = "SubmissionMinute"

RANDOM_SEED = 20260925

CV_SPLITS = 5
CV_REPEATS = 3

# Tolerances are deliberately small.
MAX_MEAN_CV_F1_DROP = 0.002
MAX_VALIDATION_F1_DROP = 0.005


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        keep_default_na=False,
        na_values=[""],
    )


def load_selected_features(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(
            f"Selected feature file not found:\n{path}\n"
            "Run features/feature_selection_loop.py first."
        )

    df = pd.read_csv(path)

    if "Feature" not in df.columns:
        raise ValueError(
            "selected_features.csv must contain a Feature column."
        )

    if "Selected" in df.columns:
        selected = df[
            df["Selected"].astype(str).str.lower().isin(
                ["true", "1", "yes"]
            )
        ]["Feature"].tolist()
    else:
        selected = df["Feature"].tolist()

    selected = [
        str(feature)
        for feature in selected
        if str(feature).strip()
    ]

    if not selected:
        raise ValueError("No selected features found.")

    return selected


def validate_inputs(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    selected_features: list[str],
) -> None:
    for name, df in [
        ("Train", train),
        ("Validation", validation),
    ]:
        if TARGET not in df.columns:
            raise ValueError(
                f"{name}: missing target {TARGET}."
            )

        if "ClaimID" not in df.columns:
            raise ValueError(
                f"{name}: missing ClaimID."
            )

        if df["ClaimID"].duplicated().any():
            raise ValueError(
                f"{name}: duplicate ClaimID found."
            )

    overlap = set(train["ClaimID"]) & set(
        validation["ClaimID"]
    )

    if overlap:
        raise ValueError(
            f"Train/Validation ClaimID overlap: {len(overlap)}."
        )

    missing_train = [
        f for f in selected_features
        if f not in train.columns
    ]

    missing_validation = [
        f for f in selected_features
        if f not in validation.columns
    ]

    if missing_train:
        raise ValueError(
            "Selected features missing from Train: "
            + ", ".join(missing_train)
        )

    if missing_validation:
        raise ValueError(
            "Selected features missing from Validation: "
            + ", ".join(missing_validation)
        )

    if FEATURE_TO_TEST not in selected_features:
        raise ValueError(
            f"{FEATURE_TO_TEST} is not in the current selected set. "
            "No stability check is needed."
        )


def infer_feature_types(
    train: pd.DataFrame,
    features: list[str],
) -> tuple[list[str], list[str]]:
    numeric_features = []
    categorical_features = []

    for column in features:
        series = train[column]

        non_missing = int(series.notna().sum())

        if non_missing == 0:
            categorical_features.append(column)
            continue

        numeric = pd.to_numeric(
            series,
            errors="coerce",
        )

        numeric_ratio = (
            float(numeric.notna().sum())
            / float(non_missing)
        )

        if numeric_ratio >= 0.95:
            numeric_features.append(column)
        else:
            categorical_features.append(column)

    return numeric_features, categorical_features


def build_pipeline(
    train_reference: pd.DataFrame,
    features: list[str],
) -> Pipeline:
    numeric_features, categorical_features = (
        infer_feature_types(
            train_reference,
            features,
        )
    )

    numeric_pipe = Pipeline([
        (
            "imputer",
            SimpleImputer(strategy="median"),
        ),
        (
            "scaler",
            StandardScaler(),
        ),
    ])

    categorical_pipe = Pipeline([
        (
            "imputer",
            SimpleImputer(
                strategy="most_frequent"
            ),
        ),
        (
            "onehot",
            OneHotEncoder(
                handle_unknown="ignore",
                sparse_output=False,
            ),
        ),
    ])

    transformers = []

    if numeric_features:
        transformers.append(
            (
                "num",
                numeric_pipe,
                numeric_features,
            )
        )

    if categorical_features:
        transformers.append(
            (
                "cat",
                categorical_pipe,
                categorical_features,
            )
        )

    preprocessor = ColumnTransformer(
        transformers=transformers,
        remainder="drop",
    )

    model = GradientBoostingClassifier(
        n_estimators=150,
        learning_rate=0.05,
        max_depth=3,
        random_state=RANDOM_SEED,
    )

    return Pipeline([
        ("preprocessor", preprocessor),
        ("model", model),
    ])


def repeated_cv_compare(
    train: pd.DataFrame,
    full_features: list[str],
    reduced_features: list[str],
) -> pd.DataFrame:
    splitter = RepeatedStratifiedKFold(
        n_splits=CV_SPLITS,
        n_repeats=CV_REPEATS,
        random_state=RANDOM_SEED,
    )

    rows = []

    X = train
    y = train[TARGET]

    for fold_number, (
        fit_idx,
        score_idx,
    ) in enumerate(
        splitter.split(
            np.zeros(len(train)),
            y,
        ),
        start=1,
    ):
        fit_df = train.iloc[
            fit_idx
        ].reset_index(drop=True)

        score_df = train.iloc[
            score_idx
        ].reset_index(drop=True)

        full_pipeline = build_pipeline(
            fit_df,
            full_features,
        )

        full_pipeline.fit(
            fit_df[full_features],
            fit_df[TARGET],
        )

        full_pred = full_pipeline.predict(
            score_df[full_features]
        )

        full_f1 = f1_score(
            score_df[TARGET],
            full_pred,
            average="macro",
        )

        reduced_pipeline = build_pipeline(
            fit_df,
            reduced_features,
        )

        reduced_pipeline.fit(
            fit_df[reduced_features],
            fit_df[TARGET],
        )

        reduced_pred = reduced_pipeline.predict(
            score_df[reduced_features]
        )

        reduced_f1 = f1_score(
            score_df[TARGET],
            reduced_pred,
            average="macro",
        )

        rows.append({
            "Fold": fold_number,
            "FullFeatureCount": len(
                full_features
            ),
            "ReducedFeatureCount": len(
                reduced_features
            ),
            "FullMacroF1": float(
                full_f1
            ),
            "WithoutSubmissionMinuteMacroF1": float(
                reduced_f1
            ),
            "DeltaWithoutMinusFull": float(
                reduced_f1 - full_f1
            ),
        })

    return pd.DataFrame(rows)


def validation_compare(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    full_features: list[str],
    reduced_features: list[str],
) -> dict:
    full_pipeline = build_pipeline(
        train,
        full_features,
    )

    full_pipeline.fit(
        train[full_features],
        train[TARGET],
    )

    full_pred = full_pipeline.predict(
        validation[full_features]
    )

    full_accuracy = accuracy_score(
        validation[TARGET],
        full_pred,
    )

    full_f1 = f1_score(
        validation[TARGET],
        full_pred,
        average="macro",
    )

    reduced_pipeline = build_pipeline(
        train,
        reduced_features,
    )

    reduced_pipeline.fit(
        train[reduced_features],
        train[TARGET],
    )

    reduced_pred = reduced_pipeline.predict(
        validation[reduced_features]
    )

    reduced_accuracy = accuracy_score(
        validation[TARGET],
        reduced_pred,
    )

    reduced_f1 = f1_score(
        validation[TARGET],
        reduced_pred,
        average="macro",
    )

    return {
        "FullValidationAccuracy": float(
            full_accuracy
        ),
        "FullValidationMacroF1": float(
            full_f1
        ),
        "ReducedValidationAccuracy": float(
            reduced_accuracy
        ),
        "ReducedValidationMacroF1": float(
            reduced_f1
        ),
        "ValidationDeltaWithoutMinusFull": float(
            reduced_f1 - full_f1
        ),
    }


def main():
    print("=" * 72)
    print(
        "ASSUREX - FEATURE STABILITY CHECK"
    )
    print("=" * 72)

    if not TRAIN_PATH.exists():
        raise FileNotFoundError(
            f"Train file not found:\n{TRAIN_PATH}"
        )

    if not VALIDATION_PATH.exists():
        raise FileNotFoundError(
            "Validation file not found:\n"
            f"{VALIDATION_PATH}"
        )

    train = read_csv(TRAIN_PATH)
    validation = read_csv(
        VALIDATION_PATH
    )

    selected_features = (
        load_selected_features(
            SELECTED_INPUT_PATH
        )
    )

    validate_inputs(
        train,
        validation,
        selected_features,
    )

    reduced_features = [
        feature
        for feature in selected_features
        if feature != FEATURE_TO_TEST
    ]

    print(
        f"Current selected features      : "
        f"{len(selected_features)}"
    )
    print(
        f"Feature under stability check  : "
        f"{FEATURE_TO_TEST}"
    )
    print(
        f"Reduced feature count          : "
        f"{len(reduced_features)}"
    )
    print(
        f"Repeated CV                    : "
        f"{CV_SPLITS}-fold x {CV_REPEATS} repeats"
    )
    print(
        "Test loaded                    : NO"
    )

    folds = repeated_cv_compare(
        train,
        selected_features,
        reduced_features,
    )

    folds.to_csv(
        FOLD_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    full_cv_mean = folds[
        "FullMacroF1"
    ].mean()

    full_cv_std = folds[
        "FullMacroF1"
    ].std(ddof=1)

    reduced_cv_mean = folds[
        "WithoutSubmissionMinuteMacroF1"
    ].mean()

    reduced_cv_std = folds[
        "WithoutSubmissionMinuteMacroF1"
    ].std(ddof=1)

    mean_cv_delta = folds[
        "DeltaWithoutMinusFull"
    ].mean()

    delta_std = folds[
        "DeltaWithoutMinusFull"
    ].std(ddof=1)

    wins = int(
        (
            folds[
                "DeltaWithoutMinusFull"
            ] > 1e-12
        ).sum()
    )

    ties = int(
        (
            folds[
                "DeltaWithoutMinusFull"
            ].abs() <= 1e-12
        ).sum()
    )

    losses = int(
        (
            folds[
                "DeltaWithoutMinusFull"
            ] < -1e-12
        ).sum()
    )

    validation_result = (
        validation_compare(
            train,
            validation,
            selected_features,
            reduced_features,
        )
    )

    validation_delta = validation_result[
        "ValidationDeltaWithoutMinusFull"
    ]

    cv_ok = (
        mean_cv_delta
        >= -MAX_MEAN_CV_F1_DROP
    )

    validation_ok = (
        validation_delta
        >= -MAX_VALIDATION_F1_DROP
    )

    remove_feature = bool(
        cv_ok and validation_ok
    )

    if remove_feature:
        final_features = reduced_features
        decision = "REMOVE"
        rationale = (
            "Repeated-CV mean Macro F1 is stable "
            "within tolerance and Validation drop "
            "is within tolerance."
        )
    else:
        final_features = selected_features
        decision = "KEEP"
        rationale = (
            "Removing the feature exceeded repeated-CV "
            "and/or Validation tolerance."
        )

    report = pd.DataFrame([
        {
            "FeatureTested": FEATURE_TO_TEST,
            "FullFeatureCount": len(
                selected_features
            ),
            "ReducedFeatureCount": len(
                reduced_features
            ),
            "CVFoldsTotal": len(folds),
            "FullCVMeanMacroF1": full_cv_mean,
            "FullCVStdMacroF1": full_cv_std,
            "ReducedCVMeanMacroF1": reduced_cv_mean,
            "ReducedCVStdMacroF1": reduced_cv_std,
            "MeanCVDeltaWithoutMinusFull": mean_cv_delta,
            "CVDeltaStd": delta_std,
            "ReducedWins": wins,
            "Ties": ties,
            "ReducedLosses": losses,
            "MaxAllowedMeanCVF1Drop": MAX_MEAN_CV_F1_DROP,
            "FullValidationMacroF1": validation_result[
                "FullValidationMacroF1"
            ],
            "ReducedValidationMacroF1": validation_result[
                "ReducedValidationMacroF1"
            ],
            "ValidationDeltaWithoutMinusFull": validation_delta,
            "MaxAllowedValidationF1Drop": MAX_VALIDATION_F1_DROP,
            "CVWithinTolerance": cv_ok,
            "ValidationWithinTolerance": validation_ok,
            "Decision": decision,
            "Rationale": rationale,
            "TestUsed": False,
        }
    ])

    report.to_csv(
        REPORT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    final_df = pd.DataFrame({
        "Feature": final_features,
        "Selected": True,
        "FrozenForModelComparison": True,
    })

    final_df.to_csv(
        FINAL_SELECTED_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    manifest = {
        "feature_tested": FEATURE_TO_TEST,
        "random_seed": RANDOM_SEED,
        "cv": {
            "folds": CV_SPLITS,
            "repeats": CV_REPEATS,
            "total_evaluations": int(
                len(folds)
            ),
        },
        "thresholds": {
            "max_mean_cv_f1_drop": MAX_MEAN_CV_F1_DROP,
            "max_validation_f1_drop": MAX_VALIDATION_F1_DROP,
        },
        "results": {
            "full_cv_mean_macro_f1": float(
                full_cv_mean
            ),
            "reduced_cv_mean_macro_f1": float(
                reduced_cv_mean
            ),
            "mean_cv_delta_without_minus_full": float(
                mean_cv_delta
            ),
            "full_validation_macro_f1": validation_result[
                "FullValidationMacroF1"
            ],
            "reduced_validation_macro_f1": validation_result[
                "ReducedValidationMacroF1"
            ],
            "validation_delta_without_minus_full": float(
                validation_delta
            ),
            "decision": decision,
        },
        "final_selected_features": final_features,
        "rules": {
            "test_loaded": False,
            "test_used": False,
            "train_used_for_repeated_cv": True,
            "validation_used_for_final_stability_confirmation": True,
            "final_feature_set_frozen_after_this_step": True,
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

    print("\nRepeated-CV results:")
    print(
        f" Full mean Macro F1            : "
        f"{full_cv_mean:.6f} +/- {full_cv_std:.6f}"
    )
    print(
        f" Without SubmissionMinute      : "
        f"{reduced_cv_mean:.6f} +/- {reduced_cv_std:.6f}"
    )
    print(
        f" Mean CV delta                 : "
        f"{mean_cv_delta:+.6f}"
    )
    print(
        f" Reduced wins / ties / losses  : "
        f"{wins} / {ties} / {losses}"
    )

    print("\nValidation confirmation:")
    print(
        f" Full Validation Macro F1      : "
        f"{validation_result['FullValidationMacroF1']:.6f}"
    )
    print(
        f" Reduced Validation Macro F1   : "
        f"{validation_result['ReducedValidationMacroF1']:.6f}"
    )
    print(
        f" Validation delta              : "
        f"{validation_delta:+.6f}"
    )

    print("\nDecision:")
    print(
        f" {FEATURE_TO_TEST:<30}: "
        f"{decision}"
    )
    print(
        f" Final selected features       : "
        f"{len(final_features)}"
    )
    print(
        " Test used                     : NO"
    )

    print("\nCreated:")
    for path in [
        REPORT_PATH,
        FOLD_PATH,
        FINAL_SELECTED_PATH,
        MANIFEST_PATH,
    ]:
        print(f" - {path}")

    print("\nIMPORTANT:")
    print(
        " - selected_features_final.csv is now the frozen "
        "feature set for training the 3 candidate algorithms."
    )
    print(
        " - Do not modify the feature set after comparing "
        "the 3 algorithms."
    )
    print(
        " - TEST remains locked."
    )


if __name__ == "__main__":
    main()
