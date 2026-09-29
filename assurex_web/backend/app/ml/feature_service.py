from __future__ import annotations
from datetime import date
import json
from pathlib import Path
import numpy as np
import pandas as pd
WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
POLICY_PATH = WORKSPACE_ROOT / "config" / "warranty_policies.json"
try:
    WARRANTY_POLICY = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    WARRANTY_POLICY = {"policy_version": "unknown", "common": {}, "categories": {}}


def get_category_policy(category):
    categories = WARRANTY_POLICY.get("categories", {})
    value = str(category or "").strip()
    if value in categories:
        return categories[value]
    normalized_category = value.casefold()
    return next(
        (policy for name, policy in categories.items() if name.casefold() == normalized_category),
        {},
    )
DOCUMENT_FIELDS = [
    "receipt_available",
    "warranty_card_available",
    "product_image_available",
    "serial_evidence_available",
    "fault_evidence_available",
]
CORE_DOCUMENT_FIELDS = [
    "receipt_available",
    "product_image_available",
    "serial_evidence_available",
    "fault_evidence_available",
]
COVERED_DAMAGE_TYPES = {
    "Manufacturing Defect",
    "Electrical Failure",
    "Internal Component Failure",
}
EXCLUDED_DAMAGE_TYPES = {
    "Accidental Damage",
    "Water Damage",
    "Physical Damage",
    "Normal Wear",
    "Misuse",
}


def yes_no(value):
    if value is None:
        return "Unknown"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    text = str(value).strip().lower()
    if text in {"yes", "y", "true", "1"}:
        return "Yes"
    if text in {"no", "n", "false", "0"}:
        return "No"
    if text in {"not applicable", "n/a", "na"}:
        return "Not Applicable"
    return "Unknown"


def normalized(value):
    return str(value or "").strip().casefold()


def parse_date(value):
    if not value:
        return None
    try:
        return pd.Timestamp(value)
    except Exception:
        return None


def build_claim_features(
    raw: dict,
    *,
    prior_claim_count: int = 0,
    duplicate_claim: bool = False,
):
    """
    Convert customer-friendly claim data into the exact 22
    model features used by the production model.
    No ClaimClass/target information is used.
    """
    claim_date = parse_date(
        raw.get("claim_date")
    ) or pd.Timestamp(date.today())
    purchase_date = parse_date(
        raw.get("purchase_date")
    )
    fault_date = parse_date(
        raw.get("fault_date")
    )
    category = str(raw.get("product_category") or "").strip()
    policy = get_category_policy(category)
    common_policy = WARRANTY_POLICY.get("common", {})
    claimed_component = str(raw.get("claimed_component") or "Main Unit").strip()
    component_policy = policy.get("components", {}).get(claimed_component, {})
    try:
        warranty_months = int(raw.get("warranty_duration_months"))
    except (TypeError, ValueError):
        warranty_months = policy.get("standard_warranty_months")
    if component_policy:
        warranty_months = component_policy.get("warranty_months", warranty_months)
    component_warranty_eligible = component_policy.get(
        "warranty_eligible",
        True if policy else None,
    )
    extended_warranty = yes_no(
        raw.get("extended_warranty")
    )
    warranty_expiry = None
    if (
        purchase_date is not None
        and warranty_months is not None
        and warranty_months > 0
    ):
        extension = (
            12
            if extended_warranty == "Yes"
            else 0
        )
        warranty_expiry = (
            purchase_date
            + pd.DateOffset(
                months=warranty_months + extension
            )
        )
    if warranty_expiry is None:
        warranty_remaining_days = np.nan
        warranty_status = "Unknown"
    else:
        warranty_remaining_days = float(
            (warranty_expiry - claim_date).days
        )
        warranty_status = (
            "Active"
            if warranty_remaining_days >= 0
            else "Expired"
        )
    if fault_date is None:
        reporting_delay = np.nan
        reporting_within_period = "Unknown"
    else:
        reporting_delay = float(
            (claim_date - fault_date).days
        )
        reporting_deadline = policy.get("reporting_deadline_days", 30)
        reporting_within_period = "Yes" if reporting_delay <= reporting_deadline else "No"
    damage_type = str(
        raw.get("damage_type") or ""
    ).strip()
    fault_type = str(raw.get("fault_type") or raw.get("problem_category") or "").strip()
    problem_category = str(raw.get("problem_category") or "").strip()
    fault_desc = str(raw.get("fault_description") or "").lower()
    policy_covered_faults = set(policy.get("potentially_covered_faults", []))
    policy_excluded_causes = set(common_policy.get("common_excluded_causes", [])) | set(policy.get("additional_excluded_causes", []))
    excluded_terms = {
        "water", "liquid", "dropped", "falling", "shattered", "physical impact",
        "spilled", "tampered", "cracked glass", "misuse", "accident",
        "roi", "rơi", "vo", "vỡ", "be", "bể", "be man hinh", "bể màn hình",
        "roi vo", "rơi vỡ", "va dap", "va đập", "rot nuoc", "rớt nước",
        "vao nuoc", "vào nước", "ngam nuoc", "ngấm nước", "do nuoc", "đổ nước",
        "physical damage", "liquid damage",
    }
    if (
        damage_type in policy_excluded_causes
        or fault_type in policy_excluded_causes
        or problem_category in policy_excluded_causes
        or any(t in problem_category.lower() for t in excluded_terms)
        or any(t in fault_desc for t in excluded_terms)
    ):
        fault_covered = "No"
    elif fault_type in policy_covered_faults or problem_category in policy_covered_faults:
        fault_covered = "Yes"
    elif damage_type in COVERED_DAMAGE_TYPES:
        fault_covered = "Yes"
    elif damage_type in EXCLUDED_DAMAGE_TYPES:
        fault_covered = "No"
    elif problem_category:
        fault_covered = "Yes"
    else:
        fault_covered = "Unknown"
    documents = {
        field: yes_no(raw.get(field))
        for field in DOCUMENT_FIELDS
    }
    evidence_aliases = {
        "warranty_proof": ["receipt_available", "warranty_card_available", "electronic_warranty_available"],
        "identity_evidence": ["serial_evidence_available", "product_image_available"],
        "fault_evidence": ["fault_evidence_available"],
        "installation_evidence": ["installation_evidence_available"],
        "repair_report": ["repair_report_available"],
        "battery_diagnostic": ["battery_diagnostic_available"],
        "screen_fault_image": ["screen_fault_image_available"],
        "service_diagnostic": ["service_diagnostic_available"],
        "component_identity_evidence": ["component_identity_evidence_available"],
        "usage_meter_evidence": ["usage_meter_evidence_available"],
    }
    policy_missing_evidence = []
    for required_evidence in policy.get("required_evidence", []):
        aliases = evidence_aliases.get(required_evidence, [required_evidence])
        if not any(yes_no(raw.get(alias)) == "Yes" for alias in aliases):
            policy_missing_evidence.append(required_evidence)
    policy_required_complete = "Yes" if not policy_missing_evidence else "No"
    observed_documents = [
        value
        for value in documents.values()
        if value != "Unknown"
    ]
    if not observed_documents:
        missing_document_count = np.nan
        available_document_count = np.nan
    else:
        missing_document_count = float(
            sum(
                value != "Yes"
                for value in observed_documents
            )
        )
        available_document_count = float(
            sum(
                value == "Yes"
                for value in observed_documents
            )
        )
    required_values = [
        documents[field]
        for field in CORE_DOCUMENT_FIELDS
    ]
    if "Unknown" in required_values:
        required_documents_complete = "Unknown"
    else:
        required_documents_complete = (
            "Yes"
            if all(
                value == "Yes"
                for value in required_values
            )
            else "No"
        )
    purchase_proof_available = documents[
        "receipt_available"
    ]
    previous_repair = yes_no(
        raw.get("previous_repair")
    )
    has_repair_history = (
        previous_repair
        if previous_repair in {"Yes", "No"}
        else "Unknown"
    )
    try:
        repair_count = int(
            raw.get("repair_count", 0)
        )
    except (TypeError, ValueError):
        repair_count = 0
    repair_report_available = yes_no(
        raw.get("repair_report_available")
    )
    if previous_repair == "No":
        repair_report_available = (
            "Not Applicable"
        )
    serial_number = normalized(
        raw.get("serial_number")
    )
    evidence_serial = normalized(
        raw.get("evidence_serial_number")
    )
    if serial_number and evidence_serial:
        serial_number_match = (
            "Yes"
            if serial_number == evidence_serial
            else "No"
        )
    else:
        serial_number_match = "Unknown"
    model_number = normalized(
        raw.get("model_number")
    )
    evidence_model = normalized(
        raw.get("evidence_model_number")
    )
    if model_number and evidence_model:
        product_model_consistent = (
            "Yes"
            if model_number == evidence_model
            else "No"
        )
    else:
        product_model_consistent = "Unknown"
    contradiction = False
    if (
        purchase_date is not None
        and fault_date is not None
        and fault_date < purchase_date
    ):
        contradiction = True
    if (
        purchase_date is not None
        and claim_date < purchase_date
    ):
        contradiction = True
    contradiction_indicator = (
        "Yes" if contradiction else "No"
    )
    duplicate_indicator = (
        "Yes" if duplicate_claim else "No"
    )
    try:
        ocr_confidence = float(
            raw.get("ocr_confidence")
        )
    except (TypeError, ValueError):
        ocr_confidence = np.nan
    try:
        claim_amount_raw = raw.get("claim_amount")
        claim_amount = (
            float(claim_amount_raw)
            if claim_amount_raw not in {None, ""}
            else np.nan
        )
    except (TypeError, ValueError):
        claim_amount = np.nan
    repair_authorized = yes_no(
        raw.get("repair_authorized")
    )
    product_identity_match = serial_number_match
    try:
        ocr_value = float(ocr_confidence)
        if np.isnan(ocr_value):
            ocr_quality_band = "Unknown"
        elif ocr_value < 0.70:
            ocr_quality_band = "Low"
        elif ocr_value < 0.85:
            ocr_quality_band = "Medium"
        else:
            ocr_quality_band = "High"
    except (TypeError, ValueError):
        ocr_quality_band = "Unknown"
    model_features = {
        "RepairAuthorized": repair_authorized,
        "SerialNumberMatch": serial_number_match,
        "ProductModelConsistent": product_model_consistent,
        "DuplicateClaimIndicator": duplicate_indicator,
        "ContradictionIndicator": contradiction_indicator,
        "OCRConfidence": ocr_confidence,
        "ClaimReportingDelayDays": reporting_delay,
        "WarrantyRemainingDays": warranty_remaining_days,
        "ClaimReportingWithinPeriod": reporting_within_period,
        "FaultCovered": fault_covered,
        "RequiredDocumentsComplete": required_documents_complete,
        "MissingDocumentCount": missing_document_count,
        "ProductIdentityMatch": product_identity_match,
        "OCRQualityBand": ocr_quality_band,
    }
    rule_data = {
        **model_features,
        "PolicyVersion": WARRANTY_POLICY.get("policy_version"),
        "PolicyCategory": category,
        "PolicyComponent": claimed_component,
        "PolicyReportingDeadlineDays": policy.get("reporting_deadline_days", 30),
        "PolicyComponentWarrantyEligible": component_warranty_eligible,
        "PolicyRequiredEvidence": policy.get("required_evidence", []),
        "PolicyConditionalEvidence": policy.get("conditional_evidence", {}),
        "PolicyRequiredEvidenceComplete": policy_required_complete,
        "PolicyMissingEvidence": policy_missing_evidence,
        "PolicyCoveredFaults": sorted(policy.get("potentially_covered_faults", [])),
        "PolicyExcludedCauses": sorted(
            set(common_policy.get("common_excluded_causes", []))
            | set(policy.get("additional_excluded_causes", []))
        ),
        "PolicyInstallationRequired": policy.get("installation_required", False),
        "PolicyUsageLimit": policy.get("usage_limit"),
        "ComponentWarrantyEligible": (
            "Yes" if component_warranty_eligible is True
            else "No" if component_warranty_eligible is False
            else "Unknown"
        ),
        "RepairAuthorized":
            repair_authorized,
        "DocumentDuplicateIndicator":
            yes_no(
                raw.get(
                    "document_duplicate_indicator"
                )
            ),
        "InstallationEvidenceAvailable": yes_no(
            raw.get("installation_evidence_available")
        ),
    }
    return {
        "model_features": model_features,
        "rule_data": rule_data,
        "derived": {
            "warranty_expiry":
                (
                    warranty_expiry.strftime(
                        "%Y-%m-%d"
                    )
                    if warranty_expiry
                    is not None
                    else None
                ),
            "warranty_status":
                warranty_status,
            "warranty_remaining_days":
                warranty_remaining_days,
            "claim_reporting_delay_days":
                reporting_delay,
            "policy_version": WARRANTY_POLICY.get("policy_version"),
            "policy_category": category,
            "policy_component": claimed_component,
            "policy_reporting_deadline_days": policy.get("reporting_deadline_days", 30),
            "policy_required_evidence": policy.get("required_evidence", []),
            "policy_conditional_evidence": policy.get("conditional_evidence", {}),
            "policy_covered_faults": sorted(policy.get("potentially_covered_faults", [])),
            "policy_excluded_causes": sorted(
                set(common_policy.get("common_excluded_causes", []))
                | set(policy.get("additional_excluded_causes", []))
            ),
        },
    }
