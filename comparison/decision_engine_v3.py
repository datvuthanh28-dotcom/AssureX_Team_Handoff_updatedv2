from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

INPUT = ROOT / "comparison" / "assurex_v3_model_comparison_base.csv"
CONFIG = ROOT / "config" / "decision_thresholds.json"

OUT = ROOT / "comparison" / "assurex_v3_model_comparison_final.csv"
SUMMARY = ROOT / "comparison" / "assurex_v3_decision_engine_summary.csv"
MANIFEST = ROOT / "comparison" / "assurex_v3_decision_engine_manifest.json"

EXPECTED_ROWS = 225


def text_value(v) -> str:
    if pd.isna(v):
        return ""
    return str(v).strip()


def norm(v) -> str:
    return text_value(v).lower()


def is_yes(v) -> bool:
    return norm(v) == "yes"


def is_no(v) -> bool:
    return norm(v) == "no"


def is_unknown(v) -> bool:
    return norm(v) in {"", "unknown", "nan", "none"}


def number(v, default=0.0) -> float:
    try:
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default


def main():
    if not INPUT.exists():
        raise FileNotFoundError(INPUT)

    if not CONFIG.exists():
        raise FileNotFoundError(CONFIG)

    df = pd.read_csv(INPUT)

    with CONFIG.open("r", encoding="utf-8") as f:
        cfg = json.load(f)

    cmp_cfg = cfg["model_comparison"]
    evidence_cfg = cfg["evidence"]

    min_conf = float(cmp_cfg["minimum_confidence"])
    strong_min = float(cmp_cfg["strong_match_min_confidence"])
    strong_diff = float(cmp_cfg["strong_match_max_difference"])
    acceptable_min = float(cmp_cfg["acceptable_match_min_confidence"])
    acceptable_diff = float(cmp_cfg["acceptable_match_max_difference"])
    large_diff = float(cmp_cfg["large_confidence_difference"])
    min_ocr = float(evidence_cfg["minimum_ocr_confidence"])

    if len(df) != EXPECTED_ROWS:
        raise ValueError(
            f"Expected {EXPECTED_ROWS} claims, found {len(df)}"
        )

    if not df["ClaimID"].is_unique:
        raise ValueError("ClaimID must be unique.")

    results = []

    for _, row in df.iterrows():
        py_pred = text_value(row["PythonPredictedClass"])
        gtm_pred = text_value(row["GTMPredictedClass"])

        py_conf = number(row["PythonTopConfidence"])
        gtm_conf = number(row["GTMTopConfidence"])
        conf_diff = abs(py_conf - gtm_conf)

        prediction_match = py_pred == gtm_pred

        # ---------------------------------------------------------
        # 1. MODEL CONSISTENCY
        # Disagreement has priority so all different predictions
        # are explicitly identified as Model Disagreement.
        # ---------------------------------------------------------
        if not prediction_match:
            consistency = "Model Disagreement"

        elif py_conf < min_conf or gtm_conf < min_conf:
            consistency = "Uncertain Result"

        else:
            min_model_conf = min(py_conf, gtm_conf)

            if min_model_conf >= strong_min and conf_diff <= strong_diff:
                consistency = "Strong Match"

            elif (
                min_model_conf >= acceptable_min
                and conf_diff <= acceptable_diff
            ):
                consistency = "Acceptable Match"

            else:
                consistency = "Weak Match"

        # ---------------------------------------------------------
        # 2. WARRANTY HARD-FAIL RULES
        # ---------------------------------------------------------
        hard_fail = []

        if norm(row["WarrantyStatus"]) == "expired":
            hard_fail.append("Warranty expired")

        if is_no(row["ComponentWarrantyEligible"]):
            hard_fail.append("Component not warranty eligible")

        if is_no(row["FaultCovered"]):
            hard_fail.append("Fault not covered")

        if is_no(row["ClaimReportingWithinPeriod"]):
            hard_fail.append("Claim reported outside allowed period")

        if (
            is_yes(row["PreviousRepair"])
            and is_no(row["RepairAuthorized"])
        ):
            hard_fail.append("Previous repair was unauthorized")

        # ---------------------------------------------------------
        # 3. MANUAL REVIEW GATES
        # SRS requires disagreement, low confidence,
        # missing evidence and large confidence differences
        # to go to manual review.
        # ---------------------------------------------------------
        manual = []
        missing_docs = []

        if not prediction_match:
            manual.append("Python and GTM predictions disagree")

        if py_conf < min_conf:
            manual.append(
                f"Python confidence below threshold ({py_conf:.3f})"
            )

        if gtm_conf < min_conf:
            manual.append(
                f"GTM confidence below threshold ({gtm_conf:.3f})"
            )

        if conf_diff > large_diff:
            manual.append(
                f"Large model-confidence difference ({conf_diff:.3f})"
            )

        required_complete = norm(row["RequiredDocumentsComplete"])

        if required_complete in {"no", "unknown", ""}:
            manual.append("Required document status incomplete or unknown")
            missing_docs.append("Required documents incomplete/unknown")

        missing_count = number(row["MissingDocumentCount"])

        if missing_count > 0:
            manual.append(
                f"Missing required documents ({int(missing_count)})"
            )
            missing_docs.append(
                f"{int(missing_count)} required document(s) missing"
            )

        if is_yes(row["CriticalDocumentMissing"]):
            manual.append("Critical document missing")
            missing_docs.append("Critical document missing")

        # Important regression rule:
        # previous repair + repair report missing/unknown -> manual.
        if is_yes(row["PreviousRepair"]):
            repair_report = norm(row["RepairReportAvailable"])

            if repair_report not in {"yes", "not applicable"}:
                manual.append(
                    "Previous repair exists but repair report is missing/unknown"
                )
                missing_docs.append(
                    "Repair report missing/unknown"
                )

            repair_auth = norm(row["RepairAuthorized"])

            if repair_auth in {"unknown", ""}:
                manual.append(
                    "Previous repair authorization is unknown"
                )

        serial_match = norm(row["SerialNumberMatch"])

        if serial_match in {"no", "unknown", ""}:
            manual.append("Serial-number verification requires review")

        identity_match = norm(row["ProductIdentityMatch"])

        if identity_match in {"no", "unknown", ""}:
            manual.append("Product identity requires review")

        model_consistent = norm(row["ProductModelConsistent"])

        if model_consistent in {"no", "unknown", ""}:
            manual.append("Product model consistency requires review")

        if is_yes(row["DuplicateClaimIndicator"]):
            manual.append("Possible duplicate claim")

        if is_yes(row["DocumentDuplicateIndicator"]):
            manual.append("Possible duplicate document")

        if is_yes(row["ContradictionIndicator"]):
            manual.append("Contradictory claim evidence detected")

        ocr_conf = number(row["OCRConfidence"], default=1.0)

        if ocr_conf < min_ocr:
            manual.append(
                f"OCR confidence below threshold ({ocr_conf:.3f})"
            )

        # remove duplicate reasons while preserving order
        manual = list(dict.fromkeys(manual))
        missing_docs = list(dict.fromkeys(missing_docs))

        # ---------------------------------------------------------
        # 4. WARRANTY RULE RESULT
        # ---------------------------------------------------------
        if hard_fail:
            warranty_rule_result = (
                "HARD_FAIL: " + "; ".join(hard_fail)
            )
        elif manual:
            warranty_rule_result = (
                "MANUAL_REVIEW: " + "; ".join(manual)
            )
        else:
            warranty_rule_result = "PASS"

        # ---------------------------------------------------------
        # 5. FINAL APPLICATION DECISION
        #
        # Mandatory manual gates come first because SRS states
        # disagreement / low confidence / missing evidence /
        # large confidence differences must be reviewed manually.
        # ---------------------------------------------------------
        # Manual-review uncertainty always has highest priority.
        if manual:
            final_decision = "Manual Review Required"

        # A definitive hard-fail may produce Likely Invalid only
        # when no manual-review/uncertainty trigger exists.
        elif hard_fail:
            final_decision = "Likely Invalid"

        elif py_pred == "Manual Review" or gtm_pred == "Manual Review":
            final_decision = "Manual Review Required"

        elif py_pred == "Valid Claim" and gtm_pred == "Valid Claim":
            final_decision = "Likely Valid"

        elif py_pred == "Invalid Claim" and gtm_pred == "Invalid Claim":
            final_decision = "Likely Invalid"

        else:
            final_decision = "Manual Review Required"

        # ---------------------------------------------------------
        # 6. DISAGREEMENT / REVIEW EXPLANATION
        # ---------------------------------------------------------
        explanation = []

        if not prediction_match:
            explanation.append(
                f"Python={py_pred}; GTM={gtm_pred}"
            )

        if conf_diff > large_diff:
            explanation.append(
                f"Top-confidence difference={conf_diff:.3f}"
            )

        if hard_fail:
            explanation.append(
                "Warranty hard-fail: " + "; ".join(hard_fail)
            )

        if manual:
            explanation.append(
                "Manual-review trigger: " + "; ".join(manual)
            )

        if not explanation:
            explanation.append(
                "Models and warranty checks are sufficiently consistent"
            )

        results.append(
            {
                "ModelConsistencyStatus": consistency,
                "WarrantyRuleResult": warranty_rule_result,
                "MissingDocuments": (
                    "; ".join(missing_docs)
                    if missing_docs
                    else "None detected"
                ),
                "ContradictionsDetected": (
                    "YES"
                    if is_yes(row["ContradictionIndicator"])
                    else "NO"
                ),
                "DuplicateIndicators": "; ".join(
                    x for x in [
                        (
                            "Duplicate claim"
                            if is_yes(row["DuplicateClaimIndicator"])
                            else ""
                        ),
                        (
                            "Duplicate document"
                            if is_yes(row["DocumentDuplicateIndicator"])
                            else ""
                        ),
                    ]
                    if x
                ) or "None detected",
                "FinalApplicationDecision": final_decision,
                "DecisionExplanation": " | ".join(explanation),
                "ManualReviewTriggerCount": len(manual),
                "HardFailRuleCount": len(hard_fail),
            }
        )

    result_df = df.copy()

    result_df["PredictedClassMatch"] = (
        result_df["PythonPredictedClass"].astype(str)
        == result_df["GTMPredictedClass"].astype(str)
    ).map({True: "YES", False: "NO"})

    result_df["TopConfidenceDifference"] = (
        result_df["PythonTopConfidence"].astype(float)
        - result_df["GTMTopConfidence"].astype(float)
    ).abs()

    extra = pd.DataFrame(results)

    # Replace old base consistency result with V3 final logic
    result_df["ModelConsistencyStatus"] = extra[
        "ModelConsistencyStatus"
    ]

    for col in [
        "WarrantyRuleResult",
        "MissingDocuments",
        "ContradictionsDetected",
        "DuplicateIndicators",
        "FinalApplicationDecision",
        "DecisionExplanation",
        "ManualReviewTriggerCount",
        "HardFailRuleCount",
    ]:
        result_df[col] = extra[col]

    result_df = result_df.sort_values("ClaimID").reset_index(drop=True)

    result_df.to_csv(
        OUT,
        index=False,
        encoding="utf-8-sig",
    )

    summary_rows = [
        ("Claims", len(result_df)),
        (
            "Prediction matches",
            int((result_df["PredictedClassMatch"] == "YES").sum()),
        ),
        (
            "Prediction disagreements",
            int((result_df["PredictedClassMatch"] == "NO").sum()),
        ),
        (
            "Mean top-confidence difference",
            float(result_df["TopConfidenceDifference"].mean()),
        ),
    ]

    for status in [
        "Strong Match",
        "Acceptable Match",
        "Weak Match",
        "Model Disagreement",
        "Uncertain Result",
    ]:
        summary_rows.append(
            (
                status,
                int(
                    (
                        result_df["ModelConsistencyStatus"]
                        == status
                    ).sum()
                ),
            )
        )

    for decision in [
        "Likely Valid",
        "Likely Invalid",
        "Manual Review Required",
    ]:
        summary_rows.append(
            (
                decision,
                int(
                    (
                        result_df["FinalApplicationDecision"]
                        == decision
                    ).sum()
                ),
            )
        )

    summary = pd.DataFrame(
        summary_rows,
        columns=["Metric", "Value"],
    )

    summary.to_csv(
        SUMMARY,
        index=False,
        encoding="utf-8-sig",
    )

    manifest = {
        "version": "3.0.0",
        "input": str(INPUT.relative_to(ROOT)),
        "output": str(OUT.relative_to(ROOT)),
        "claims": int(len(result_df)),
        "test_set_modified": False,
        "python_model_retrained": False,
        "gtm_model_retrained": False,
        "decision_engine_is_trained_model": False,
        "threshold_config": str(CONFIG.relative_to(ROOT)),
        "final_decision_labels": [
            "Likely Valid",
            "Likely Invalid",
            "Manual Review Required",
        ],
    }

    with MANIFEST.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("=" * 76)
    print("ASSUREX V3 DECISION ENGINE")
    print("=" * 76)
    print(summary.to_string(index=False))
    print()
    print("Final comparison:", OUT)
    print("Summary         :", SUMMARY)
    print("Manifest        :", MANIFEST)


if __name__ == "__main__":
    main()
