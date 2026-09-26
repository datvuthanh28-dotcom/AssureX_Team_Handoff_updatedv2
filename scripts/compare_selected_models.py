import argparse
import csv
import html
import json
import re
from pathlib import Path

import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix


ROOT = Path(__file__).resolve().parents[1]
CLASS_ORDER = ["Invalid Claim", "Manual Review", "Valid Claim"]


def load_csv(path):
    if not path.is_file():
        raise FileNotFoundError(f"Prediction file not found: {path}")
    return pd.read_csv(path, dtype={"ClaimID": "string"})


def find_column(frame, candidates, required=True):
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
    if required:
        raise ValueError(f"Missing prediction column; expected one of {candidates}")
    return None


def normalize_prediction_file(frame, *, model_kind, model_version):
    if "split" in frame.columns:
        frame = frame.loc[frame["split"].eq("test")].copy()
    if "model_version" in frame.columns:
        frame = frame.loc[frame["model_version"].eq(model_version)].copy()
    if frame.empty:
        raise ValueError(f"No test predictions found for {model_version}")
    id_column = find_column(frame, ["ClaimID", "claim_id"])
    actual_column = find_column(frame, ["ActualClass", "Actual", "actual_class"])
    predicted_column = find_column(frame, ["PredictedClass", "Predicted", "prediction"])
    if model_kind == "python":
        confidence_columns = {
            "Invalid Claim": find_column(frame, ["Confidence_Invalid Claim", "Confidence_Invalid_Claim", "ConfidenceInvalid"]),
            "Manual Review": find_column(frame, ["Confidence_Manual Review", "Confidence_Manual_Review", "ConfidenceManual"]),
            "Valid Claim": find_column(frame, ["Confidence_Valid Claim", "Confidence_Valid_Claim", "ConfidenceValid"]),
        }
    else:
        confidence_columns = {
            "Invalid Claim": find_column(frame, ["ConfidenceInvalid", "GoogleConfidenceInvalid"]),
            "Manual Review": find_column(frame, ["ConfidenceManual", "GoogleConfidenceManual"]),
            "Valid Claim": find_column(frame, ["ConfidenceValid", "GoogleConfidenceValid"]),
        }
    output = pd.DataFrame(
        {
            "ClaimID": frame[id_column].astype("string"),
            "ActualClass": frame[actual_column].astype(str),
            "PredictedClass": frame[predicted_column].astype(str),
            "ConfidenceInvalid": pd.to_numeric(frame[confidence_columns["Invalid Claim"]]),
            "ConfidenceManual": pd.to_numeric(frame[confidence_columns["Manual Review"]]),
            "ConfidenceValid": pd.to_numeric(frame[confidence_columns["Valid Claim"]]),
        }
    )
    if output["ClaimID"].isna().any() or output["ClaimID"].duplicated().any():
        raise ValueError(f"{model_kind} prediction file has blank or duplicate ClaimIDs")
    if not set(output["ActualClass"]).issubset(CLASS_ORDER):
        raise ValueError(f"{model_kind} predictions contain unknown actual classes")
    if not set(output["PredictedClass"]).issubset(CLASS_ORDER):
        raise ValueError(f"{model_kind} predictions contain unknown predicted classes")
    output["TopConfidence"] = output[
        ["ConfidenceInvalid", "ConfidenceManual", "ConfidenceValid"]
    ].max(axis=1)
    return output


def metric_summary(actual, predicted):
    report = classification_report(
        actual,
        predicted,
        labels=CLASS_ORDER,
        output_dict=True,
        zero_division=0,
    )
    return {
        "accuracy": report["accuracy"],
        "precision": report["weighted avg"]["precision"],
        "recall": report["weighted avg"]["recall"],
        "f1": report["weighted avg"]["f1-score"],
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
        "confusion_matrix": confusion_matrix(
            actual,
            predicted,
            labels=CLASS_ORDER,
        ).tolist(),
    }


def validate_thresholds(config):
    if config.get("status") != "calibrated":
        raise ValueError(
            "Model consistency thresholds are not calibrated from common validation predictions; "
            "refusing to create a final comparison or decision report."
        )
    names = [
        "minimum_confidence",
        "strong_match_max_difference",
        "acceptable_match_max_difference",
        "weak_match_max_difference",
    ]
    values = [config.get(name) for name in names]
    if any(not isinstance(value, (int, float)) for value in values):
        raise ValueError("All calibrated consistency thresholds must be numeric")
    if not (0 <= values[0] <= 1 and 0 <= values[1] <= values[2] <= values[3] <= 1):
        raise ValueError("Consistency thresholds must satisfy 0 <= min confidence <= 1 and 0 <= strong <= acceptable <= weak <= 1")
    return config


def consistency_status(prediction_match, confidence_difference, confidence_min, thresholds):
    if not prediction_match:
        return "Model Disagreement"
    if confidence_min < thresholds["minimum_confidence"]:
        return "Uncertain Result"
    if confidence_difference <= thresholds["strong_match_max_difference"]:
        return "Strong Match"
    if confidence_difference <= thresholds["acceptable_match_max_difference"]:
        return "Acceptable Match"
    if confidence_difference <= thresholds["weak_match_max_difference"]:
        return "Weak Match"
    return "Uncertain Result"


def missing_documents(row):
    evidence = {
        "receipt_available": "Receipt",
        "warranty_card_available": "Warranty card",
        "product_image_available": "Product image",
        "serial_evidence_available": "Serial evidence",
        "fault_evidence_available": "Fault evidence",
    }
    missing = [label for field, label in evidence.items() if str(row.get(field, "")).strip().lower() != "yes"]
    if str(row.get("previous_repair", "")).strip().lower() == "yes" and str(row.get("repair_report_available", "")).strip().lower() != "yes":
        missing.append("Repair report")
    return missing


def apply_final_decision(row, consistency):
    hard_invalid = []
    manual_review = []
    warranty_status = str(row.get("WarrantyStatus", "")).strip().lower()
    if warranty_status == "expired":
        hard_invalid.append("Warranty expired")
    if str(row.get("FaultCovered", "")).strip().lower() == "no":
        hard_invalid.append("Fault not covered")
    if str(row.get("DuplicateClaimIndicator", "")).strip().lower() == "yes":
        hard_invalid.append("Duplicate claim")
    if str(row.get("SerialNumberMatch", "")).strip().lower() == "no":
        hard_invalid.append("Serial number mismatch")
    if str(row.get("RepairAuthorized", "")).strip().lower() == "no":
        hard_invalid.append("Unauthorized repair")

    missing = missing_documents(row)
    if str(row.get("RequiredDocumentsComplete", "")).strip().lower() != "yes" or missing:
        manual_review.append("Missing required documents")
    if str(row.get("ContradictionIndicator", "")).strip().lower() == "yes":
        manual_review.append("Claim contradiction")
    if str(row.get("ProductModelConsistent", "")).strip().lower() == "no":
        manual_review.append("Product/model inconsistency")
    if str(row.get("WarrantyStatus", "")).strip().lower() == "unknown":
        manual_review.append("Warranty status unknown")
    if consistency in {"Model Disagreement", "Uncertain Result"}:
        manual_review.append(consistency)

    if hard_invalid:
        return "Invalid Claim", hard_invalid + manual_review, missing
    if manual_review:
        return "Manual Review", manual_review, missing
    return row["PythonPredictedClass"], [], missing


def main():
    parser = argparse.ArgumentParser(
        description="Compare selected Python and Google predictions on the same unseen test ClaimIDs."
    )
    parser.add_argument("--python-predictions", type=Path, required=True)
    parser.add_argument("--google-predictions", type=Path, required=True)
    parser.add_argument("--version-suffix", default="v1")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", args.version_suffix):
        parser.error("--version-suffix may contain only letters, digits, _ and -")

    registry_path = ROOT / "model_tracking" / "active_models.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    python_model = registry["python_model"]
    google_model = registry["google_model"]
    config = validate_thresholds(
        json.loads((ROOT / "config" / "model_consistency.json").read_text(encoding="utf-8"))
    )
    python_predictions = normalize_prediction_file(
        load_csv(args.python_predictions),
        model_kind="python",
        model_version=python_model["version"],
    )
    google_predictions = normalize_prediction_file(
        load_csv(args.google_predictions),
        model_kind="google",
        model_version=google_model["version"],
    )
    if len(python_predictions) < 30 or len(google_predictions) < 30:
        raise ValueError("At least 30 unseen test predictions from each model are required")
    if set(python_predictions["ClaimID"]) != set(google_predictions["ClaimID"]):
        raise ValueError("Python and Google prediction files must contain the same test ClaimIDs")

    python_predictions = python_predictions.set_index("ClaimID")
    google_predictions = google_predictions.set_index("ClaimID")
    joined = python_predictions.join(
        google_predictions,
        lsuffix="_python",
        rsuffix="_google",
    )
    if not joined["ActualClass_python"].equals(joined["ActualClass_google"]):
        raise ValueError("ActualClass differs between Python and Google predictions")

    test_data = load_csv(ROOT / "submission_final" / "dataset" / "assurex_test.csv").set_index("ClaimID")
    if set(joined.index) - set(test_data.index):
        raise ValueError("Prediction IDs are not present in the locked test dataset")
    joined = joined.join(test_data, rsuffix="_dataset")
    comparison_rows = []
    for claim_id, row in joined.iterrows():
        python_prediction = row["PredictedClass_python"]
        google_prediction = row["PredictedClass_google"]
        python_confidence = float(row["TopConfidence_python"])
        google_confidence = float(row["TopConfidence_google"])
        difference = abs(python_confidence - google_confidence)
        match = python_prediction == google_prediction
        consistency = consistency_status(
            match,
            difference,
            min(python_confidence, google_confidence),
            config,
        )
        enriched = row.to_dict()
        enriched["PythonPredictedClass"] = python_prediction
        enriched["GooglePredictedClass"] = google_prediction
        final_decision, reasons, missing = apply_final_decision(enriched, consistency)
        comparison_rows.append(
            {
                "ClaimID": claim_id,
                "ActualClass": row["ActualClass_python"],
                "PythonModel": python_model["name"],
                "PythonVersion": python_model["version"],
                "PythonPrediction": python_prediction,
                "PythonConfidenceValid": row["Confidence_Valid Claim"],
                "PythonConfidenceInvalid": row["Confidence_Invalid Claim"],
                "PythonConfidenceManual": row["Confidence_Manual Review"],
                "GoogleModel": google_model["name"],
                "GoogleVersion": google_model["version"],
                "GoogleCardFilename": f"{claim_id}.png",
                "GooglePrediction": google_prediction,
                "GoogleConfidenceValid": row["ConfidenceValid"],
                "GoogleConfidenceInvalid": row["ConfidenceInvalid"],
                "GoogleConfidenceManual": row["ConfidenceManual"],
                "PredictionMatch": match,
                "PythonTopConfidence": python_confidence,
                "GoogleTopConfidence": google_confidence,
                "ConfidenceDifference": difference,
                "ModelConsistencyStatus": consistency,
                "WarrantyRuleResult": "; ".join(
                    hard_reason
                    for hard_reason in reasons
                    if hard_reason in {
                        "Warranty expired",
                        "Fault not covered",
                        "Duplicate claim",
                        "Serial number mismatch",
                        "Unauthorized repair",
                    }
                ) or "No hard-invalid warranty rule",
                "MissingDocuments": "; ".join(missing),
                "Contradictions": str(row.get("ContradictionIndicator", "Unknown")),
                "DuplicateIndicator": str(row.get("DuplicateClaimIndicator", "Unknown")),
                "FinalDecision": final_decision,
                "DecisionReasons": "; ".join(reasons),
            }
        )

    frame = pd.DataFrame(comparison_rows)
    actual = frame["ActualClass"]
    python_metrics = metric_summary(actual, frame["PythonPrediction"])
    google_metrics = metric_summary(actual, frame["GooglePrediction"])
    consistency_counts = frame["ModelConsistencyStatus"].value_counts().to_dict()
    summary = {
        "python_model": {"name": python_model["name"], "version": python_model["version"], **python_metrics},
        "google_model": {"name": google_model["name"], "version": google_model["version"], **google_metrics},
        "test_claims": len(frame),
        "model_agreement_rate": float(frame["PredictionMatch"].mean()),
        "model_disagreement_rate": float((~frame["PredictionMatch"]).mean()),
        "average_confidence_difference": float(frame["ConfidenceDifference"].mean()),
        "consistency_status_counts": {
            status: int(consistency_counts.get(status, 0))
            for status in ["Strong Match", "Acceptable Match", "Weak Match", "Model Disagreement", "Uncertain Result"]
        },
        "manual_review_count": int(frame["FinalDecision"].eq("Manual Review").sum()),
        "final_decision_counts": frame["FinalDecision"].value_counts().to_dict(),
        "selection_policy": "Models must be selected on validation metrics only; this report is final test evaluation.",
    }

    output_dir = ROOT / "model_tracking"
    comparison_path = output_dir / f"model_comparison_{args.version_suffix}.csv"
    summary_path = ROOT / "evaluation" / "comparison" / f"model_comparison_summary_{args.version_suffix}.json"
    html_path = ROOT / "evaluation" / "comparison" / f"model_comparison_report_{args.version_suffix}.html"
    for path in (comparison_path, summary_path, html_path):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite existing report: {path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(comparison_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    html_path.write_text(
        "<!doctype html><html><head><meta charset='utf-8'><title>AssureX Model Comparison</title></head><body>"
        "<h1>AssureX Python vs Google Model Comparison</h1>"
        "<p>On this common unseen test dataset, the selected models were evaluated independently. "
        "This comparison does not claim one technology is universally better.</p>"
        f"<pre>{html.escape(json.dumps(summary, indent=2))}</pre>"
        f"<p>Per-claim report: {html.escape(comparison_path.relative_to(ROOT).as_posix())}</p>"
        "</body></html>",
        encoding="utf-8",
    )
    print(json.dumps({"comparison_csv": comparison_path.relative_to(ROOT).as_posix(), "summary": summary_path.relative_to(ROOT).as_posix(), "html": html_path.relative_to(ROOT).as_posix(), "metrics": summary}, indent=2))


if __name__ == "__main__":
    main()
