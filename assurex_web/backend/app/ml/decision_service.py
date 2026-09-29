from __future__ import annotations
import json
from pathlib import Path
WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
THRESHOLD_PATH = WORKSPACE_ROOT / "config" / "decision_thresholds.json"
DEFAULT_THRESHOLDS = {
    "model_comparison": {
        "minimum_confidence": 0.60,
        "strong_match_min_confidence": 0.85,
        "strong_match_max_difference": 0.10,
        "acceptable_match_min_confidence": 0.70,
        "acceptable_match_max_difference": 0.20,
        "large_confidence_difference": 0.25,
    },
    "evidence": {"minimum_ocr_confidence": 0.70},
}


def _load_thresholds():
    if THRESHOLD_PATH.is_file():
        return json.loads(
            THRESHOLD_PATH.read_text(encoding="utf-8")
        )
    return DEFAULT_THRESHOLDS


def _norm(value):
    if value is None:
        return ""
    return str(value).strip().lower()


def _is_yes(value):
    return _norm(value) in {"yes", "true", "1"}


def _is_no(value):
    return _norm(value) in {"no", "false", "0"}


def _number(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _legacy_label(final_application_decision):
    return {
        "Likely Valid": "Valid Claim",
        "Likely Invalid": "Invalid Claim",
        "Manual Review Required": "Manual Review",
    }.get(final_application_decision, "Manual Review")


def apply_business_rules(
    claim_data,
    ml_prediction,
    ml_confidence,
    gtm_prediction=None,
    gtm_confidence=None,
    python_probabilities=None,
    gtm_probabilities=None,
):
    cfg = _load_thresholds()
    cmp_cfg = cfg["model_comparison"]
    evidence_cfg = cfg["evidence"]
    min_conf = float(cmp_cfg["minimum_confidence"])
    strong_min = float(cmp_cfg["strong_match_min_confidence"])
    strong_diff = float(cmp_cfg["strong_match_max_difference"])
    acceptable_min = float(cmp_cfg["acceptable_match_min_confidence"])
    acceptable_diff = float(cmp_cfg["acceptable_match_max_difference"])
    large_diff = float(cmp_cfg["large_confidence_difference"])
    min_ocr = float(evidence_cfg["minimum_ocr_confidence"])
    py_pred = str(ml_prediction or "").strip()
    py_conf = _number(ml_confidence)
    gtm_available = (
        gtm_prediction is not None
        and gtm_confidence is not None
    )
    if gtm_available:
        gt_pred = str(gtm_prediction).strip()
        gt_conf = _number(gtm_confidence)
        prediction_match = py_pred == gt_pred
        confidence_difference = abs(py_conf - gt_conf)
        if not prediction_match:
            consistency = "Model Disagreement"
        elif py_conf < min_conf or gt_conf < min_conf:
            consistency = "Uncertain Result"
        else:
            min_model_conf = min(py_conf, gt_conf)
            if (
                min_model_conf >= strong_min
                and confidence_difference <= strong_diff
            ):
                consistency = "Strong Match"
            elif (
                min_model_conf >= acceptable_min
                and confidence_difference <= acceptable_diff
            ):
                consistency = "Acceptable Match"
            else:
                consistency = "Weak Match"
    else:
        gt_pred = None
        gt_conf = None
        prediction_match = False
        confidence_difference = None
        consistency = "Uncertain Result"
    hard_fail = []
    manual = []
    warnings = []
    missing_docs = []
    if not gtm_available:
        manual.append("GTM G2 V3 inference unavailable")
    else:
        if not prediction_match:
            manual.append("Python and GTM predictions disagree")
        if gt_conf < min_conf:
            manual.append(
                f"GTM confidence below threshold ({gt_conf:.3f})"
            )
        if (
            confidence_difference is not None
            and confidence_difference > large_diff
        ):
            manual.append(
                f"Large model-confidence difference ({confidence_difference:.3f})"
            )
    if py_conf < min_conf:
        manual.append(
            f"Python confidence below threshold ({py_conf:.3f})"
        )
    if _norm(claim_data.get("WarrantyStatus")) == "expired":
        hard_fail.append("Warranty expired")
    if _is_no(claim_data.get("ComponentWarrantyEligible")):
        hard_fail.append("Component not warranty eligible")
    if _is_no(claim_data.get("FaultCovered")):
        hard_fail.append("Fault not covered")
    if _is_no(claim_data.get("ClaimReportingWithinPeriod")):
        hard_fail.append("Claim reported outside allowed period")
    previous_repair = _is_yes(claim_data.get("PreviousRepair"))
    repair_authorized = _norm(claim_data.get("RepairAuthorized"))
    if previous_repair and repair_authorized == "no":
        hard_fail.append("Previous repair was unauthorized")
    required_complete = _norm(
        claim_data.get("RequiredDocumentsComplete")
    )
    if required_complete in {"no", "unknown", ""}:
        manual.append(
            "Required document status incomplete or unknown"
        )
        missing_docs.append(
            "Required documents incomplete/unknown"
        )
    policy_required_complete = _norm(
        claim_data.get("PolicyRequiredEvidenceComplete")
    )
    policy_missing_evidence = claim_data.get("PolicyMissingEvidence") or []
    if policy_required_complete in {"no", "unknown", ""}:
        missing_label = ", ".join(str(item) for item in policy_missing_evidence)
        manual.append(
            "Category policy evidence missing"
            + (f": {missing_label}" if missing_label else "")
        )
        missing_docs.append(
            "Category policy evidence missing"
            + (f": {missing_label}" if missing_label else "")
        )
    if _is_no(claim_data.get("ComponentWarrantyEligible")):
        hard_fail.append("Component is not covered by the category policy")
    if _is_yes(claim_data.get("PolicyInstallationRequired")) and _norm(
        claim_data.get("InstallationEvidenceAvailable")
    ) != "yes":
        manual.append("Category policy requires installation evidence")
        missing_docs.append("Installation evidence required by category policy")
    missing_count = _number(
        claim_data.get("MissingDocumentCount")
    )
    if missing_count > 0:
        manual.append(
            f"Missing required documents ({int(missing_count)})"
        )
        missing_docs.append(
            f"{int(missing_count)} required document(s) missing"
        )
    if _is_yes(claim_data.get("CriticalDocumentMissing")):
        manual.append("Critical document missing")
        missing_docs.append("Critical document missing")
    if previous_repair:
        repair_report = _norm(
            claim_data.get("RepairReportAvailable")
        )
        if repair_report not in {"yes", "not applicable"}:
            manual.append(
                "Previous repair exists but repair report is missing/unknown"
            )
            missing_docs.append(
                "Repair report missing/unknown"
            )
        if repair_authorized in {"unknown", ""}:
            manual.append(
                "Previous repair authorization is unknown"
            )
    if _norm(claim_data.get("SerialNumberMatch")) in {
        "no", "unknown", ""
    }:
        manual.append(
            "Serial-number verification requires review"
        )
    if _norm(claim_data.get("ProductIdentityMatch")) in {
        "no", "unknown", ""
    }:
        manual.append(
            "Product identity requires review"
        )
    if _norm(claim_data.get("ProductModelConsistent")) in {
        "no", "unknown", ""
    }:
        manual.append(
            "Product model consistency requires review"
        )
    if _is_yes(claim_data.get("DuplicateClaimIndicator")):
        manual.append("Possible duplicate claim")
    if _is_yes(claim_data.get("DocumentDuplicateIndicator")):
        manual.append("Possible duplicate document")
        warnings.append("Duplicate document warning")
    if _is_yes(claim_data.get("ContradictionIndicator")):
        manual.append(
            "Contradictory claim evidence detected"
        )
    if _is_yes(
        claim_data.get("WarrantyDocumentMismatchIndicator")
    ):
        manual.append(
            "Warranty document mismatch requires review"
        )
    ocr_conf = _number(
        claim_data.get("OCRConfidence"),
        default=1.0,
    )
    if ocr_conf < min_ocr:
        manual.append(
            f"OCR confidence below threshold ({ocr_conf:.3f})"
        )
    hard_fail = list(dict.fromkeys(hard_fail))
    manual = list(dict.fromkeys(manual))
    warnings = list(dict.fromkeys(warnings))
    missing_docs = list(dict.fromkeys(missing_docs))
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
    if manual:
        final_application_decision = "Manual Review Required"
    elif hard_fail:
        final_application_decision = "Likely Invalid"
    elif not gtm_available:
        final_application_decision = "Manual Review Required"
    elif py_pred == "Manual Review" or gt_pred == "Manual Review":
        final_application_decision = "Manual Review Required"
    elif py_pred == "Valid Claim" and gt_pred == "Valid Claim":
        final_application_decision = "Likely Valid"
    elif py_pred == "Invalid Claim" and gt_pred == "Invalid Claim":
        final_application_decision = "Likely Invalid"
    else:
        final_application_decision = "Manual Review Required"
    reasons = []
    if gtm_available and not prediction_match:
        reasons.append(f"Python={py_pred}; GTM={gt_pred}")
    if (
        confidence_difference is not None
        and confidence_difference > large_diff
    ):
        reasons.append(
            f"Top-confidence difference={confidence_difference:.3f}"
        )
    if hard_fail:
        reasons.append(
            "Warranty hard-fail: " + "; ".join(hard_fail)
        )
    if manual:
        reasons.append(
            "Manual-review trigger: " + "; ".join(manual)
        )
    reasons.extend(warnings)
    if not reasons:
        reasons.append(
            "Models and warranty checks are sufficiently consistent"
        )
    legacy_final_decision = _legacy_label(
        final_application_decision
    )
    customer_status = {
        "Likely Valid": "Waiting to proceed",
        "Likely Invalid": "Under Review",
        "Manual Review Required": "Under Review",
    }[final_application_decision]
    return {
        "ml_prediction": py_pred,
        "ml_confidence": py_conf,
        "final_decision": legacy_final_decision,
        "customer_status": customer_status,
        "requires_admin_review":
            final_application_decision == "Manual Review Required",
        "decision_reasons": reasons,
        "python_prediction": py_pred,
        "python_confidence": py_conf,
        "python_probabilities": python_probabilities or {},
        "gtm_prediction": gt_pred,
        "gtm_confidence": gt_conf,
        "gtm_probabilities": gtm_probabilities or {},
        "predicted_class_match":
            bool(prediction_match) if gtm_available else False,
        "confidence_difference": confidence_difference,
        "model_consistency_status": consistency,
        "warranty_rule_result": warranty_rule_result,
        "missing_documents": missing_docs,
        "final_application_decision": final_application_decision,
    }
