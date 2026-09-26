from __future__ import annotations

from datetime import date
import numpy as np
import pandas as pd


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

    # -------------------------------------------------
    # WARRANTY
    # -------------------------------------------------

    try:
        warranty_months = int(
            raw.get("warranty_duration_months")
        )
    except (TypeError, ValueError):
        warranty_months = None

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

    # -------------------------------------------------
    # CLAIM REPORTING
    # -------------------------------------------------

    if fault_date is None:
        reporting_delay = np.nan
        reporting_within_period = "Unknown"
    else:
        reporting_delay = float(
            (claim_date - fault_date).days
        )

        reporting_within_period = (
            "Yes"
            if reporting_delay <= 30
            else "No"
        )

    # -------------------------------------------------
    # DAMAGE / COVERAGE
    # -------------------------------------------------

    damage_type = str(
        raw.get("damage_type") or ""
    ).strip()

    if damage_type in COVERED_DAMAGE_TYPES:
        fault_covered = "Yes"
    elif damage_type in EXCLUDED_DAMAGE_TYPES:
        fault_covered = "No"
    else:
        fault_covered = "Unknown"

    # -------------------------------------------------
    # DOCUMENTS
    # -------------------------------------------------

    documents = {
        field: yes_no(raw.get(field))
        for field in DOCUMENT_FIELDS
    }

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

    # -------------------------------------------------
    # REPAIR HISTORY
    # -------------------------------------------------

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

    # -------------------------------------------------
    # SERIAL / MODEL CONSISTENCY
    # -------------------------------------------------

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

    # -------------------------------------------------
    # CONTRADICTION CHECK
    # -------------------------------------------------

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

    # -------------------------------------------------
    # OCR
    # OCR is intentionally missing until the OCR stage
    # is integrated. The trained sklearn pipeline has
    # numerical imputation.
    # -------------------------------------------------

    try:
        ocr_confidence = float(
            raw.get("ocr_confidence")
        )
    except (TypeError, ValueError):
        ocr_confidence = np.nan

    # -------------------------------------------------
    # CLAIM AMOUNT
    #
    # Customer may not know an estimated amount.
    # Preserve missing values for the sklearn numerical
    # preprocessing pipeline instead of converting them to 0.
    # -------------------------------------------------

    try:
        claim_amount_raw = raw.get("claim_amount")

        claim_amount = (
            float(claim_amount_raw)
            if claim_amount_raw not in {None, ""}
            else np.nan
        )

    except (TypeError, ValueError):
        claim_amount = np.nan

    # -------------------------------------------------
    # EXACT 22 PRODUCTION MODEL FEATURES
    # -------------------------------------------------

    model_features = {
        "WarrantyCardAvailable":
            documents["warranty_card_available"],

        "RepairReportAvailable":
            repair_report_available,

        "PreviousRepair":
            previous_repair,

        "RepairCount":
            repair_count,

        "SerialNumberMatch":
            serial_number_match,

        "ProductModelConsistent":
            product_model_consistent,

        "DuplicateClaimIndicator":
            duplicate_indicator,

        "ContradictionIndicator":
            contradiction_indicator,

        "PriorClaimCount":
            int(prior_claim_count),

        "ClaimAmount":
            claim_amount,

        "OCRConfidence":
            ocr_confidence,

        "ClaimSubmissionChannel":
            "Web",

        "ClaimReportingDelayDays":
            reporting_delay,

        "WarrantyRemainingDays":
            warranty_remaining_days,

        "WarrantyStatus":
            warranty_status,

        "ClaimReportingWithinPeriod":
            reporting_within_period,

        "FaultCovered":
            fault_covered,

        "MissingDocumentCount":
            missing_document_count,

        "AvailableDocumentCount":
            available_document_count,

        "RequiredDocumentsComplete":
            required_documents_complete,

        "PurchaseProofAvailable":
            purchase_proof_available,

        "HasRepairHistory":
            has_repair_history,
    }

    # Additional raw values used by Decision Engine.
    rule_data = {
        **model_features,

        "RepairAuthorized":
            yes_no(
                raw.get("repair_authorized")
            ),

        "DocumentDuplicateIndicator":
            yes_no(
                raw.get(
                    "document_duplicate_indicator"
                )
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
        },
    }
