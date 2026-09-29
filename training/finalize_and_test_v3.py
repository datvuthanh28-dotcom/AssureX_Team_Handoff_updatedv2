from pathlib import Path
import hashlib
import json
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    OneHotEncoder,
    StandardScaler,
)
ROOT = Path(__file__).resolve().parent.parent
TRAIN_PATH = (
    ROOT
    / "data/train/assurex_v3_train.csv"
)
VALIDATION_PATH = (
    ROOT
    / "data/validation/assurex_v3_validation.csv"
)
TEST_PATH = (
    ROOT
    / "data/test/assurex_v3_test.csv"
)
SELECTED_PATH = (
    ROOT
    / "data/feature_selection_v3"
    / "assurex_v3_selected_features.csv"
)
COMPARISON_PATH = (
    ROOT
    / "data/model_comparison_v3"
    / "assurex_v3_model_comparison.csv"
)
MODEL_DIR = ROOT / "model"
OUT_DIR = (
    ROOT
    / "data/final_evaluation_v3"
)
AUDIT_DIR = (
    ROOT
    / "data/audit"
)
for folder in [
    MODEL_DIR,
    OUT_DIR,
    AUDIT_DIR,
]:
    folder.mkdir(
        parents=True,
        exist_ok=True,
    )
FINAL_MODEL_PATH = (
    MODEL_DIR
    / "assurex_v3_final_model.joblib"
)
FINAL_FEATURES_PATH = (
    MODEL_DIR
    / "assurex_v3_final_features.csv"
)
FREEZE_MANIFEST_PATH = (
    AUDIT_DIR
    / "assurex_v3_model_freeze_manifest.json"
)
FINAL_MANIFEST_PATH = (
    AUDIT_DIR
    / "assurex_v3_final_evaluation_manifest.json"
)
METRICS_PATH = (
    OUT_DIR
    / "assurex_v3_test_metrics.csv"
)
PREDICTIONS_PATH = (
    OUT_DIR
    / "assurex_v3_test_predictions.csv"
)
CONFUSION_PATH = (
    OUT_DIR
    / "assurex_v3_test_confusion_matrix.csv"
)
REPORT_PATH = (
    OUT_DIR
    / "assurex_v3_test_classification_report.csv"
)
TARGET = "ClaimClass"
EXPECTED_WINNER = "Gradient Boosting"
RANDOM_SEED = 20260926
LABELS = [
    "Valid Claim",
    "Invalid Claim",
    "Manual Review",
]


def read_csv(path):
    return pd.read_csv(
        path,
        keep_default_na=False,
        na_values=[""],
    )


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(1024 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def selected_features():
    df = pd.read_csv(
        SELECTED_PATH
    )
    features = (
        df.loc[
            df["Selected"]
            .astype(str)
            .str.lower()
            .isin([
                "true",
                "1",
                "yes",
            ]),
            "Feature",
        ]
        .tolist()
    )
    if not features:
        raise RuntimeError(
            "No selected features found."
        )
    return features


def infer_types(
    frame,
    features,
):
    numeric = []
    categorical = []
    for column in features:
        series = frame[column]
        observed = int(
            series.notna().sum()
        )
        parsed = pd.to_numeric(
            series,
            errors="coerce",
        )
        if (
            observed > 0
            and (
                parsed.notna().sum()
                / observed
            ) >= 0.95
        ):
            numeric.append(column)
        else:
            categorical.append(
                column
            )
    return numeric, categorical


def build_pipeline(
    training_frame,
    features,
):
    numeric, categorical = infer_types(
        training_frame,
        features,
    )
    numeric_pipeline = Pipeline([
        (
            "imputer",
            SimpleImputer(
                strategy="median"
            ),
        ),
        (
            "scaler",
            StandardScaler(),
        ),
    ])
    categorical_pipeline = Pipeline([
        (
            "imputer",
            SimpleImputer(
                strategy="most_frequent"
            ),
        ),
        (
            "encoder",
            OneHotEncoder(
                handle_unknown="ignore",
                sparse_output=False,
            ),
        ),
    ])
    preprocessor = ColumnTransformer([
        (
            "numeric",
            numeric_pipeline,
            numeric,
        ),
        (
            "categorical",
            categorical_pipeline,
            categorical,
        ),
    ])
    model = GradientBoostingClassifier(
        n_estimators=150,
        learning_rate=0.05,
        max_depth=3,
        random_state=RANDOM_SEED,
    )
    pipeline = Pipeline([
        (
            "preprocessor",
            preprocessor,
        ),
        (
            "model",
            model,
        ),
    ])
    return pipeline


def leakage_check(features):
    forbidden_exact = {
        "ClaimClass",
        "ClaimID",
        "PolicyClass",
        "HardInvalidReasons",
        "ManualReviewReasons",
        "WarrantyTimingContextTruth",
        "WarrantyRemainingDaysTruth",
        "ReportingDelayDaysTruth",
        "ComponentWarrantyEligibleTruth",
        "ApplicableWarrantyMonthsTruth",
        "EffectiveWarrantyMonthsTruth",
    }
    forbidden_tokens = [
        "truth",
        "target",
        "label",
        "policyclass",
        "hardinvalidreason",
        "manualreviewreason",
    ]
    bad = []
    for feature in features:
        key = feature.casefold()
        if feature in forbidden_exact:
            bad.append(feature)
        elif any(
            token in key
            for token in forbidden_tokens
        ):
            bad.append(feature)
    if bad:
        raise RuntimeError(
            "Leakage candidates found: "
            + ", ".join(bad)
        )


def main():
    train = read_csv(
        TRAIN_PATH
    )
    validation = read_csv(
        VALIDATION_PATH
    )
    features = selected_features()
    leakage_check(
        features
    )
    if len(features) != 14:
        raise RuntimeError(
            f"Expected frozen 14 features, found {len(features)}."
        )
    comparison = pd.read_csv(
        COMPARISON_PATH
    )
    comparison = comparison.sort_values(
        [
            "ValidationMacroF1",
            "ValidationAccuracy",
        ],
        ascending=False,
    )
    winner = str(
        comparison.iloc[0]["Model"]
    )
    validation_f1 = float(
        comparison.iloc[0][
            "ValidationMacroF1"
        ]
    )
    if winner != EXPECTED_WINNER:
        raise RuntimeError(
            f"Expected winner {EXPECTED_WINNER}, "
            f"found {winner}."
        )
    train_ids = set(
        train["ClaimID"]
    )
    validation_ids = set(
        validation["ClaimID"]
    )
    if train_ids & validation_ids:
        raise RuntimeError(
            "Train / Validation ClaimID overlap."
        )
    for feature in features:
        if (
            feature not in train.columns
            or feature
            not in validation.columns
        ):
            raise RuntimeError(
                f"Frozen feature missing: {feature}"
            )
    development = pd.concat(
        [
            train,
            validation,
        ],
        ignore_index=True,
    )
    if len(development) != 1275:
        raise RuntimeError(
            f"Expected 1275 development claims, "
            f"found {len(development)}."
        )
    development_counts = (
        development[TARGET]
        .value_counts()
        .to_dict()
    )
    expected_development = {
        "Valid Claim": 425,
        "Invalid Claim": 425,
        "Manual Review": 425,
    }
    if development_counts != expected_development:
        raise RuntimeError(
            "Unexpected development class balance: "
            + str(development_counts)
        )
    pipeline = build_pipeline(
        development,
        features,
    )
    pipeline.fit(
        development[features],
        development[TARGET],
    )
    joblib.dump(
        pipeline,
        FINAL_MODEL_PATH,
    )
    pd.DataFrame({
        "Feature": features,
        "Selected": True,
        "FrozenOrder":
            range(
                1,
                len(features) + 1,
            ),
    }).to_csv(
        FINAL_FEATURES_PATH,
        index=False,
    )
    model_hash = sha256(
        FINAL_MODEL_PATH
    )
    freeze_manifest = {
        "status":
            "FROZEN_BEFORE_TEST",
        "winner":
            winner,
        "selection_metric":
            "Validation Macro F1",
        "validation_macro_f1":
            validation_f1,
        "train_rows":
            len(train),
        "validation_rows":
            len(validation),
        "refit_rows":
            len(development),
        "refit_class_counts":
            development_counts,
        "selected_feature_count":
            len(features),
        "selected_features":
            features,
        "model":
            "GradientBoostingClassifier",
        "hyperparameters": {
            "n_estimators": 150,
            "learning_rate": 0.05,
            "max_depth": 3,
            "random_state":
                RANDOM_SEED,
        },
        "model_path":
            str(FINAL_MODEL_PATH),
        "model_sha256":
            model_hash,
        "test_loaded":
            False,
        "test_used":
            False,
        "post_test_model_changes_allowed":
            False,
    }
    FREEZE_MANIFEST_PATH.write_text(
        json.dumps(
            freeze_manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("=" * 72)
    print("ASSUREX V3 - MODEL FROZEN")
    print("=" * 72)
    print(
        "Winner                 :",
        winner,
    )
    print(
        "Frozen feature count   :",
        len(features),
    )
    print(
        "Refit rows             :",
        len(development),
    )
    print(
        "Validation Macro F1    :",
        f"{validation_f1:.6f}",
    )
    print(
        "Test loaded so far     : NO"
    )
    print(
        "Model frozen           : YES"
    )
    print()
    test = read_csv(
        TEST_PATH
    )
    if len(test) != 225:
        raise RuntimeError(
            f"Expected 225 test rows, "
            f"found {len(test)}."
        )
    if (
        test["ClaimID"]
        .duplicated()
        .any()
    ):
        raise RuntimeError(
            "Duplicate ClaimID in Test."
        )
    if (
        set(test["ClaimID"])
        & set(development["ClaimID"])
    ):
        raise RuntimeError(
            "Development / Test ClaimID overlap."
        )
    test_counts = (
        test[TARGET]
        .value_counts()
        .to_dict()
    )
    expected_test = {
        "Valid Claim": 75,
        "Invalid Claim": 75,
        "Manual Review": 75,
    }
    if test_counts != expected_test:
        raise RuntimeError(
            "Unexpected Test class distribution: "
            + str(test_counts)
        )
    for feature in features:
        if feature not in test.columns:
            raise RuntimeError(
                f"Frozen feature missing in Test: {feature}"
            )
    X_test = test[features]
    y_test = test[TARGET]
    predictions = pipeline.predict(
        X_test
    )
    probabilities = pipeline.predict_proba(
        X_test
    )
    classes = list(
        pipeline.classes_
    )
    confidence = (
        probabilities.max(axis=1)
    )
    accuracy = accuracy_score(
        y_test,
        predictions,
    )
    macro_precision = precision_score(
        y_test,
        predictions,
        average="macro",
        zero_division=0,
    )
    macro_recall = recall_score(
        y_test,
        predictions,
        average="macro",
        zero_division=0,
    )
    macro_f1 = f1_score(
        y_test,
        predictions,
        average="macro",
    )
    errors = int(
        (
            predictions
            != y_test.to_numpy()
        ).sum()
    )
    mean_confidence = float(
        confidence.mean()
    )
    metrics = pd.DataFrame([
        {
            "Metric":
                "TestAccuracy",
            "Value":
                accuracy,
        },
        {
            "Metric":
                "TestMacroPrecision",
            "Value":
                macro_precision,
        },
        {
            "Metric":
                "TestMacroRecall",
            "Value":
                macro_recall,
        },
        {
            "Metric":
                "TestMacroF1",
            "Value":
                macro_f1,
        },
        {
            "Metric":
                "MeanConfidence",
            "Value":
                mean_confidence,
        },
        {
            "Metric":
                "Errors",
            "Value":
                errors,
        },
    ])
    metrics.to_csv(
        METRICS_PATH,
        index=False,
    )
    prediction_df = pd.DataFrame({
        "ClaimID":
            test["ClaimID"],
        "Actual":
            y_test,
        "Predicted":
            predictions,
        "Correct":
            (
                y_test.to_numpy()
                == predictions
            ),
        "Confidence":
            confidence,
    })
    for index, label in enumerate(
        classes
    ):
        safe_name = (
            label
            .replace(" ", "_")
        )
        prediction_df[
            f"Probability_{safe_name}"
        ] = probabilities[:, index]
    prediction_df.to_csv(
        PREDICTIONS_PATH,
        index=False,
    )
    cm = confusion_matrix(
        y_test,
        predictions,
        labels=LABELS,
    )
    cm_df = pd.DataFrame(
        cm,
        index=[
            f"Actual_{x}"
            for x in LABELS
        ],
        columns=[
            f"Predicted_{x}"
            for x in LABELS
        ],
    )
    cm_df.to_csv(
        CONFUSION_PATH,
    )
    report = classification_report(
        y_test,
        predictions,
        labels=LABELS,
        output_dict=True,
        zero_division=0,
    )
    pd.DataFrame(
        report
    ).T.to_csv(
        REPORT_PATH,
    )
    final_manifest = {
        **freeze_manifest,
        "status":
            "FINAL_TEST_COMPLETED",
        "test_loaded":
            True,
        "test_used":
            True,
        "test_rows":
            len(test),
        "test_class_counts":
            test_counts,
        "test_accuracy":
            accuracy,
        "test_macro_precision":
            macro_precision,
        "test_macro_recall":
            macro_recall,
        "test_macro_f1":
            macro_f1,
        "test_mean_confidence":
            mean_confidence,
        "test_errors":
            errors,
        "model_sha256_after_test":
            sha256(
                FINAL_MODEL_PATH
            ),
        "model_changed_after_test":
            (
                sha256(
                    FINAL_MODEL_PATH
                )
                != model_hash
            ),
    }
    FINAL_MANIFEST_PATH.write_text(
        json.dumps(
            final_manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    if (
        final_manifest[
            "model_changed_after_test"
        ]
    ):
        raise RuntimeError(
            "Frozen model changed after Test."
        )
    print("=" * 72)
    print("ASSUREX V3 - FINAL LOCKED TEST")
    print("=" * 72)
    print(
        f"Test Accuracy          : {accuracy:.6f}"
    )
    print(
        f"Test Macro Precision   : {macro_precision:.6f}"
    )
    print(
        f"Test Macro Recall      : {macro_recall:.6f}"
    )
    print(
        f"Test Macro F1          : {macro_f1:.6f}"
    )
    print(
        f"Mean Confidence        : {mean_confidence:.6f}"
    )
    print(
        f"Errors / 225           : {errors}"
    )
    print()
    print("Confusion Matrix:")
    print(
        cm_df.to_string()
    )
    print()
    print(
        "Model changed after test: NO"
    )
    print(
        "Test evaluation complete."
    )
    print()
    print("Created:")
    for path in [
        FINAL_MODEL_PATH,
        FINAL_FEATURES_PATH,
        FREEZE_MANIFEST_PATH,
        METRICS_PATH,
        PREDICTIONS_PATH,
        CONFUSION_PATH,
        REPORT_PATH,
        FINAL_MANIFEST_PATH,
    ]:
        print(" -", path)
if __name__ == "__main__":
    main()
