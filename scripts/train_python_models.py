import argparse
import csv
import hashlib
import json
import re
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline


ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "submission_final" / "dataset"
SOURCE_MODEL = ROOT / "assurex_web" / "backend" / "app" / "ml" / "assurex_final_model.joblib"
CLASS_ORDER = ["Invalid Claim", "Manual Review", "Valid Claim"]
RANDOM_SEED = 20260925


def model_specs(seed):
    return [
        {
            "name": "Logistic Regression",
            "key": "logistic",
            "version": "python-logistic",
            "estimator": LogisticRegression(
                max_iter=3000,
                random_state=seed,
            ),
        },
        {
            "name": "Random Forest",
            "key": "random_forest",
            "version": "python-randomforest",
            "estimator": RandomForestClassifier(
                n_estimators=300,
                random_state=seed,
                n_jobs=-1,
            ),
        },
        {
            "name": "Gradient Boosting",
            "key": "gradient_boosting",
            "version": "python-gradientboosting",
            "estimator": GradientBoostingClassifier(
                learning_rate=0.05,
                n_estimators=150,
                random_state=seed,
            ),
        },
    ]


def read_split(name):
    path = DATASET_DIR / f"assurex_{name}.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Dataset split not found: {path}")
    return pd.read_csv(path, dtype={"ClaimID": "string"})


def validate_split_ids(splits):
    id_sets = {}
    for name, frame in splits.items():
        if "ClaimID" not in frame:
            raise ValueError(f"{name} split has no ClaimID column")
        if frame["ClaimID"].isna().any() or frame["ClaimID"].duplicated().any():
            raise ValueError(f"{name} split has blank or duplicate ClaimIDs")
        id_sets[name] = set(frame["ClaimID"])

    names = list(id_sets)
    for index, name in enumerate(names):
        for other in names[index + 1 :]:
            overlap = id_sets[name] & id_sets[other]
            if overlap:
                raise ValueError(
                    f"ClaimID leakage between {name} and {other}: "
                    f"{len(overlap)} overlapping IDs"
                )


def dataset_version():
    digest = hashlib.sha256()
    for name in ("train", "validation", "test"):
        path = DATASET_DIR / f"assurex_{name}.csv"
        digest.update(name.encode("utf-8"))
        digest.update(path.read_bytes())
    return f"assurex-locked-split-{digest.hexdigest()[:12]}"


def evaluate(model, frame, features, split_name):
    actual = frame["ClaimClass"].astype(str)
    predicted = model.predict(frame[features])
    probabilities = model.predict_proba(frame[features])
    classes = list(model.classes_)
    report = classification_report(
        actual,
        predicted,
        labels=CLASS_ORDER,
        output_dict=True,
        zero_division=0,
    )
    metrics = {
        "accuracy": report["accuracy"],
        "precision": report["weighted avg"]["precision"],
        "recall": report["weighted avg"]["recall"],
        "f1": report["weighted avg"]["f1-score"],
        "macro_precision": report["macro avg"]["precision"],
        "macro_recall": report["macro avg"]["recall"],
        "macro_f1": report["macro avg"]["f1-score"],
        "mean_top_confidence": float(np.max(probabilities, axis=1).mean()),
    }
    class_rows = [
        {
            "split": split_name,
            "class": label,
            "precision": report[label]["precision"],
            "recall": report[label]["recall"],
            "f1": report[label]["f1-score"],
            "support": int(report[label]["support"]),
        }
        for label in CLASS_ORDER
    ]
    confusion = confusion_matrix(actual, predicted, labels=CLASS_ORDER).tolist()
    prediction_rows = []
    for row_index, (_, row) in enumerate(frame.iterrows()):
        result = {
            "split": split_name,
            "ClaimID": row["ClaimID"],
            "ActualClass": actual.iloc[row_index],
            "PredictedClass": predicted[row_index],
            "TopConfidence": float(np.max(probabilities[row_index])),
        }
        result.update(
            {
                f"Confidence_{label}": float(probabilities[row_index, classes.index(label)])
                for label in CLASS_ORDER
            }
        )
        prediction_rows.append(result)

    return metrics, class_rows, confusion, prediction_rows


def write_csv(path, rows):
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Train and compare the three AssureX Python classifiers."
    )
    parser.add_argument("--version-suffix", default="v1")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.version_suffix):
        parser.error("--version-suffix may contain only letters, digits, _ and -")

    source_model = joblib.load(SOURCE_MODEL)
    if not isinstance(source_model, Pipeline) or "preprocessor" not in source_model.named_steps:
        raise TypeError("The existing runtime artifact has no reusable preprocessor step")
    features = list(source_model.feature_names_in_)
    if "ClaimID" in features or "ClaimClass" in features:
        raise ValueError("Identifiers and target must not be model features")

    train = read_split("train")
    validation = read_split("validation")
    validate_split_ids({"train": train, "validation": validation})
    for name, frame in (("train", train), ("validation", validation)):
        missing = sorted(set(features + ["ClaimClass"]) - set(frame.columns))
        if missing:
            raise ValueError(f"{name} split is missing required columns: {missing}")
        if set(frame["ClaimClass"].astype(str)) != set(CLASS_ORDER):
            raise ValueError(f"{name} split does not contain all three expected classes")

    specs = model_specs(args.seed)
    run_versions = {
        spec["key"]: f"{spec['version']}-{args.version_suffix}"
        for spec in specs
    }
    artifact_paths = {
        spec["key"]: ROOT
        / "model"
        / "python"
        / spec["key"]
        / f"{run_versions[spec['key']]}.joblib"
        for spec in specs
    }
    evaluation_dir = ROOT / "evaluation" / "python"
    versioned_outputs = [
        evaluation_dir / f"model_comparison_{args.version_suffix}.csv",
        evaluation_dir / f"model_class_metrics_{args.version_suffix}.csv",
        evaluation_dir / f"model_confusion_matrices_{args.version_suffix}.json",
        evaluation_dir / f"model_predictions_{args.version_suffix}.csv",
        evaluation_dir / f"selected_model_{args.version_suffix}.json",
    ]
    tracking_path = ROOT / "model_tracking" / "python_models.csv"
    if any(path.exists() for path in artifact_paths.values()) or any(
        path.exists() for path in versioned_outputs
    ):
        raise FileExistsError(
            "Versioned output already exists; choose a new --version-suffix "
            "to preserve existing artifacts."
        )

    trained = {}
    validation_results = {}
    class_rows = []
    confusion_results = {}
    prediction_rows = []
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=args.seed)

    for spec in specs:
        pipeline = Pipeline(
            [
                ("preprocessor", clone(source_model.named_steps["preprocessor"])),
                ("model", spec["estimator"]),
            ]
        )
        cv_scores = cross_val_score(
            pipeline,
            train[features],
            train["ClaimClass"].astype(str),
            cv=cv,
            scoring="f1_macro",
            n_jobs=1,
        )
        pipeline.fit(train[features], train["ClaimClass"].astype(str))
        metrics, classes, matrix, predictions = evaluate(
            pipeline, validation, features, "validation"
        )
        metrics["cv_mean_f1"] = float(cv_scores.mean())
        metrics["cv_std_f1"] = float(cv_scores.std(ddof=1))
        trained[spec["key"]] = pipeline
        validation_results[spec["key"]] = metrics
        class_rows.extend(
            {"model_version": run_versions[spec["key"]], **row}
            for row in classes
        )
        confusion_results[f"{run_versions[spec['key']]}_validation"] = {
            "labels": CLASS_ORDER,
            "matrix": matrix,
        }
        prediction_rows.extend(
            {
                "model_version": run_versions[spec["key"]],
                **row,
            }
            for row in predictions
        )

    selected_key = max(
        validation_results,
        key=lambda key: (
            validation_results[key]["macro_f1"],
            validation_results[key]["macro_recall"],
            validation_results[key]["macro_precision"],
            -validation_results[key]["cv_std_f1"],
        ),
    )

    test = read_split("test")
    validate_split_ids({"train": train, "validation": validation, "test": test})
    if set(test["ClaimClass"].astype(str)) != set(CLASS_ORDER):
        raise ValueError("test split does not contain all three expected classes")
    missing_test = sorted(set(features + ["ClaimClass"]) - set(test.columns))
    if missing_test:
        raise ValueError(f"test split is missing required columns: {missing_test}")

    test_results = {}
    for spec in specs:
        metrics, classes, matrix, predictions = evaluate(
            trained[spec["key"]], test, features, "test"
        )
        test_results[spec["key"]] = metrics
        class_rows.extend(
            {"model_version": run_versions[spec["key"]], **row}
            for row in classes
        )
        confusion_results[f"{run_versions[spec['key']]}_test"] = {
            "labels": CLASS_ORDER,
            "matrix": matrix,
        }
        prediction_rows.extend(
            {
                "model_version": run_versions[spec["key"]],
                **row,
            }
            for row in predictions
        )

    version = dataset_version()
    feature_version = "production-22-" + hashlib.sha256(
        "\n".join(features).encode("utf-8")
    ).hexdigest()[:8]
    tracking_rows = []
    comparison_rows = []
    for spec in specs:
        key = spec["key"]
        validation_metrics = validation_results[key]
        test_metrics = test_results[key]
        status = "SELECTED" if key == selected_key else "EVALUATED"
        reason = (
            "Selected by validation macro F1; ties use macro recall, "
            "macro precision, then lower 5-fold CV standard deviation."
            if key == selected_key
            else f"Not selected; validation macro F1 was {validation_metrics['macro_f1']:.6f}."
        )
        hyperparameters = spec["estimator"].get_params(deep=False)
        tracking_rows.append(
            {
                "model_name": spec["name"],
                "algorithm": type(spec["estimator"]).__name__,
                "version": run_versions[key],
                "training_date": date.today().isoformat(),
                "dataset_version": version,
                "feature_version": feature_version,
                "preprocessing_version": "runtime-column-transformer-v1",
                "random_seed": args.seed,
                "hyperparameters": json.dumps(hyperparameters, sort_keys=True),
                "validation_accuracy": validation_metrics["accuracy"],
                "validation_precision": validation_metrics["precision"],
                "validation_recall": validation_metrics["recall"],
                "validation_f1": validation_metrics["f1"],
                "validation_macro_precision": validation_metrics["macro_precision"],
                "validation_macro_recall": validation_metrics["macro_recall"],
                "validation_macro_f1": validation_metrics["macro_f1"],
                "cv_mean_f1": validation_metrics["cv_mean_f1"],
                "cv_std_f1": validation_metrics["cv_std_f1"],
                "test_accuracy": test_metrics["accuracy"],
                "test_precision": test_metrics["precision"],
                "test_recall": test_metrics["recall"],
                "test_f1": test_metrics["f1"],
                "test_macro_precision": test_metrics["macro_precision"],
                "test_macro_recall": test_metrics["macro_recall"],
                "test_macro_f1": test_metrics["macro_f1"],
                "validation_mean_top_confidence": validation_metrics["mean_top_confidence"],
                "test_mean_top_confidence": test_metrics["mean_top_confidence"],
                "status": status,
                "selection_reason": reason,
                "artifact_path": artifact_paths[key].relative_to(ROOT).as_posix(),
            }
        )
        comparison_rows.append(
            {
                "model_name": spec["name"],
                "version": run_versions[key],
                "selected_by_validation": key == selected_key,
                **{f"validation_{name}": value for name, value in validation_metrics.items()},
                **{f"test_{name}": value for name, value in test_metrics.items()},
            }
        )

    if tracking_path.exists():
        with tracking_path.open(encoding="utf-8", newline="") as stream:
            existing_rows = list(csv.DictReader(stream))
        existing_versions = {row.get("version") for row in existing_rows}
        collisions = existing_versions & {row["version"] for row in tracking_rows}
        if collisions:
            raise FileExistsError(f"Model versions already tracked: {sorted(collisions)}")
        tracking_rows = existing_rows + tracking_rows

    for key, pipeline in trained.items():
        artifact_path = artifact_paths[key]
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(pipeline, artifact_path, compress=3)

    write_csv(tracking_path, tracking_rows)
    write_csv(versioned_outputs[0], comparison_rows)
    write_csv(versioned_outputs[1], class_rows)
    write_csv(versioned_outputs[3], prediction_rows)
    versioned_outputs[2].parent.mkdir(parents=True, exist_ok=True)
    versioned_outputs[2].write_text(
        json.dumps(confusion_results, indent=2), encoding="utf-8"
    )
    selected_spec = next(spec for spec in specs if spec["key"] == selected_key)
    versioned_outputs[4].write_text(
        json.dumps(
            {
                "selected_model": selected_spec["name"],
                "selected_version": run_versions[selected_key],
                "selection_metric": "validation_macro_f1",
                "selection_reason": tracking_rows[-3 + [s["key"] for s in specs].index(selected_key)]["selection_reason"],
                "validation_metrics": validation_results[selected_key],
                "test_metrics": test_results[selected_key],
                "dataset_version": version,
                "random_seed": args.seed,
                "test_accessed_after_selection": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "selected_model": selected_spec["name"],
                "selected_version": run_versions[selected_key],
                "validation_macro_f1": validation_results[selected_key]["macro_f1"],
                "selected_test_metrics": test_results[selected_key],
                "dataset_version": version,
                "tracking_path": tracking_path.relative_to(ROOT).as_posix(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()