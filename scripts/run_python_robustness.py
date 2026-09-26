import argparse
import hashlib
import json
import re
from pathlib import Path

import joblib
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline


ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "submission_final" / "dataset"
MODEL_PATH = ROOT / "model" / "python" / "gradient_boosting" / "python-gradientboosting-v1.joblib"
SEED = 20260925
ROBUST_FEATURES = [
    "WarrantyCardAvailable",
    "RepairReportAvailable",
    "PreviousRepair",
    "RepairCount",
    "PriorClaimCount",
    "ClaimAmount",
    "OCRConfidence",
    "ClaimSubmissionChannel",
]
RULE_DERIVED_FEATURES = [
    "SerialNumberMatch",
    "ProductModelConsistent",
    "DuplicateClaimIndicator",
    "ContradictionIndicator",
    "ClaimReportingDelayDays",
    "WarrantyRemainingDays",
    "WarrantyStatus",
    "ClaimReportingWithinPeriod",
    "FaultCovered",
    "MissingDocumentCount",
    "AvailableDocumentCount",
    "RequiredDocumentsComplete",
    "PurchaseProofAvailable",
    "HasRepairHistory",
]
CLASS_ORDER = ["Invalid Claim", "Manual Review", "Valid Claim"]


def read_split(name):
    return pd.read_csv(
        DATASET_DIR / f"assurex_{name}.csv",
        dtype={"ClaimID": "string"},
    )


def macro_metrics(actual, predicted):
    report = classification_report(
        actual,
        predicted,
        labels=CLASS_ORDER,
        output_dict=True,
        zero_division=0,
    )
    return {
        "accuracy": report["accuracy"],
        "macro_precision": report["macro avg"]["precision"],
        "macro_recall": report["macro avg"]["recall"],
        "macro_f1": report["macro avg"]["f1-score"],
        "class_metrics": {
            label: {
                "precision": report[label]["precision"],
                "recall": report[label]["recall"],
                "f1": report[label]["f1-score"],
                "support": int(report[label]["support"]),
            }
            for label in CLASS_ORDER
        },
    }


def dataset_fingerprint():
    digest = hashlib.sha256()
    for split in ("train", "validation"):
        digest.update(split.encode("utf-8"))
        digest.update((DATASET_DIR / f"assurex_{split}.csv").read_bytes())
    return f"train-validation-{digest.hexdigest()[:12]}"


def pure_rule_bins(train):
    results = {}
    for feature in RULE_DERIVED_FEATURES:
        table = pd.crosstab(
            train[feature].fillna("<NA>").astype(str),
            train["ClaimClass"],
        )
        pure_values = []
        for value, counts in table.iterrows():
            support = int(counts.sum())
            if support >= 10 and int(counts.max()) == support:
                pure_values.append(
                    {
                        "value": str(value),
                        "class": str(counts.idxmax()),
                        "support": support,
                    }
                )
        if pure_values:
            results[feature] = pure_values
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Compare the selected full-feature model with a rule-feature-excluded robustness model."
    )
    parser.add_argument("--version-suffix", default="v1")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.version_suffix):
        parser.error("--version-suffix may contain only letters, digits, _ and -")

    output_path = ROOT / "evaluation" / "python" / f"robustness_{args.version_suffix}.json"
    if output_path.exists():
        raise FileExistsError(f"Versioned robustness report already exists: {output_path}")

    train = read_split("train")
    validation = read_split("validation")
    for name, frame in (("train", train), ("validation", validation)):
        if frame["ClaimID"].isna().any() or frame["ClaimID"].duplicated().any():
            raise ValueError(f"{name} split has blank or duplicate ClaimIDs")
        if set(frame["ClaimClass"].astype(str)) != set(CLASS_ORDER):
            raise ValueError(f"{name} split does not contain all expected classes")
    if set(train["ClaimID"]) & set(validation["ClaimID"]):
        raise ValueError("ClaimID overlap found between train and validation")

    missing = sorted(
        set(ROBUST_FEATURES + RULE_DERIVED_FEATURES + ["ClaimClass", "ClaimID"])
        - set(train.columns)
    )
    if missing:
        raise ValueError(f"Dataset is missing audited columns: {missing}")

    full_model = joblib.load(MODEL_PATH)
    full_features = list(full_model.feature_names_in_)
    full_train = Pipeline(
        [
            ("preprocessor", clone(full_model.named_steps["preprocessor"])),
            (
                "model",
                GradientBoostingClassifier(
                    learning_rate=0.05,
                    n_estimators=150,
                    random_state=SEED,
                ),
            ),
        ]
    )
    robust_preprocessor = clone(full_model.named_steps["preprocessor"])
    robust_preprocessor.transformers = [
        (
            name,
            transformer,
            [column for column in columns if column in ROBUST_FEATURES],
        )
        for name, transformer, columns in robust_preprocessor.transformers
    ]
    robust_model = Pipeline(
        [
            ("preprocessor", robust_preprocessor),
            (
                "model",
                GradientBoostingClassifier(
                    learning_rate=0.05,
                    n_estimators=150,
                    random_state=SEED,
                ),
            ),
        ]
    )

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    y_train = train["ClaimClass"].astype(str)
    y_validation = validation["ClaimClass"].astype(str)
    full_cv = cross_val_score(
        full_train,
        train[full_features],
        y_train,
        cv=cv,
        scoring="f1_macro",
        n_jobs=1,
    )
    robust_cv = cross_val_score(
        robust_model,
        train[ROBUST_FEATURES],
        y_train,
        cv=cv,
        scoring="f1_macro",
        n_jobs=1,
    )
    full_train.fit(train[full_features], y_train)
    robust_model.fit(train[ROBUST_FEATURES], y_train)
    full_metrics = macro_metrics(
        y_validation,
        full_train.predict(validation[full_features]),
    )
    robust_metrics = macro_metrics(
        y_validation,
        robust_model.predict(validation[ROBUST_FEATURES]),
    )
    full_metrics["cv_macro_f1_mean"] = float(full_cv.mean())
    full_metrics["cv_macro_f1_std"] = float(full_cv.std(ddof=1))
    robust_metrics["cv_macro_f1_mean"] = float(robust_cv.mean())
    robust_metrics["cv_macro_f1_std"] = float(robust_cv.std(ddof=1))

    report = {
        "dataset_version": dataset_fingerprint(),
        "training_seed": SEED,
        "evaluation_split": "validation",
        "test_set_used": False,
        "identifier_columns": ["ClaimID"],
        "identifier_columns_excluded_from_features": True,
        "full_feature_model": {
            "version": "python-gradientboosting-v1",
            "feature_count": len(full_features),
            "metrics": full_metrics,
        },
        "robustness_model": {
            "algorithm": "GradientBoostingClassifier",
            "feature_count": len(ROBUST_FEATURES),
            "features": ROBUST_FEATURES,
            "excluded_rule_derived_features": RULE_DERIVED_FEATURES,
            "hyperparameters": {
                "learning_rate": 0.05,
                "n_estimators": 150,
                "random_state": SEED,
            },
            "metrics": robust_metrics,
        },
        "validation_macro_f1_difference_robust_minus_full": (
            robust_metrics["macro_f1"] - full_metrics["macro_f1"]
        ),
        "training_rule_feature_bins_with_10plus_records_and_single_class": pure_rule_bins(train),
        "interpretation": (
            "The full model includes outputs derived by warranty/document rules. "
            "Pure-class bins and the robustness performance gap indicate that "
            "the full-feature score partly reflects those encoded rules; it "
            "must not be interpreted as independent evidence of generalization."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "report": output_path.relative_to(ROOT).as_posix(),
                "full_validation_macro_f1": full_metrics["macro_f1"],
                "robust_validation_macro_f1": robust_metrics["macro_f1"],
                "validation_macro_f1_difference": report[
                    "validation_macro_f1_difference_robust_minus_full"
                ],
                "test_set_used": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()