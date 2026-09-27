from __future__ import annotations

from pathlib import Path
import json
import time

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


# ============================================================
# ASSUREX CLAIM ENGINE - TRAIN 3 ALGORITHMS
# ============================================================
# Purpose:
# - Use the frozen selected feature set.
# - Train and compare 3 candidate algorithms:
#       1) Logistic Regression
#       2) Random Forest
#       3) Gradient Boosting
# - Train on TRAIN.
# - Evaluate model-selection performance on VALIDATION.
# - 5-fold CV is performed on TRAIN only as a stability reference.
#
# CRITICAL:
# - TEST IS NEVER LOADED.
# - Primary selection metric = Validation Macro F1.
# - Tie-breakers:
#       Validation Accuracy
#       Train CV Macro F1 mean
# - This step selects the algorithm only.
# - Final model is NOT created yet.
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

TRAIN_PATH = PROJECT_ROOT / "data" / "train" / "assurex_train.csv"
VALIDATION_PATH = (
    PROJECT_ROOT / "data" / "validation" / "assurex_validation.csv"
)

SELECTED_FEATURES_PATH = (
    PROJECT_ROOT
    / "data"
    / "feature_selection"
    / "selected_features_final.csv"
)

MODEL_DIR = PROJECT_ROOT / "model"
AUDIT_DIR = PROJECT_ROOT / "data" / "audit"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

COMPARISON_PATH = MODEL_DIR / "model_comparison.csv"
CLASS_METRICS_PATH = MODEL_DIR / "validation_class_metrics.csv"
CONFUSION_PATH = MODEL_DIR / "validation_confusion_matrices.csv"
SELECTION_PATH = MODEL_DIR / "best_model_selection.json"
MANIFEST_PATH = AUDIT_DIR / "model_selection_manifest.json"

LOGISTIC_MODEL_PATH = MODEL_DIR / "candidate_logistic_regression.joblib"
RF_MODEL_PATH = MODEL_DIR / "candidate_random_forest.joblib"
GB_MODEL_PATH = MODEL_DIR / "candidate_gradient_boosting.joblib"


TARGET = "ClaimClass"
ALIGNMENT_COLUMNS = {"ClaimID"}

RANDOM_SEED = 20260925
CV_SPLITS = 5

CLASS_ORDER = [
    "Invalid Claim",
    "Manual Review",
    "Valid Claim",
]


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        keep_default_na=False,
        na_values=[""],
    )


def load_selected_features(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(
            f"Frozen selected feature file not found:\n{path}\n"
            "Run features/feature_stability_check.py first."
        )

    df = pd.read_csv(path)

    if "Feature" not in df.columns:
        raise ValueError(
            "selected_features_final.csv must contain a Feature column."
        )

    if "Selected" in df.columns:
        mask = df["Selected"].astype(str).str.lower().isin(
            ["true", "1", "yes"]
        )
        features = df.loc[mask, "Feature"].astype(str).tolist()
    else:
        features = df["Feature"].astype(str).tolist()

    features = [
        feature.strip()
        for feature in features
        if feature.strip()
    ]

    if not features:
        raise ValueError("No frozen selected features found.")

    return features


def validate_inputs(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    features: list[str],
) -> None:
    for name, df in [
        ("Train", train),
        ("Validation", validation),
    ]:
        if df.empty:
            raise ValueError(f"{name} dataset is empty.")

        if TARGET not in df.columns:
            raise ValueError(f"{name}: missing target {TARGET}.")

        if "ClaimID" not in df.columns:
            raise ValueError(f"{name}: missing ClaimID.")

        if df["ClaimID"].duplicated().any():
            raise ValueError(f"{name}: duplicate ClaimID found.")

        missing_features = [
            feature
            for feature in features
            if feature not in df.columns
        ]

        if missing_features:
            raise ValueError(
                f"{name}: selected features missing: "
                + ", ".join(missing_features)
            )

    overlap = set(train["ClaimID"]) & set(validation["ClaimID"])

    if overlap:
        raise ValueError(
            f"Train/Validation ClaimID overlap detected: {len(overlap)}"
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

        numeric = pd.to_numeric(series, errors="coerce")
        numeric_ratio = (
            float(numeric.notna().sum()) / float(non_missing)
        )

        if numeric_ratio >= 0.95:
            numeric_features.append(column)
        else:
            categorical_features.append(column)

    return numeric_features, categorical_features


def build_preprocessor(
    train: pd.DataFrame,
    features: list[str],
) -> ColumnTransformer:
    numeric_features, categorical_features = infer_feature_types(
        train,
        features,
    )

    numeric_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    categorical_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
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
            ("num", numeric_pipe, numeric_features)
        )

    if categorical_features:
        transformers.append(
            ("cat", categorical_pipe, categorical_features)
        )

    return ColumnTransformer(
        transformers=transformers,
        remainder="drop",
    )


def build_models(
    train: pd.DataFrame,
    features: list[str],
) -> dict[str, Pipeline]:
    models = {}

    models["Logistic Regression"] = Pipeline([
        (
            "preprocessor",
            build_preprocessor(train, features),
        ),
        (
            "model",
            LogisticRegression(
                max_iter=3000,
                random_state=RANDOM_SEED,
            ),
        ),
    ])

    models["Random Forest"] = Pipeline([
        (
            "preprocessor",
            build_preprocessor(train, features),
        ),
        (
            "model",
            RandomForestClassifier(
                n_estimators=300,
                random_state=RANDOM_SEED,
                n_jobs=-1,
            ),
        ),
    ])

    models["Gradient Boosting"] = Pipeline([
        (
            "preprocessor",
            build_preprocessor(train, features),
        ),
        (
            "model",
            GradientBoostingClassifier(
                n_estimators=150,
                learning_rate=0.05,
                max_depth=3,
                random_state=RANDOM_SEED,
            ),
        ),
    ])

    return models


def macro_metrics(
    y_true: pd.Series,
    y_pred: np.ndarray,
) -> dict[str, float]:
    return {
        "Accuracy": float(
            accuracy_score(y_true, y_pred)
        ),
        "PrecisionMacro": float(
            precision_score(
                y_true,
                y_pred,
                average="macro",
                zero_division=0,
            )
        ),
        "RecallMacro": float(
            recall_score(
                y_true,
                y_pred,
                average="macro",
                zero_division=0,
            )
        ),
        "F1Macro": float(
            f1_score(
                y_true,
                y_pred,
                average="macro",
                zero_division=0,
            )
        ),
    }


def class_metrics_rows(
    model_name: str,
    y_true: pd.Series,
    y_pred: np.ndarray,
) -> list[dict]:
    rows = []

    for label in CLASS_ORDER:
        y_true_binary = (y_true == label).astype(int)
        y_pred_binary = (y_pred == label).astype(int)

        rows.append({
            "Model": model_name,
            "Class": label,
            "Precision": precision_score(
                y_true_binary,
                y_pred_binary,
                zero_division=0,
            ),
            "Recall": recall_score(
                y_true_binary,
                y_pred_binary,
                zero_division=0,
            ),
            "F1": f1_score(
                y_true_binary,
                y_pred_binary,
                zero_division=0,
            ),
            "Support": int(y_true_binary.sum()),
        })

    return rows


def confusion_rows(
    model_name: str,
    y_true: pd.Series,
    y_pred: np.ndarray,
) -> list[dict]:
    matrix = confusion_matrix(
        y_true,
        y_pred,
        labels=CLASS_ORDER,
    )

    rows = []

    for actual_idx, actual_label in enumerate(CLASS_ORDER):
        for predicted_idx, predicted_label in enumerate(CLASS_ORDER):
            rows.append({
                "Model": model_name,
                "ActualClass": actual_label,
                "PredictedClass": predicted_label,
                "Count": int(
                    matrix[actual_idx, predicted_idx]
                ),
            })

    return rows


def estimate_prediction_time_ms(
    pipeline: Pipeline,
    X_validation: pd.DataFrame,
    repeats: int = 5,
) -> float:
    times = []

    # Warmup.
    pipeline.predict(X_validation.iloc[: min(20, len(X_validation))])

    for _ in range(repeats):
        start = time.perf_counter()
        pipeline.predict(X_validation)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    mean_total_seconds = float(np.mean(times))

    return (
        mean_total_seconds
        / max(len(X_validation), 1)
        * 1000.0
    )


def model_output_path(model_name: str) -> Path:
    mapping = {
        "Logistic Regression": LOGISTIC_MODEL_PATH,
        "Random Forest": RF_MODEL_PATH,
        "Gradient Boosting": GB_MODEL_PATH,
    }
    return mapping[model_name]


def main():
    print("=" * 72)
    print("ASSUREX - TRAIN 3 ALGORITHMS")
    print("=" * 72)

    train = read_csv(TRAIN_PATH)
    validation = read_csv(VALIDATION_PATH)
    selected_features = load_selected_features(
        SELECTED_FEATURES_PATH
    )

    validate_inputs(
        train,
        validation,
        selected_features,
    )

    print(f"Train rows                    : {len(train)}")
    print(f"Validation rows               : {len(validation)}")
    print(f"Frozen selected features      : {len(selected_features)}")
    print("Test loaded                    : NO")
    print("Primary selection metric       : Validation Macro F1")

    models = build_models(
        train,
        selected_features,
    )

    cv = StratifiedKFold(
        n_splits=CV_SPLITS,
        shuffle=True,
        random_state=RANDOM_SEED,
    )

    comparison_rows = []
    class_rows = []
    confusion_output_rows = []

    for model_name, pipeline in models.items():
        print("\n" + "-" * 72)
        print(model_name)
        print("-" * 72)

        cv_result = cross_validate(
            pipeline,
            train[selected_features],
            train[TARGET],
            cv=cv,
            scoring={
                "accuracy": "accuracy",
                "f1_macro": "f1_macro",
                "precision_macro": "precision_macro",
                "recall_macro": "recall_macro",
            },
            n_jobs=-1,
            return_train_score=False,
        )

        cv_accuracy_mean = float(
            np.mean(cv_result["test_accuracy"])
        )
        cv_accuracy_std = float(
            np.std(
                cv_result["test_accuracy"],
                ddof=1,
            )
        )
        cv_f1_mean = float(
            np.mean(cv_result["test_f1_macro"])
        )
        cv_f1_std = float(
            np.std(
                cv_result["test_f1_macro"],
                ddof=1,
            )
        )

        start_fit = time.perf_counter()

        pipeline.fit(
            train[selected_features],
            train[TARGET],
        )

        fit_seconds = (
            time.perf_counter()
            - start_fit
        )

        validation_pred = pipeline.predict(
            validation[selected_features]
        )

        metrics = macro_metrics(
            validation[TARGET],
            validation_pred,
        )

        avg_prediction_ms = (
            estimate_prediction_time_ms(
                pipeline,
                validation[selected_features],
            )
        )

        output_path = model_output_path(
            model_name
        )

        joblib.dump(
            pipeline,
            output_path,
        )

        model_size_mb = (
            output_path.stat().st_size
            / (1024.0 * 1024.0)
        )

        comparison_rows.append({
            "Model": model_name,
            "FeatureCount": len(selected_features),
            "TrainRows": len(train),
            "ValidationRows": len(validation),
            "CVAccuracyMean": cv_accuracy_mean,
            "CVAccuracyStd": cv_accuracy_std,
            "CVMacroF1Mean": cv_f1_mean,
            "CVMacroF1Std": cv_f1_std,
            "ValidationAccuracy": metrics["Accuracy"],
            "ValidationPrecisionMacro": metrics["PrecisionMacro"],
            "ValidationRecallMacro": metrics["RecallMacro"],
            "ValidationMacroF1": metrics["F1Macro"],
            "FitSeconds": float(fit_seconds),
            "AvgValidationPredictionMsPerClaim": avg_prediction_ms,
            "SerializedModelSizeMB": model_size_mb,
        })

        class_rows.extend(
            class_metrics_rows(
                model_name,
                validation[TARGET],
                validation_pred,
            )
        )

        confusion_output_rows.extend(
            confusion_rows(
                model_name,
                validation[TARGET],
                validation_pred,
            )
        )

        print(
            f"Train CV Macro F1             : "
            f"{cv_f1_mean:.6f} +/- {cv_f1_std:.6f}"
        )
        print(
            f"Validation Accuracy           : "
            f"{metrics['Accuracy']:.6f}"
        )
        print(
            f"Validation Macro F1           : "
            f"{metrics['F1Macro']:.6f}"
        )
        print(
            f"Fit time                      : "
            f"{fit_seconds:.4f} sec"
        )
        print(
            f"Avg prediction time / claim   : "
            f"{avg_prediction_ms:.4f} ms"
        )
        print(
            f"Serialized model size         : "
            f"{model_size_mb:.4f} MB"
        )

    comparison = pd.DataFrame(
        comparison_rows
    )

    # Selection:
    # 1) Validation Macro F1
    # 2) Validation Accuracy
    # 3) Train CV Macro F1 mean
    # No test data is used.
    ranked = comparison.sort_values(
        [
            "ValidationMacroF1",
            "ValidationAccuracy",
            "CVMacroF1Mean",
        ],
        ascending=[False, False, False],
    ).reset_index(drop=True)

    ranked.insert(
        0,
        "Rank",
        np.arange(1, len(ranked) + 1),
    )

    best_row = ranked.iloc[0]
    best_model_name = str(
        best_row["Model"]
    )

    ranked.to_csv(
        COMPARISON_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    pd.DataFrame(
        class_rows
    ).to_csv(
        CLASS_METRICS_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    pd.DataFrame(
        confusion_output_rows
    ).to_csv(
        CONFUSION_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    selection = {
        "selected_model": best_model_name,
        "selection_basis": [
            "Validation Macro F1",
            "Validation Accuracy",
            "Train 5-fold CV Macro F1 mean",
        ],
        "validation_macro_f1": float(
            best_row["ValidationMacroF1"]
        ),
        "validation_accuracy": float(
            best_row["ValidationAccuracy"]
        ),
        "cv_macro_f1_mean": float(
            best_row["CVMacroF1Mean"]
        ),
        "feature_count": int(
            best_row["FeatureCount"]
        ),
        "selected_features_file": str(
            SELECTED_FEATURES_PATH
        ),
        "candidate_model_file": str(
            model_output_path(best_model_name)
        ),
        "test_used": False,
        "note": (
            "Candidate model file is trained on Train only. "
            "The selected algorithm will be refit on Train+Validation "
            "before the single final Test evaluation."
        ),
    }

    SELECTION_PATH.write_text(
        json.dumps(
            selection,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    manifest = {
        "train_rows": int(len(train)),
        "validation_rows": int(len(validation)),
        "test_loaded": False,
        "feature_count": int(
            len(selected_features)
        ),
        "selected_features": selected_features,
        "algorithms_compared": list(
            models.keys()
        ),
        "cv": {
            "type": "StratifiedKFold",
            "folds": CV_SPLITS,
            "random_seed": RANDOM_SEED,
        },
        "selection": selection,
        "rules": {
            "features_frozen": True,
            "test_used_for_model_selection": False,
            "validation_primary_metric": "Macro F1",
            "final_model_created": False,
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

    print("\n" + "=" * 72)
    print("MODEL SELECTION COMPLETE")
    print("=" * 72)

    for _, row in ranked.iterrows():
        print(
            f"#{int(row['Rank'])} "
            f"{row['Model']:<22} "
            f"Val F1={row['ValidationMacroF1']:.6f} "
            f"Val Acc={row['ValidationAccuracy']:.6f} "
            f"CV F1={row['CVMacroF1Mean']:.6f}"
        )

    print(
        f"\nSelected algorithm            : {best_model_name}"
    )
    print(
        f"Selected Validation Macro F1  : "
        f"{float(best_row['ValidationMacroF1']):.6f}"
    )
    print(
        "Test used                     : NO"
    )

    print("\nCreated:")
    for path in [
        COMPARISON_PATH,
        CLASS_METRICS_PATH,
        CONFUSION_PATH,
        SELECTION_PATH,
        LOGISTIC_MODEL_PATH,
        RF_MODEL_PATH,
        GB_MODEL_PATH,
        MANIFEST_PATH,
    ]:
        print(f" - {path}")

    print("\nIMPORTANT:")
    print(
        " - The best ALGORITHM is now frozen."
    )
    print(
        " - Candidate .joblib files are not yet the final production model."
    )
    print(
        " - Next step: refit the selected algorithm on Train+Validation, "
        "then open FINAL TEST exactly once."
    )


if __name__ == "__main__":
    main()
