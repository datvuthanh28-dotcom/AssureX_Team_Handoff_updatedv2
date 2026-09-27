from __future__ import annotations

from pathlib import Path
import json
import time

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


# ============================================================
# ASSUREX CLAIM ENGINE - REFIT BEST MODEL + FINAL TEST ONCE
# ============================================================
# Purpose:
# - Read the algorithm selected from Train + Validation only.
# - Refit that algorithm on Train + Validation.
# - Open the locked Test set once for the final unbiased evaluation.
# - Save the final Python model and final test evidence.
#
# IMPORTANT:
# - No feature/model/hyperparameter decision is made from Test.
# - Test results are reporting only.
# - This script must not be rerun to tune the model.
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

TRAIN_PATH = PROJECT_ROOT / "data" / "train" / "assurex_train.csv"
VALIDATION_PATH = PROJECT_ROOT / "data" / "validation" / "assurex_validation.csv"
TEST_PATH = PROJECT_ROOT / "data" / "test" / "assurex_test.csv"

SELECTED_FEATURES_PATH = (
    PROJECT_ROOT
    / "data"
    / "feature_selection"
    / "selected_features_final.csv"
)

SELECTION_PATH = PROJECT_ROOT / "model" / "best_model_selection.json"

MODEL_DIR = PROJECT_ROOT / "model"
AUDIT_DIR = PROJECT_ROOT / "data" / "audit"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

FINAL_MODEL_PATH = MODEL_DIR / "assurex_final_model.joblib"
FINAL_METRICS_PATH = MODEL_DIR / "final_test_metrics.csv"
FINAL_CLASS_METRICS_PATH = MODEL_DIR / "final_test_class_metrics.csv"
FINAL_CONFUSION_PATH = MODEL_DIR / "final_test_confusion_matrix.csv"
FINAL_PREDICTIONS_PATH = MODEL_DIR / "final_test_predictions.csv"
FINAL_INFO_PATH = MODEL_DIR / "final_model_info.json"
FINAL_MANIFEST_PATH = AUDIT_DIR / "final_test_manifest.json"


TARGET = "ClaimClass"
ID_COLUMN = "ClaimID"
RANDOM_SEED = 20260925

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
            f"Frozen selected feature file not found:\n{path}"
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
        f.strip()
        for f in features
        if f.strip()
    ]

    if not features:
        raise ValueError("No frozen selected features found.")

    return features


def load_selected_algorithm(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(
            f"Model selection file not found:\n{path}"
        )

    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    selected = data.get("selected_model")

    if not selected:
        raise ValueError(
            "best_model_selection.json does not contain selected_model."
        )

    return str(selected)


def validate_data(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
    features: list[str],
) -> None:
    for name, df in [
        ("Train", train),
        ("Validation", validation),
        ("Test", test),
    ]:
        if df.empty:
            raise ValueError(f"{name} dataset is empty.")

        if TARGET not in df.columns:
            raise ValueError(f"{name}: missing target {TARGET}.")

        if ID_COLUMN not in df.columns:
            raise ValueError(f"{name}: missing ClaimID.")

        if df[ID_COLUMN].duplicated().any():
            raise ValueError(f"{name}: duplicate ClaimID found.")

        missing = [
            feature
            for feature in features
            if feature not in df.columns
        ]

        if missing:
            raise ValueError(
                f"{name}: missing frozen features: "
                + ", ".join(missing)
            )

    train_ids = set(train[ID_COLUMN])
    validation_ids = set(validation[ID_COLUMN])
    test_ids = set(test[ID_COLUMN])

    if train_ids & validation_ids:
        raise ValueError("Train / Validation ClaimID overlap detected.")

    if train_ids & test_ids:
        raise ValueError("Train / Test ClaimID overlap detected.")

    if validation_ids & test_ids:
        raise ValueError("Validation / Test ClaimID overlap detected.")

    if len(train) != 1050:
        raise ValueError(f"Expected 1050 Train rows, found {len(train)}.")

    if len(validation) != 225:
        raise ValueError(
            f"Expected 225 Validation rows, found {len(validation)}."
        )

    if len(test) != 225:
        raise ValueError(f"Expected 225 Test rows, found {len(test)}.")


def infer_feature_types(
    train_reference: pd.DataFrame,
    features: list[str],
) -> tuple[list[str], list[str]]:
    numeric_features = []
    categorical_features = []

    for column in features:
        series = train_reference[column]
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
    selected_algorithm: str,
) -> Pipeline:
    numeric_features, categorical_features = infer_feature_types(
        train_reference,
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

    preprocessor = ColumnTransformer(
        transformers=transformers,
        remainder="drop",
    )

    if selected_algorithm == "Gradient Boosting":
        model = GradientBoostingClassifier(
            n_estimators=150,
            learning_rate=0.05,
            max_depth=3,
            random_state=RANDOM_SEED,
        )
    else:
        raise ValueError(
            "This final-test script currently expects the selected "
            f"algorithm to be Gradient Boosting, found: {selected_algorithm}"
        )

    return Pipeline([
        ("preprocessor", preprocessor),
        ("model", model),
    ])


def class_metric_rows(
    y_true: pd.Series,
    y_pred: np.ndarray,
) -> list[dict]:
    rows = []

    for label in CLASS_ORDER:
        true_binary = (y_true == label).astype(int)
        pred_binary = (y_pred == label).astype(int)

        rows.append({
            "Class": label,
            "Precision": precision_score(
                true_binary,
                pred_binary,
                zero_division=0,
            ),
            "Recall": recall_score(
                true_binary,
                pred_binary,
                zero_division=0,
            ),
            "F1": f1_score(
                true_binary,
                pred_binary,
                zero_division=0,
            ),
            "Support": int(true_binary.sum()),
        })

    return rows


def main():
    print("=" * 72)
    print("ASSUREX - FINAL PYTHON TEST")
    print("=" * 72)

    selected_features = load_selected_features(
        SELECTED_FEATURES_PATH
    )

    selected_algorithm = load_selected_algorithm(
        SELECTION_PATH
    )

    # Test is intentionally first opened here, after all choices are frozen.
    train = read_csv(TRAIN_PATH)
    validation = read_csv(VALIDATION_PATH)
    test = read_csv(TEST_PATH)

    validate_data(
        train,
        validation,
        test,
        selected_features,
    )

    train_validation = pd.concat(
        [train, validation],
        ignore_index=True,
    )

    pipeline = build_pipeline(
        train_validation,
        selected_features,
        selected_algorithm,
    )

    print(f"Selected algorithm            : {selected_algorithm}")
    print(f"Frozen selected features      : {len(selected_features)}")
    print(f"Train + Validation rows       : {len(train_validation)}")
    print(f"Locked Test rows              : {len(test)}")
    print("Model / feature choices       : FROZEN")

    fit_start = time.perf_counter()

    pipeline.fit(
        train_validation[selected_features],
        train_validation[TARGET],
    )

    fit_seconds = time.perf_counter() - fit_start

    # --------------------------------------------------------
    # FINAL TEST PREDICTION
    # One reporting evaluation. No tuning follows.
    # --------------------------------------------------------
    predict_start = time.perf_counter()

    test_pred = pipeline.predict(
        test[selected_features]
    )

    predict_seconds = (
        time.perf_counter()
        - predict_start
    )

    if hasattr(pipeline, "predict_proba"):
        probabilities = pipeline.predict_proba(
            test[selected_features]
        )
        classes = list(pipeline.classes_)
        max_confidence = probabilities.max(axis=1)
    else:
        probabilities = None
        classes = []
        max_confidence = np.full(
            len(test),
            np.nan,
        )

    accuracy = float(
        accuracy_score(
            test[TARGET],
            test_pred,
        )
    )

    precision_macro = float(
        precision_score(
            test[TARGET],
            test_pred,
            average="macro",
            zero_division=0,
        )
    )

    recall_macro = float(
        recall_score(
            test[TARGET],
            test_pred,
            average="macro",
            zero_division=0,
        )
    )

    macro_f1 = float(
        f1_score(
            test[TARGET],
            test_pred,
            average="macro",
            zero_division=0,
        )
    )

    class_metrics = pd.DataFrame(
        class_metric_rows(
            test[TARGET],
            test_pred,
        )
    )

    cm = confusion_matrix(
        test[TARGET],
        test_pred,
        labels=CLASS_ORDER,
    )

    confusion_df = pd.DataFrame(
        cm,
        index=[
            f"Actual_{label}"
            for label in CLASS_ORDER
        ],
        columns=[
            f"Predicted_{label}"
            for label in CLASS_ORDER
        ],
    )

    predictions = pd.DataFrame({
        "ClaimID": test[ID_COLUMN],
        "ActualClass": test[TARGET],
        "PredictedClass": test_pred,
        "Correct": (
            test[TARGET].to_numpy()
            == test_pred
        ),
        "Confidence": max_confidence,
    })

    if probabilities is not None:
        for idx, label in enumerate(classes):
            safe_label = (
                label.replace(" ", "")
                .replace("/", "_")
            )
            predictions[
                f"Probability_{safe_label}"
            ] = probabilities[:, idx]

    metrics_df = pd.DataFrame([
        {
            "Model": selected_algorithm,
            "FeatureCount": len(selected_features),
            "TrainValidationRows": len(
                train_validation
            ),
            "TestRows": len(test),
            "TestAccuracy": accuracy,
            "TestPrecisionMacro": precision_macro,
            "TestRecallMacro": recall_macro,
            "TestMacroF1": macro_f1,
            "FitSeconds": float(fit_seconds),
            "TestPredictionSeconds": float(
                predict_seconds
            ),
            "AvgPredictionMsPerClaim": float(
                predict_seconds
                / len(test)
                * 1000.0
            ),
            "MeanConfidence": float(
                np.nanmean(max_confidence)
            ),
            "LowConfidenceUnder060": int(
                np.nansum(
                    max_confidence < 0.60
                )
            ),
        }
    ])

    joblib.dump(
        pipeline,
        FINAL_MODEL_PATH,
    )

    model_size_mb = (
        FINAL_MODEL_PATH.stat().st_size
        / (1024.0 * 1024.0)
    )

    metrics_df[
        "SerializedModelSizeMB"
    ] = model_size_mb

    metrics_df.to_csv(
        FINAL_METRICS_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    class_metrics.to_csv(
        FINAL_CLASS_METRICS_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    confusion_df.to_csv(
        FINAL_CONFUSION_PATH,
        encoding="utf-8-sig",
    )

    predictions.to_csv(
        FINAL_PREDICTIONS_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    final_info = {
        "model": selected_algorithm,
        "random_seed": RANDOM_SEED,
        "feature_count": len(selected_features),
        "selected_features": selected_features,
        "training_rows": int(
            len(train_validation)
        ),
        "test_rows": int(len(test)),
        "test_metrics": {
            "accuracy": accuracy,
            "precision_macro": precision_macro,
            "recall_macro": recall_macro,
            "macro_f1": macro_f1,
        },
        "efficiency": {
            "fit_seconds": float(
                fit_seconds
            ),
            "test_prediction_seconds": float(
                predict_seconds
            ),
            "average_prediction_ms_per_claim": float(
                predict_seconds
                / len(test)
                * 1000.0
            ),
            "serialized_model_size_mb": float(
                model_size_mb
            ),
        },
        "model_file": str(
            FINAL_MODEL_PATH
        ),
        "test_predictions_file": str(
            FINAL_PREDICTIONS_PATH
        ),
    }

    FINAL_INFO_PATH.write_text(
        json.dumps(
            final_info,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    manifest = {
        "algorithm_frozen_before_test": True,
        "feature_set_frozen_before_test": True,
        "hyperparameters_frozen_before_test": True,
        "refit_data": "Train + Validation",
        "test_rows": int(len(test)),
        "test_claimids_unique": bool(
            test[ID_COLUMN].is_unique
        ),
        "test_metrics_used_for_tuning": False,
        "next_steps_may_report_but_must_not_retune": True,
        "outputs": {
            "final_model": str(FINAL_MODEL_PATH),
            "metrics": str(FINAL_METRICS_PATH),
            "class_metrics": str(
                FINAL_CLASS_METRICS_PATH
            ),
            "confusion_matrix": str(
                FINAL_CONFUSION_PATH
            ),
            "predictions": str(
                FINAL_PREDICTIONS_PATH
            ),
            "model_info": str(
                FINAL_INFO_PATH
            ),
        },
    }

    FINAL_MANIFEST_PATH.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\nFINAL TEST RESULTS")
    print("-" * 72)
    print(f"Accuracy                      : {accuracy:.6f}")
    print(f"Macro Precision               : {precision_macro:.6f}")
    print(f"Macro Recall                  : {recall_macro:.6f}")
    print(f"Macro F1                      : {macro_f1:.6f}")
    print(f"Mean confidence               : {np.nanmean(max_confidence):.6f}")
    print(
        f"Low confidence (<0.60)        : "
        f"{int(np.nansum(max_confidence < 0.60))}"
    )
    print(f"Fit time                      : {fit_seconds:.4f} sec")
    print(
        f"Avg prediction time / claim   : "
        f"{predict_seconds / len(test) * 1000.0:.4f} ms"
    )
    print(
        f"Serialized model size         : "
        f"{model_size_mb:.4f} MB"
    )

    print("\nPer-class metrics:")
    for _, row in class_metrics.iterrows():
        print(
            f" - {row['Class']:<15} "
            f"P={row['Precision']:.4f} "
            f"R={row['Recall']:.4f} "
            f"F1={row['F1']:.4f} "
            f"N={int(row['Support'])}"
        )

    print("\nCreated:")
    for path in [
        FINAL_MODEL_PATH,
        FINAL_METRICS_PATH,
        FINAL_CLASS_METRICS_PATH,
        FINAL_CONFUSION_PATH,
        FINAL_PREDICTIONS_PATH,
        FINAL_INFO_PATH,
        FINAL_MANIFEST_PATH,
    ]:
        print(f" - {path}")

    print("\nIMPORTANT:")
    print(
        " - FINAL TEST is now consumed for reporting."
    )
    print(
        " - Do not change features/model/hyperparameters based on these results."
    )
    print(
        " - assurex_final_model.joblib is now the FINAL PYTHON MODEL."
    )
    print(
        " - Next stage: final model-native feature importance + sanity check."
    )


if __name__ == "__main__":
    main()
