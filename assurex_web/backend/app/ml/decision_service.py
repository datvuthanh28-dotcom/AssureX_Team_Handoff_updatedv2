LOW_CONFIDENCE_THRESHOLD = 0.60


WARRANTY_MISMATCH_LABELS = {
    "serial_number": "serial number",
    "model_number": "model number",
    "purchase_date": "purchase date",
    "warranty_duration_months": "warranty duration",
}


def apply_business_rules(
    claim_data,
    ml_prediction,
    ml_confidence,
):
    hard_invalid_reasons = []
    manual_review_reasons = []
    warning_reasons = []

    def value(name):
        return str(
            claim_data.get(name, "")
        ).strip().lower()

    warranty_mismatch = (
        value(
            "WarrantyDocumentMismatchIndicator"
        )
        == "yes"
    )

    mismatch_fields = (
        claim_data.get(
            "WarrantyDocumentMismatchFields"
        )
        or []
    )

    # -----------------------------------------
    # WARRANTY DOCUMENT MISMATCH
    #
    # Important:
    # A customer-edited value that conflicts
    # with OCR evidence is uncertainty, not an
    # automatic rejection.
    # -----------------------------------------

    if warranty_mismatch:
        for field in mismatch_fields:
            label = WARRANTY_MISMATCH_LABELS.get(
                field,
                field,
            )

            reason = (
                f"Warranty document mismatch: "
                f"{label}"
            )

            if reason not in manual_review_reasons:
                manual_review_reasons.append(
                    reason
                )

    # -----------------------------------------
    # LOW CONFIDENCE
    # -----------------------------------------

    if ml_confidence < LOW_CONFIDENCE_THRESHOLD:
        manual_review_reasons.append(
            "Low ML confidence"
        )

    # -----------------------------------------
    # MISSING DOCUMENTS
    # -----------------------------------------

    if value(
        "RequiredDocumentsComplete"
    ) in {
        "no",
        "false",
        "0",
    }:
        manual_review_reasons.append(
            "Missing required documents"
        )

    # -----------------------------------------
    # CONTRADICTIONS
    # -----------------------------------------

    if (
        value("ContradictionIndicator")
        == "yes"
        and not warranty_mismatch
    ):
        manual_review_reasons.append(
            "Claim contradiction"
        )

    if (
        value(
            "DocumentContradictionIndicator"
        )
        == "yes"
        and not warranty_mismatch
    ):
        manual_review_reasons.append(
            "Document contradiction"
        )

    # -----------------------------------------
    # PRODUCT / MODEL
    # -----------------------------------------

    if (
        value("ProductModelConsistent")
        == "no"
        and not warranty_mismatch
    ):
        manual_review_reasons.append(
            "Product/model inconsistency"
        )

    # -----------------------------------------
    # HARD INVALID
    # -----------------------------------------

    if value(
        "DuplicateClaimIndicator"
    ) in {
        "yes",
        "true",
        "1",
    }:
        hard_invalid_reasons.append(
            "Duplicate claim"
        )

    if value("WarrantyStatus") == "expired":
        hard_invalid_reasons.append(
            "Warranty expired"
        )

    if value("FaultCovered") == "no":
        hard_invalid_reasons.append(
            "Fault not covered"
        )

    # -----------------------------------------
    # SERIAL VERIFICATION
    #
    # If serial mismatch came from customer
    # editing OCR-extracted warranty data,
    # route to Manual Review instead of
    # automatically rejecting it.
    # -----------------------------------------

    serial_status = value(
        "SerialNumberMatch"
    )

    if serial_status == "no":
        if warranty_mismatch:
            reason = (
                "Warranty document mismatch: "
                "serial number"
            )

            if reason not in manual_review_reasons:
                manual_review_reasons.append(
                    reason
                )
        else:
            hard_invalid_reasons.append(
                "Serial number mismatch"
            )

    elif serial_status == "unknown":
        manual_review_reasons.append(
            "Serial number verification issue"
        )

    # -----------------------------------------
    # REPAIR AUTHORIZATION
    # -----------------------------------------

    repair_status = value(
        "RepairAuthorized"
    )

    if repair_status == "no":
        hard_invalid_reasons.append(
            "Unauthorized repair"
        )

    elif repair_status == "unknown":
        manual_review_reasons.append(
            "Repair authorization issue"
        )

    # -----------------------------------------
    # DOCUMENT DUPLICATE WARNING
    # -----------------------------------------

    if value(
        "DocumentDuplicateIndicator"
    ) in {
        "yes",
        "true",
        "1",
    }:
        warning_reasons.append(
            "Duplicate document warning"
        )

    # -----------------------------------------
    # FINAL PRECEDENCE
    #
    # True hard invalid rules still win:
    # expired warranty, uncovered fault,
    # duplicate claim, unauthorized repair.
    #
    # Warranty-document mismatches themselves
    # are Manual Review.
    # -----------------------------------------

    if hard_invalid_reasons:
        final_decision = "Invalid Claim"

        reasons = (
            hard_invalid_reasons
            + manual_review_reasons
            + warning_reasons
        )

    elif manual_review_reasons:
        final_decision = "Manual Review"

        reasons = (
            manual_review_reasons
            + warning_reasons
        )

    else:
        final_decision = ml_prediction
        reasons = warning_reasons

    customer_status = {
        "Valid Claim": "Approved",
        "Invalid Claim": "Rejected",
        "Manual Review": "Under Review",
    }.get(
        final_decision,
        "Under Review",
    )

    return {
        "ml_prediction": ml_prediction,
        "ml_confidence": ml_confidence,
        "final_decision": final_decision,
        "customer_status": customer_status,
        "requires_admin_review":
            final_decision == "Manual Review",
        "decision_reasons": reasons,
    }
