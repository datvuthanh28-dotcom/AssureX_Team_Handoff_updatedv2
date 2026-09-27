from __future__ import annotations

from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd

from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, f1_score, recall_score


# ============================================================
# ASSUREX CLAIM ENGINE - FINAL MODEL ANALYSIS / SANITY CHECK
# ============================================================
# This is a POST-HOC reporting stage only.
#
# It:
# 1) Computes model-native Gradient Boosting feature importance,
#    aggregated back to ORIGINAL selected features.
# 2) Computes permutation importance on the already-consumed final Test set
#    for reporting/sanity only.
# 3) Audits selected features for identifiers/noise.
# 4) Audits final performance, per-class recall, confidence, errors,
#    model size and latency against project expectations.
#
# It MUST NOT:
# - remove features
# - change hyperparameters
# - choose a different model
# - retrain/tune based on Test
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MODEL_DIR = PROJECT_ROOT / "model"
AUDIT_DIR = PROJECT_ROOT / "data" / "audit"
FS_DIR = PROJECT_ROOT / "data" / "feature_selection"

FINAL_MODEL_PATH = MODEL_DIR / "assurex_final_model.joblib"
FINAL_PREDICTIONS_PATH = MODEL_DIR / "final_test_predictions.csv"
FINAL_METRICS_PATH = MODEL_DIR / "final_test_metrics.csv"
FINAL_CLASS_METRICS_PATH = MODEL_DIR / "final_test_class_metrics.csv"
TEST_PATH = PROJECT_ROOT / "data" / "test" / "assurex_test.csv"
SELECTED_FEATURES_PATH = FS_DIR / "selected_features_final.csv"

NATIVE_IMPORTANCE_PATH = MODEL_DIR / "final_native_feature_importance.csv"
PERM_IMPORTANCE_PATH = MODEL_DIR / "final_permutation_importance.csv"
ERROR_ANALYSIS_PATH = MODEL_DIR / "final_error_analysis.csv"
CONFIDENCE_PATH = MODEL_DIR / "final_confidence_analysis.csv"
SANITY_PATH = MODEL_DIR / "final_sanity_check.csv"
REPORT_PATH = MODEL_DIR / "final_python_model_report.txt"
MANIFEST_PATH = AUDIT_DIR / "final_model_analysis_manifest.json"

TARGET = "ClaimClass"
RANDOM_SEED = 20260925

FORBIDDEN_IDENTIFIER_FEATURES = {
    "RecordID",
    "ClaimID",
    "CustomerID",
    "ProductID",
    "ModelNumber",
    "SerialNumber",
    "InternalBatchCode",
}

KNOWN_NOISE_FEATURES = {
    "BrowserFamily",
    "SubmissionMinute",
    "UiTheme",
    "RandomScore",
    "InternalBatchCode",
}

CLASS_ORDER = [
    "Invalid Claim",
    "Manual Review",
    "Valid Claim",
]

# SRS/project sanity expectations
MIN_OVERALL_ACCURACY = 0.85
MIN_MACRO_F1 = 0.85
MIN_CLASS_RECALL = 0.85
MAX_NORMAL_RESPONSE_SECONDS = 5.0

PERMUTATION_REPEATS = 15


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        keep_default_na=False,
        na_values=[""],
    )


def load_selected_features(path: Path) -> list[str]:
    df = pd.read_csv(path)

    if "Feature" not in df.columns:
        raise ValueError(
            "selected_features_final.csv must contain Feature."
        )

    if "Selected" in df.columns:
        mask = df["Selected"].astype(str).str.lower().isin(
            ["true", "1", "yes"]
        )
        features = df.loc[mask, "Feature"].astype(str).tolist()
    else:
        features = df["Feature"].astype(str).tolist()

    return [
        f.strip()
        for f in features
        if f.strip()
    ]


def validate_files() -> None:
    required = [
        FINAL_MODEL_PATH,
        FINAL_PREDICTIONS_PATH,
        FINAL_METRICS_PATH,
        FINAL_CLASS_METRICS_PATH,
        TEST_PATH,
        SELECTED_FEATURES_PATH,
    ]

    missing = [
        str(path)
        for path in required
        if not path.exists()
    ]

    if missing:
        raise FileNotFoundError(
            "Missing required final artifacts:\n"
            + "\n".join(missing)
        )


def original_native_importance(
    pipeline,
    selected_features: list[str],
) -> pd.DataFrame:
    if "preprocessor" not in pipeline.named_steps:
        raise ValueError(
            "Final model pipeline has no preprocessor."
        )

    if "model" not in pipeline.named_steps:
        raise ValueError(
            "Final model pipeline has no model."
        )

    preprocessor = pipeline.named_steps["preprocessor"]
    model = pipeline.named_steps["model"]

    if not hasattr(model, "feature_importances_"):
        raise ValueError(
            "Selected final model does not expose feature_importances_."
        )

    importances = np.asarray(
        model.feature_importances_,
        dtype=float,
    )

    aggregated = {
        feature: 0.0
        for feature in selected_features
    }

    offset = 0

    for name, transformer, columns in preprocessor.transformers_:
        if name == "remainder":
            continue

        columns = list(columns)

        if transformer == "drop":
            continue

        if transformer == "passthrough":
            count = len(columns)

            for j, column in enumerate(columns):
                aggregated[column] += float(
                    importances[offset + j]
                )

            offset += count
            continue

        # sklearn Pipeline
        if hasattr(transformer, "named_steps"):
            if "onehot" in transformer.named_steps:
                encoder = transformer.named_steps["onehot"]

                for column, categories in zip(
                    columns,
                    encoder.categories_,
                ):
                    count = len(categories)

                    aggregated[column] += float(
                        importances[
                            offset: offset + count
                        ].sum()
                    )

                    offset += count

            else:
                count = len(columns)

                for j, column in enumerate(columns):
                    aggregated[column] += float(
                        importances[offset + j]
                    )

                offset += count

        else:
            count = len(columns)

            for j, column in enumerate(columns):
                aggregated[column] += float(
                    importances[offset + j]
                )

            offset += count

    if offset != len(importances):
        raise RuntimeError(
            "Could not map all transformed model importances "
            f"back to original features: mapped {offset}, "
            f"model has {len(importances)}."
        )

    result = pd.DataFrame([
        {
            "Feature": feature,
            "NativeImportance": importance,
        }
        for feature, importance in aggregated.items()
    ])

    total = result["NativeImportance"].sum()

    if total > 0:
        result["NativeImportanceNormalized"] = (
            result["NativeImportance"] / total
        )
    else:
        result["NativeImportanceNormalized"] = 0.0

    return result.sort_values(
        ["NativeImportanceNormalized", "Feature"],
        ascending=[False, True],
    ).reset_index(drop=True)


def permutation_importance_report(
    pipeline,
    test: pd.DataFrame,
    selected_features: list[str],
) -> pd.DataFrame:
    result = permutation_importance(
        pipeline,
        test[selected_features],
        test[TARGET],
        scoring="f1_macro",
        n_repeats=PERMUTATION_REPEATS,
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )

    frame = pd.DataFrame({
        "Feature": selected_features,
        "PermutationImportanceMean": result.importances_mean,
        "PermutationImportanceStd": result.importances_std,
    })

    frame["PermutationImportanceLower"] = (
        frame["PermutationImportanceMean"]
        - frame["PermutationImportanceStd"]
    )

    frame["Interpretation"] = np.select(
        [
            frame["PermutationImportanceMean"] > 0.03,
            frame["PermutationImportanceMean"] > 0.01,
            frame["PermutationImportanceMean"] > 0.002,
        ],
        [
            "High",
            "Moderate",
            "Low positive",
        ],
        default="Near-zero / negative",
    )

    return frame.sort_values(
        ["PermutationImportanceMean", "Feature"],
        ascending=[False, True],
    ).reset_index(drop=True)


def confidence_analysis(
    predictions: pd.DataFrame,
) -> pd.DataFrame:
    bins = [
        0.0,
        0.60,
        0.70,
        0.80,
        0.90,
        1.0000001,
    ]

    labels = [
        "<0.60",
        "0.60-0.70",
        "0.70-0.80",
        "0.80-0.90",
        ">=0.90",
    ]

    temp = predictions.copy()

    temp["ConfidenceBand"] = pd.cut(
        temp["Confidence"],
        bins=bins,
        labels=labels,
        right=False,
        include_lowest=True,
    )

    rows = []

    for band in labels:
        group = temp[
            temp["ConfidenceBand"] == band
        ]

        if group.empty:
            rows.append({
                "ConfidenceBand": band,
                "Claims": 0,
                "Correct": 0,
                "Incorrect": 0,
                "ObservedAccuracy": np.nan,
                "MeanConfidence": np.nan,
            })
            continue

        correct = int(
            group["Correct"].astype(bool).sum()
        )

        rows.append({
            "ConfidenceBand": band,
            "Claims": len(group),
            "Correct": correct,
            "Incorrect": len(group) - correct,
            "ObservedAccuracy": correct / len(group),
            "MeanConfidence": group["Confidence"].mean(),
        })

    return pd.DataFrame(rows)


def main():
    print("=" * 72)
    print("ASSUREX - FINAL FEATURE IMPORTANCE / SANITY CHECK")
    print("=" * 72)

    validate_files()

    pipeline = joblib.load(
        FINAL_MODEL_PATH
    )

    selected_features = load_selected_features(
        SELECTED_FEATURES_PATH
    )

    test = read_csv(TEST_PATH)
    predictions = read_csv(
        FINAL_PREDICTIONS_PATH
    )
    final_metrics = read_csv(
        FINAL_METRICS_PATH
    )
    class_metrics = read_csv(
        FINAL_CLASS_METRICS_PATH
    )

    if TARGET not in test.columns:
        raise ValueError(
            "Test dataset does not contain ClaimClass."
        )

    if test["ClaimID"].duplicated().any():
        raise ValueError(
            "Duplicate ClaimID found in final Test."
        )

    if set(predictions["ClaimID"]) != set(test["ClaimID"]):
        raise ValueError(
            "Final predictions ClaimIDs do not exactly match Test ClaimIDs."
        )

    missing_features = [
        f
        for f in selected_features
        if f not in test.columns
    ]

    if missing_features:
        raise ValueError(
            "Frozen selected features missing from Test: "
            + ", ".join(missing_features)
        )

    # --------------------------------------------------------
    # Final feature importance
    # --------------------------------------------------------
    native = original_native_importance(
        pipeline,
        selected_features,
    )

    native.to_csv(
        NATIVE_IMPORTANCE_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    permutation = permutation_importance_report(
        pipeline,
        test,
        selected_features,
    )

    permutation.to_csv(
        PERM_IMPORTANCE_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    # --------------------------------------------------------
    # Error / confidence analysis
    # --------------------------------------------------------
    errors = predictions[
        ~predictions["Correct"].astype(bool)
    ].copy()

    errors = errors.sort_values(
        ["Confidence", "ClaimID"],
        ascending=[False, True],
    )

    errors.to_csv(
        ERROR_ANALYSIS_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    confidence = confidence_analysis(
        predictions
    )

    confidence.to_csv(
        CONFIDENCE_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    # --------------------------------------------------------
    # Sanity checks
    # --------------------------------------------------------
    metric_row = final_metrics.iloc[0]

    accuracy = float(
        metric_row["TestAccuracy"]
    )
    macro_f1 = float(
        metric_row["TestMacroF1"]
    )
    avg_ms = float(
        metric_row["AvgPredictionMsPerClaim"]
    )
    model_size_mb = float(
        metric_row["SerializedModelSizeMB"]
    )

    class_recall = {
        str(row["Class"]): float(row["Recall"])
        for _, row in class_metrics.iterrows()
    }

    identifier_features = sorted(
        set(selected_features)
        & FORBIDDEN_IDENTIFIER_FEATURES
    )

    noise_features = sorted(
        set(selected_features)
        & KNOWN_NOISE_FEATURES
    )

    max_native_feature = str(
        native.iloc[0]["Feature"]
    )
    max_native_importance = float(
        native.iloc[0]["NativeImportanceNormalized"]
    )

    top5_native = native.head(5)["Feature"].tolist()

    sanity_rows = []

    def add_check(
        check,
        passed,
        observed,
        expected,
        note="",
    ):
        sanity_rows.append({
            "Check": check,
            "Status": "PASS" if passed else "REVIEW",
            "Observed": observed,
            "Expected": expected,
            "Note": note,
        })

    add_check(
        "Final test Accuracy",
        accuracy >= MIN_OVERALL_ACCURACY,
        f"{accuracy:.6f}",
        f">= {MIN_OVERALL_ACCURACY:.2f}",
    )

    add_check(
        "Final test Macro F1",
        macro_f1 >= MIN_MACRO_F1,
        f"{macro_f1:.6f}",
        f">= {MIN_MACRO_F1:.2f}",
    )

    for label in CLASS_ORDER:
        recall = class_recall.get(
            label,
            np.nan,
        )

        add_check(
            f"{label} Recall",
            bool(
                np.isfinite(recall)
                and recall >= MIN_CLASS_RECALL
            ),
            (
                f"{recall:.6f}"
                if np.isfinite(recall)
                else "missing"
            ),
            f">= {MIN_CLASS_RECALL:.2f}",
        )

    add_check(
        "No identifier leakage in final feature set",
        len(identifier_features) == 0,
        (
            "NONE"
            if not identifier_features
            else " | ".join(identifier_features)
        ),
        "NONE",
    )

    add_check(
        "No known injected noise in final feature set",
        len(noise_features) == 0,
        (
            "NONE"
            if not noise_features
            else " | ".join(noise_features)
        ),
        "NONE",
    )

    add_check(
        "Inference within normal-response requirement",
        avg_ms / 1000.0 < MAX_NORMAL_RESPONSE_SECONDS,
        f"{avg_ms:.6f} ms/claim",
        f"< {MAX_NORMAL_RESPONSE_SECONDS:.1f} sec/claim",
    )

    add_check(
        "No single feature dominates native importance",
        max_native_importance < 0.50,
        (
            f"{max_native_feature}="
            f"{max_native_importance:.6f}"
        ),
        "< 0.50",
        (
            "A single feature above 50% would warrant shortcut review; "
            "this is a reporting check only."
        ),
    )

    add_check(
        "Final prediction/Test ClaimID alignment",
        set(predictions["ClaimID"]) == set(test["ClaimID"]),
        f"{predictions['ClaimID'].nunique()} matched IDs",
        f"{test['ClaimID'].nunique()} matched IDs",
    )

    sanity = pd.DataFrame(
        sanity_rows
    )

    sanity.to_csv(
        SANITY_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    # --------------------------------------------------------
    # Final report
    # --------------------------------------------------------
    report_lines = [
        "ASSUREX CLAIM ENGINE - FINAL PYTHON MODEL REPORT",
        "=" * 64,
        "",
        "MODEL",
        f"Algorithm: Gradient Boosting",
        f"Frozen selected features: {len(selected_features)}",
        f"Serialized model size: {model_size_mb:.4f} MB",
        "",
        "FINAL TEST",
        f"Claims: {len(test)}",
        f"Accuracy: {accuracy:.6f}",
        f"Macro F1: {macro_f1:.6f}",
        f"Mean confidence: {predictions['Confidence'].mean():.6f}",
        f"Incorrect claims: {len(errors)}",
        f"Low confidence (<0.60): {(predictions['Confidence'] < 0.60).sum()}",
        "",
        "PER-CLASS RECALL",
    ]

    for label in CLASS_ORDER:
        report_lines.append(
            f"{label}: {class_recall.get(label, np.nan):.6f}"
        )

    report_lines.extend([
        "",
        "TOP 5 MODEL-NATIVE FEATURE IMPORTANCE",
    ])

    for _, row in native.head(5).iterrows():
        report_lines.append(
            f"{row['Feature']}: "
            f"{row['NativeImportanceNormalized']:.6f}"
        )

    report_lines.extend([
        "",
        "TOP 5 POST-HOC TEST PERMUTATION IMPORTANCE",
    ])

    for _, row in permutation.head(5).iterrows():
        report_lines.append(
            f"{row['Feature']}: "
            f"{row['PermutationImportanceMean']:.6f}"
        )

    report_lines.extend([
        "",
        "SANITY",
        f"Identifier features present: {identifier_features or 'NONE'}",
        f"Known noise features present: {noise_features or 'NONE'}",
        f"Highest native importance: {max_native_feature} "
        f"({max_native_importance:.6f})",
        f"All sanity PASS: "
        f"{bool((sanity['Status'] == 'PASS').all())}",
        "",
        "IMPORTANT",
        "Test-set permutation importance is POST-HOC reporting only.",
        "No model/feature/hyperparameter changes are allowed from this analysis.",
        "The final Python model remains assurex_final_model.joblib.",
    ])

    REPORT_PATH.write_text(
        "\n".join(report_lines),
        encoding="utf-8",
    )

    manifest = {
        "stage": "post-hoc final model reporting",
        "final_model": str(FINAL_MODEL_PATH),
        "feature_count": int(
            len(selected_features)
        ),
        "test_rows": int(
            len(test)
        ),
        "test_already_consumed_before_analysis": True,
        "native_importance": str(
            NATIVE_IMPORTANCE_PATH
        ),
        "permutation_importance": {
            "file": str(
                PERM_IMPORTANCE_PATH
            ),
            "dataset": "Final Test",
            "purpose": "post-hoc reporting only",
            "used_for_model_changes": False,
        },
        "error_analysis": str(
            ERROR_ANALYSIS_PATH
        ),
        "confidence_analysis": str(
            CONFIDENCE_PATH
        ),
        "sanity_check": str(
            SANITY_PATH
        ),
        "report": str(
            REPORT_PATH
        ),
        "rules": {
            "retraining": False,
            "feature_removal": False,
            "hyperparameter_tuning": False,
            "model_reselection": False,
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

    print(f"Frozen selected features      : {len(selected_features)}")
    print(f"Final Test claims             : {len(test)}")
    print(f"Final Accuracy                : {accuracy:.6f}")
    print(f"Final Macro F1                : {macro_f1:.6f}")
    print(f"Incorrect claims              : {len(errors)}")
    print(
        f"Known noise still selected    : "
        f"{len(noise_features)}"
    )
    print(
        f"Identifier leakage features   : "
        f"{len(identifier_features)}"
    )
    print(
        f"Top native feature            : "
        f"{max_native_feature} "
        f"({max_native_importance:.6f})"
    )
    print(
        f"All sanity checks PASS        : "
        f"{bool((sanity['Status'] == 'PASS').all())}"
    )

    print("\nTop 10 native feature importance:")
    for _, row in native.head(10).iterrows():
        print(
            f" - {row['Feature']:<32} "
            f"{row['NativeImportanceNormalized']:.6f}"
        )

    print("\nTop 10 permutation importance (POST-HOC):")
    for _, row in permutation.head(10).iterrows():
        print(
            f" - {row['Feature']:<32} "
            f"{row['PermutationImportanceMean']:.6f}"
        )

    print("\nCreated:")
    for path in [
        NATIVE_IMPORTANCE_PATH,
        PERM_IMPORTANCE_PATH,
        ERROR_ANALYSIS_PATH,
        CONFIDENCE_PATH,
        SANITY_PATH,
        REPORT_PATH,
        MANIFEST_PATH,
    ]:
        print(f" - {path}")

    print("\nIMPORTANT:")
    print(
        " - This was post-hoc reporting only."
    )
    print(
        " - No features/model/hyperparameters were changed."
    )
    print(
        " - Python pipeline is now complete."
    )


if __name__ == "__main__":
    main()
