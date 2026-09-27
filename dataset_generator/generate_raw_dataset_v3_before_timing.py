from __future__ import annotations

import json

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


# ============================================================
# ASSUREX CLAIM ENGINE - STEP 1
# REALISTIC RAW DATASET GENERATOR
# ============================================================
# Design goals:
# 1) Generate a clean latent/observed claim first.
# 2) Assign ClaimClass from business truth/policy, not by directly
#    setting fields from a chosen class.
# 3) Inject realistic data-quality problems AFTER the label exists.
# 4) Keep an audit-only truth/manifest file that is NEVER used by ML.
# 5) Do NOT split train/validation/test yet. Splitting happens after
#    raw-data audit and duplicate grouping in later steps.
# ============================================================

RANDOM_SEED = 20260925
rng = np.random.default_rng(RANDOM_SEED)

# SRS-compatible common dataset target: 1,500 unique claims.
UNIQUE_CLAIMS = 1500
TARGET_PER_CLASS = {
    "Valid Claim": 500,
    "Invalid Claim": 500,
    "Manual Review": 500,
}

# Raw-data corruption controls.
EXACT_DUPLICATE_RATE = 0.020       # ~30 duplicated ingestion rows
NEAR_DUPLICATE_RATE = 0.010        # ~15 near-duplicate ingestion rows
CATEGORY_INCONSISTENCY_RATE = 0.010
INVALID_VALUE_RATE = 0.006
DATE_CORRUPTION_RATE = 0.004

# Missingness is intentionally heterogeneous and realistic.
MISSING_RATES = {
    "ReceiptAvailable": 0.05,
    "WarrantyCardAvailable": 0.06,
    "ProductImageAvailable": 0.04,
    "SerialEvidenceAvailable": 0.05,
    "FaultEvidenceAvailable": 0.07,
    "RepairReportAvailable": 0.10,
    "PreviousRepairCost": 0.08,
    "OCRConfidence": 0.04,
    "ClaimAmount": 0.02,
    "Brand": 0.01,
    "ModelNumber": 0.015,
    "SerialNumber": 0.01,
}

# Noise columns are deliberately unrelated to the target.
NOISE_COLUMNS = [
    "BrowserFamily",
    "SubmissionMinute",
    "UiTheme",
    "RandomScore",
    "InternalBatchCode",
]

# These are computed internally to establish policy truth, but they are
# intentionally NOT exported in the raw ML dataset. They will be recreated
# later in the FEATURE ENGINEERING stage of the pipeline.
RAW_ENGINEERED_COLUMNS = [
    "WarrantyExpiryDate",
    "WarrantyStatus",
    "FaultCovered",
    "ClaimReportingWithinPeriod",
    "RequiredDocumentsComplete",
    "PurchaseProofAvailable",

    # Used internally to establish business truth,
    # but intentionally removed from raw ML input.
    "ComponentWarrantyEligible",
    "ReportingDeadlineDays",
    "RequiredDocumentCoverageRatio",
    "CriticalDocumentMissing",
]

def load_warranty_policy_config():
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent

    policy_path = (
        project_root
        / "config"
        / "warranty_policies.json"
    )

    if not policy_path.exists():
        raise FileNotFoundError(
            f"Warranty policy not found: {policy_path}"
        )

    with policy_path.open(
        "r",
        encoding="utf-8",
    ) as f:
        data = json.load(f)

    if "categories" not in data:
        raise ValueError(
            "Invalid warranty policy: "
            "missing categories"
        )

    return data, policy_path


WARRANTY_POLICY_DATA, WARRANTY_POLICY_PATH = (
    load_warranty_policy_config()
)

WARRANTY_POLICY_VERSION = str(
    WARRANTY_POLICY_DATA.get(
        "policy_version",
        "unknown",
    )
)

WARRANTY_POLICIES = (
    WARRANTY_POLICY_DATA["categories"]
)


PRODUCTS = {
    "Laptop": {
        "brands": ["NovaTech", "Aster", "ZenCore"],
        "price": (500, 2600),
        "faults": ["Power Failure", "Display Failure", "Battery Problem", "Overheating", "Connectivity Issue"],
    },
    "Smartphone": {
        "brands": ["NovaTech", "PrimeView", "Aster"],
        "price": (250, 1800),
        "faults": ["Power Failure", "Display Failure", "Battery Problem", "Overheating", "Connectivity Issue"],
    },
    "Television": {
        "brands": ["PrimeView", "Aster", "HomePro"],
        "price": (350, 3200),
        "faults": ["Power Failure", "Display Failure", "Audio Failure", "Connectivity Issue"],
    },
    "Refrigerator": {
        "brands": ["HomePro", "ZenCore", "Aster"],
        "price": (500, 3000),
        "faults": ["Power Failure", "Cooling Failure", "Water Leakage", "Noise", "Mechanical Failure"],
    },
    "Washing Machine": {
        "brands": ["HomePro", "ZenCore", "PrimeView"],
        "price": (350, 2200),
        "faults": ["Power Failure", "Water Leakage", "Noise", "Mechanical Failure"],
    },
    "Air Conditioner": {
        "brands": ["HomePro", "Aster", "ZenCore"],
        "price": (450, 2800),
        "faults": ["Power Failure", "Cooling Failure", "Water Leakage", "Noise"],
    },
    "Camera": {
        "brands": ["PrimeView", "NovaTech", "Aster"],
        "price": (300, 3500),
        "faults": ["Power Failure", "Display Failure", "Battery Problem", "Lens Failure", "Connectivity Issue"],
    },
    "Printer": {
        "brands": ["PrimeView", "NovaTech", "HomePro"],
        "price": (120, 1200),
        "faults": ["Power Failure", "Paper Feed Failure", "Connectivity Issue", "Mechanical Failure"],
    },
}

COVERED_DAMAGE_TYPES = [
    "Manufacturing Defect",
    "Electrical Failure",
    "Internal Component Failure",
]

EXCLUDED_DAMAGE_TYPES = [
    "Accidental Damage",
    "Water Damage",
    "Physical Damage",
    "Normal Wear",
    "Misuse",
]

CLAIM_CHANNELS = ["Web", "Mobile App", "Service Center", "Email"]
BROWSERS = ["Chrome", "Safari", "Edge", "Firefox", "MobileWebView"]
UI_THEMES = ["Light", "Dark", "System"]


if set(PRODUCTS) != set(WARRANTY_POLICIES):
    missing = sorted(
        set(PRODUCTS)
        - set(WARRANTY_POLICIES)
    )

    extra = sorted(
        set(WARRANTY_POLICIES)
        - set(PRODUCTS)
    )

    raise ValueError(
        "Product / policy category mismatch. "
        f"Missing={missing}; Extra={extra}"
    )


@dataclass
class PolicyResult:
    claim_class: str
    hard_invalid_reasons: list[str]
    manual_reasons: list[str]


def choose(options, p=None):
    value = rng.choice(options, p=p)
    return value.item() if isinstance(value, np.generic) else value


def random_date(start: pd.Timestamp, end: pd.Timestamp) -> pd.Timestamp:
    if end <= start:
        return start
    days = int((end - start).days)
    return start + pd.Timedelta(days=int(rng.integers(0, days + 1)))


def yes_no(prob_yes: float) -> str:
    return "Yes" if rng.random() < prob_yes else "No"


def maybe_unknown(prob_yes: float, prob_no: float, prob_unknown: float) -> str:
    value = rng.choice(
        ["Yes", "No", "Unknown"],
        p=[prob_yes, prob_no, prob_unknown],
    )
    return str(value)


def choose_claimed_component(
    policy_cfg: dict[str, Any],
) -> str:
    """
    Generate which component the customer is claiming.

    Most claims concern the main product assembly.
    Special-component claims are less common.

    These probabilities are generation assumptions,
    not decision rules.
    """

    components = list(
        policy_cfg["components"].keys()
    )

    if not components:
        raise ValueError(
            "Policy contains no components."
        )

    if len(components) == 1:
        return components[0]

    primary_probability = 0.78

    other_probability = (
        (1.0 - primary_probability)
        / (len(components) - 1)
    )

    probabilities = [
        primary_probability,
        *[
            other_probability
            for _ in components[1:]
        ],
    ]

    return str(
        rng.choice(
            components,
            p=probabilities,
        )
    )


def derive_fault_coverage(
    policy_cfg: dict[str, Any],
    component_warranty_eligible: str,
    fault_type: str,
    damage_type: str,
) -> str:
    """
    Determine whether the reported fault context is potentially
    covered by the applicable category/component policy.

    DamageType is retained for backward compatibility with the
    existing pipeline. Semantically it represents the fault cause
    or damage cause reported by the customer.
    """

    if component_warranty_eligible != "Yes":
        return "No"

    covered_faults = set(
        policy_cfg.get(
            "potentially_covered_faults",
            [],
        )
    )

    if fault_type not in covered_faults:
        return "No"

    exclusions = set(EXCLUDED_DAMAGE_TYPES)

    exclusions.update(
        policy_cfg.get(
            "additional_excluded_causes",
            [],
        )
    )

    if damage_type in exclusions:
        return "No"

    return "Yes"


def get_required_evidence_keys(
    policy_cfg: dict[str, Any],
    claimed_component: str,
    previous_repair: str,
) -> list[str]:
    """
    Resolve the evidence requirements dynamically from policy.

    The result depends on:
    - product category policy,
    - claimed component,
    - repair history,
    - installation / usage policy.
    """

    required = list(
        policy_cfg.get(
            "required_evidence",
            [],
        )
    )

    conditional = policy_cfg.get(
        "conditional_evidence",
        {},
    )

    if previous_repair == "Yes":
        required.extend(
            conditional.get(
                "previous_repair",
                [],
            )
        )

    component_condition_map = {
        "Battery": "battery_claim",
        "Display Panel": "display_panel_claim",
        "Compressor": "compressor_claim",
        "Motor": "motor_claim",
        "Lens": "lens_claim",
    }

    condition = component_condition_map.get(
        claimed_component
    )

    if condition:
        required.extend(
            conditional.get(
                condition,
                [],
            )
        )

    if policy_cfg.get("usage_limit") is not None:
        required.extend(
            conditional.get(
                "usage_limited_model",
                [],
            )
        )

    # Remove duplicates while preserving order.
    return list(dict.fromkeys(required))


def evaluate_required_evidence(
    policy_cfg: dict[str, Any],
    required_keys: list[str],
    evidence_state: dict[str, str],
) -> tuple[str, float, str, list[str]]:
    """
    Return:
    - RequiredDocumentsComplete
    - RequiredDocumentCoverageRatio
    - CriticalDocumentMissing
    - list of missing evidence keys
    """

    if not required_keys:
        return "Yes", 1.0, "No", []

    missing = [
        key
        for key in required_keys
        if evidence_state.get(key) != "Yes"
    ]

    available_count = (
        len(required_keys)
        - len(missing)
    )

    coverage_ratio = round(
        available_count
        / len(required_keys),
        4,
    )

    complete = (
        "Yes"
        if not missing
        else "No"
    )

    # Critical evidence is intentionally narrower than
    # RequiredDocumentsComplete.
    critical_keys = {
        "warranty_proof",
        "identity_evidence",
    }

    if policy_cfg.get(
        "installation_required",
        False,
    ):
        critical_keys.add(
            "installation_evidence"
        )

    critical_missing = (
        "Yes"
        if any(
            key in missing
            for key in critical_keys
        )
        else "No"
    )

    return (
        complete,
        coverage_ratio,
        critical_missing,
        missing,
    )


def derive_policy(clean: dict[str, Any]) -> PolicyResult:
    hard_invalid = []
    manual = []

    if (
        clean.get(
            "ComponentWarrantyEligible"
        )
        == "No"
    ):
        hard_invalid.append(
            "Claimed component not warranty eligible"
        )

    if clean["WarrantyStatus"] == "Expired":
        hard_invalid.append("Warranty expired")
    if clean["FaultCovered"] == "No":
        hard_invalid.append("Fault/damage excluded")
    if clean["ClaimReportingWithinPeriod"] == "No":
        hard_invalid.append("Reporting period exceeded")
    if clean["SerialNumberMatch"] == "No":
        hard_invalid.append("Serial mismatch")
    if clean["RepairAuthorized"] == "No":
        hard_invalid.append("Unauthorized repair")
    if clean["DuplicateClaimIndicator"] == "Yes":
        hard_invalid.append("Duplicate claim")

    if clean["RequiredDocumentsComplete"] == "No":
        manual.append("Missing required evidence")
    if clean["ContradictionIndicator"] == "Yes":
        manual.append("Contradictory evidence")
    if clean["ProductModelConsistent"] == "No":
        manual.append("Product/model inconsistency")
    if clean["SerialNumberMatch"] == "Unknown":
        manual.append("Serial verification uncertain")
    if clean["RepairAuthorized"] == "Unknown":
        manual.append("Repair authorization uncertain")
    if clean["OCRConfidence"] < 0.70:
        manual.append("Low OCR confidence")

    if hard_invalid:
        label = "Invalid Claim"
    elif manual:
        label = "Manual Review"
    else:
        label = "Valid Claim"

    return PolicyResult(label, hard_invalid, manual)


def generate_clean_claim(index: int) -> tuple[dict[str, Any], dict[str, Any]]:
    category = str(
        rng.choice(list(PRODUCTS))
    )

    product_cfg = PRODUCTS[category]
    policy_cfg = WARRANTY_POLICIES[category]

    brand = str(
        rng.choice(
            product_cfg["brands"]
        )
    )

    claimed_component = (
        choose_claimed_component(
            policy_cfg
        )
    )

    component_cfg = (
        policy_cfg["components"][
            claimed_component
        ]
    )

    component_warranty_eligible = (
        "Yes"
        if bool(
            component_cfg[
                "warranty_eligible"
            ]
        )
        else "No"
    )

    reporting_deadline_days = int(
        policy_cfg[
            "reporting_deadline_days"
        ]
    )

    customer_id = f"CUS{int(rng.integers(1, 700)):05d}"
    product_id = f"PRD{int(rng.integers(1, 1000)):05d}"
    model_number = f"{brand[:3].upper()}-{category[:3].upper()}-{int(rng.integers(100, 999))}"
    serial_number = f"SN-{int(rng.integers(10000000, 99999999))}"

    purchase_date = random_date(
        pd.Timestamp("2023-01-01"),
        pd.Timestamp("2026-02-28"),
    )

    # Warranty duration now comes from the applicable
    # category + claimed-component warranty policy.
    warranty_months = int(
        component_cfg[
            "warranty_months"
        ]
    )

    primary_component = next(
        iter(
            policy_cfg[
                "components"
            ]
        )
    )

    # Keep the existing extended-warranty behaviour,
    # but only apply it to the primary product assembly.
    if (
        claimed_component == primary_component
        and component_warranty_eligible == "Yes"
    ):
        extended_warranty = yes_no(0.16)
    else:
        extended_warranty = "No"

    effective_months = (
        warranty_months
        + (
            12
            if extended_warranty == "Yes"
            else 0
        )
    )

    warranty_expiry = (
        purchase_date
        + pd.DateOffset(
            months=effective_months
        )
    )

    claim_date = random_date(
        purchase_date + pd.Timedelta(days=5),
        pd.Timestamp("2026-09-15"),
    )

    reporting_delay = int(np.clip(rng.gamma(shape=2.0, scale=8.0), 0, 90))
    fault_date = claim_date - pd.Timedelta(days=reporting_delay)
    if fault_date < purchase_date:
        fault_date = purchase_date
        reporting_delay = int((claim_date - fault_date).days)

    warranty_remaining_days = int((warranty_expiry - claim_date).days)
    warranty_status = "Active" if warranty_remaining_days >= 0 else "Expired"

    fault_type = str(
        rng.choice(
            product_cfg["faults"]
        )
    )

    # --------------------------------------------------------
    # Fault cause / damage cause generation.
    #
    # Most claims arise from potentially covered causes.
    # A smaller group contains common or category-specific
    # exclusions.
    # --------------------------------------------------------

    category_exclusions = list(
        policy_cfg.get(
            "additional_excluded_causes",
            [],
        )
    )

    excluded_cause_pool = list(
        dict.fromkeys(
            EXCLUDED_DAMAGE_TYPES
            + category_exclusions
        )
    )

    if rng.random() < 0.76:
        damage_type = str(
            rng.choice(
                COVERED_DAMAGE_TYPES
            )
        )
    else:
        damage_type = str(
            rng.choice(
                excluded_cause_pool
            )
        )

    fault_covered = derive_fault_coverage(
        policy_cfg=policy_cfg,
        component_warranty_eligible=(
            component_warranty_eligible
        ),
        fault_type=fault_type,
        damage_type=damage_type,
    )

    reporting_within_period = (
        "Yes"
        if reporting_delay
        <= reporting_deadline_days
        else "No"
    )

    receipt = yes_no(0.90)
    warranty_card = yes_no(0.86)

    # Electronic warranty is common for modern electronics.
    # It can satisfy warranty-proof requirements even where
    # a physical warranty card is unavailable.
    electronic_warranty = yes_no(0.58)

    product_image = yes_no(0.93)
    serial_evidence = yes_no(0.90)
    fault_evidence = yes_no(0.88)

    previous_repair = yes_no(0.28)
    if previous_repair == "Yes":
        repair_count = int(rng.integers(1, 4))
        repair_authorized = maybe_unknown(0.82, 0.10, 0.08)
        repair_report = yes_no(0.78)
        previous_repair_cost = round(float(rng.uniform(30, 650)), 2)
    else:
        repair_count = 0
        repair_authorized = "Not Applicable"
        repair_report = "Not Applicable"
        previous_repair_cost = 0.0

    # --------------------------------------------------------
    # Dynamic evidence requirements
    # --------------------------------------------------------

    required_evidence_keys = (
        get_required_evidence_keys(
            policy_cfg=policy_cfg,
            claimed_component=(
                claimed_component
            ),
            previous_repair=(
                previous_repair
            ),
        )
    )

    installation_evidence = (
        yes_no(0.90)
        if "installation_evidence"
        in required_evidence_keys
        else "Not Applicable"
    )

    battery_diagnostic = (
        yes_no(0.82)
        if "battery_diagnostic"
        in required_evidence_keys
        else "Not Applicable"
    )

    screen_fault_image = (
        yes_no(0.91)
        if "screen_fault_image"
        in required_evidence_keys
        else "Not Applicable"
    )

    service_diagnostic = (
        yes_no(0.85)
        if "service_diagnostic"
        in required_evidence_keys
        else "Not Applicable"
    )

    component_identity_evidence = (
        yes_no(0.90)
        if "component_identity_evidence"
        in required_evidence_keys
        else "Not Applicable"
    )

    usage_meter_evidence = (
        yes_no(0.86)
        if "usage_meter_evidence"
        in required_evidence_keys
        else "Not Applicable"
    )

    warranty_proof_available = (
        "Yes"
        if (
            receipt == "Yes"
            or warranty_card == "Yes"
            or electronic_warranty == "Yes"
        )
        else "No"
    )

    evidence_state = {
        "warranty_proof":
            warranty_proof_available,

        "identity_evidence":
            serial_evidence,

        "fault_evidence":
            fault_evidence,

        "installation_evidence":
            installation_evidence,

        "repair_report":
            repair_report,

        "battery_diagnostic":
            battery_diagnostic,

        "screen_fault_image":
            screen_fault_image,

        "service_diagnostic":
            service_diagnostic,

        "component_identity_evidence":
            component_identity_evidence,

        "usage_meter_evidence":
            usage_meter_evidence,
    }

    (
        required_docs_complete,
        required_document_coverage_ratio,
        critical_document_missing,
        missing_required_evidence,
    ) = evaluate_required_evidence(
        policy_cfg=policy_cfg,
        required_keys=(
            required_evidence_keys
        ),
        evidence_state=evidence_state,
    )

    previous_replacement = yes_no(0.10)
    replacement_within_warranty = (
        yes_no(0.85) if previous_replacement == "Yes" else "Not Applicable"
    )

    serial_match = maybe_unknown(0.91, 0.045, 0.045)
    model_consistent = yes_no(0.965)
    duplicate_claim = yes_no(0.035)
    document_duplicate = yes_no(0.025)
    contradiction = yes_no(0.035)

    # Purchase proof remains receipt/invoice based.
    # Warranty proof is broader and may also be established by
    # electronic warranty or warranty card.
    purchase_proof = receipt

    prior_claim_count = int(np.clip(rng.poisson(0.75), 0, 5))
    low, high = product_cfg["price"]
    product_price = float(rng.uniform(low, high))
    claim_amount = round(float(product_price * rng.uniform(0.08, 0.95)), 2)

    # Mostly good OCR, but with a realistic long tail.
    if rng.random() < 0.10:
        ocr_confidence = round(float(rng.uniform(0.45, 0.72)), 3)
    else:
        ocr_confidence = round(float(rng.uniform(0.72, 0.995)), 3)

    submission_channel = str(rng.choice(CLAIM_CHANNELS, p=[0.38, 0.27, 0.23, 0.12]))

    clean = {
        "ClaimID": f"CLM{index:05d}",
        "CustomerID": customer_id,
        "ProductID": product_id,
        "ProductCategory": category,
        "ClaimedComponent": claimed_component,
        "Brand": brand,
        "ModelNumber": model_number,
        "SerialNumber": serial_number,
        "PurchaseDate": purchase_date.strftime("%Y-%m-%d"),
        "ClaimDate": claim_date.strftime("%Y-%m-%d"),
        "FaultDate": fault_date.strftime("%Y-%m-%d"),
        "WarrantyDurationMonths":
            warranty_months,

        "ComponentWarrantyEligible":
            component_warranty_eligible,

        "ReportingDeadlineDays":
            reporting_deadline_days,

        "WarrantyExpiryDate":
            warranty_expiry.strftime(
                "%Y-%m-%d"
            ),
        "WarrantyStatus": warranty_status,
        "ExtendedWarranty": extended_warranty,
        "FaultType": fault_type,
        "DamageType": damage_type,
        "FaultCovered": fault_covered,
        "ClaimReportingWithinPeriod": reporting_within_period,
        "ReceiptAvailable":
            receipt,

        "WarrantyCardAvailable":
            warranty_card,

        "ElectronicWarrantyAvailable":
            electronic_warranty,

        "ProductImageAvailable":
            product_image,

        "SerialEvidenceAvailable":
            serial_evidence,

        "FaultEvidenceAvailable":
            fault_evidence,

        "InstallationEvidenceAvailable":
            installation_evidence,

        "BatteryDiagnosticAvailable":
            battery_diagnostic,

        "ScreenFaultImageAvailable":
            screen_fault_image,

        "ServiceDiagnosticAvailable":
            service_diagnostic,

        "ComponentIdentityEvidenceAvailable":
            component_identity_evidence,

        "UsageMeterEvidenceAvailable":
            usage_meter_evidence,

        "RepairReportAvailable":
            repair_report,
        "PreviousRepair": previous_repair,
        "RepairCount": repair_count,
        "RepairAuthorized": repair_authorized,
        "PreviousReplacement": previous_replacement,
        "ReplacementWithinWarranty": replacement_within_warranty,
        "SerialNumberMatch": serial_match,
        "ProductModelConsistent": model_consistent,
        "DuplicateClaimIndicator": duplicate_claim,
        "DocumentDuplicateIndicator": document_duplicate,
        "ContradictionIndicator": contradiction,
        "RequiredDocumentsComplete":
            required_docs_complete,

        "RequiredDocumentCoverageRatio":
            required_document_coverage_ratio,

        "CriticalDocumentMissing":
            critical_document_missing,

        "PurchaseProofAvailable":
            purchase_proof,
        "PriorClaimCount": prior_claim_count,
        "ClaimAmount": claim_amount,
        "PreviousRepairCost": previous_repair_cost,
        "OCRConfidence": ocr_confidence,
        "ClaimSubmissionChannel": submission_channel,
    }

    policy = derive_policy(clean)
    clean["ClaimClass"] = policy.claim_class

    # Audit-only latent/policy information. NEVER use as model features.
    audit = {
        "ClaimID": clean["ClaimID"],
        "PolicyClass": policy.claim_class,
        "HardInvalidReasons": " | ".join(policy.hard_invalid_reasons),
        "ManualReviewReasons": " | ".join(policy.manual_reasons),
        "WarrantyPolicyVersion":
            WARRANTY_POLICY_VERSION,

        "ProductCategoryTruth":
            category,

        "ClaimedComponentTruth":
            claimed_component,

        "ApplicableWarrantyMonthsTruth":
            warranty_months,

        "ComponentWarrantyEligibleTruth":
            component_warranty_eligible,

        "ReportingDeadlineDaysTruth":
            reporting_deadline_days,

        "FaultCoveredTruth":
            fault_covered,

        "RequiredEvidenceTruth":
            " | ".join(
                required_evidence_keys
            ),

        "MissingRequiredEvidenceTruth":
            " | ".join(
                missing_required_evidence
            ),

        "RequiredDocumentCoverageRatioTruth":
            required_document_coverage_ratio,

        "CriticalDocumentMissingTruth":
            critical_document_missing,

        "WarrantyRemainingDaysTruth":
            warranty_remaining_days,

        "ReportingDelayDaysTruth":
            reporting_delay,
    }
    return clean, audit


def build_balanced_clean_dataset() -> tuple[pd.DataFrame, pd.DataFrame]:
    accepted = []
    audits = []
    counts = Counter()
    attempts = 0
    max_attempts = 300000

    while sum(counts.values()) < UNIQUE_CLAIMS:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError("Could not reach target class balance; adjust generator probabilities.")

        clean, audit = generate_clean_claim(attempts)
        label = clean["ClaimClass"]
        if counts[label] >= TARGET_PER_CLASS[label]:
            continue

        # Re-number accepted claims so IDs are compact and stable.
        accepted_index = len(accepted) + 1
        clean["ClaimID"] = f"CLM{accepted_index:05d}"
        audit["ClaimID"] = clean["ClaimID"]

        accepted.append(clean)
        audits.append(audit)
        counts[label] += 1

    clean_df = pd.DataFrame(accepted)
    truth_df = pd.DataFrame(audits)

    # Randomize row order only after quotas are met.
    order = rng.permutation(len(clean_df))
    clean_df = clean_df.iloc[order].reset_index(drop=True)
    truth_df = truth_df.set_index("ClaimID").loc[clean_df["ClaimID"]].reset_index()

    return clean_df, truth_df


def add_noise_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    n = len(out)
    out["BrowserFamily"] = rng.choice(BROWSERS, size=n)
    out["SubmissionMinute"] = rng.integers(0, 60, size=n)
    out["UiTheme"] = rng.choice(UI_THEMES, size=n)
    out["RandomScore"] = np.round(rng.normal(0, 1, size=n), 5)
    out["InternalBatchCode"] = [f"B{int(x):04d}" for x in rng.integers(1, 1000, size=n)]
    return out


def inject_missingness(df: pd.DataFrame, issues: dict[str, set[str]]) -> pd.DataFrame:
    out = df.copy()
    for column, rate in MISSING_RATES.items():
        mask = rng.random(len(out)) < rate
        for record_id in out.loc[mask, "RecordID"]:
            issues[record_id].add(f"missing:{column}")
        out.loc[mask, column] = np.nan
    return out


def dirty_yes_no(value: Any) -> Any:
    if pd.isna(value):
        return value
    mapping = {
        "Yes": ["yes", "YES", "Y", " Yes "],
        "No": ["no", "NO", "N", " No "],
        "Unknown": ["unknown", "UNKNOWN", "UNK"],
        "Not Applicable": ["not applicable", "N/A", "NA"],
    }
    choices = mapping.get(str(value))
    return str(rng.choice(choices)) if choices else value


def inject_category_inconsistency(df: pd.DataFrame, issues: dict[str, set[str]]) -> pd.DataFrame:
    out = df.copy()
    candidate_columns = [
        "ExtendedWarranty", "ReceiptAvailable",
        "WarrantyCardAvailable", "ProductImageAvailable",
        "SerialEvidenceAvailable", "FaultEvidenceAvailable",
        "RepairReportAvailable", "PreviousRepair", "RepairAuthorized",
        "PreviousReplacement", "ReplacementWithinWarranty",
        "SerialNumberMatch", "ProductModelConsistent",
        "DuplicateClaimIndicator", "DocumentDuplicateIndicator",
        "ContradictionIndicator",
    ]

    for column in candidate_columns:
        mask = rng.random(len(out)) < CATEGORY_INCONSISTENCY_RATE
        for idx in out.index[mask]:
            old = out.at[idx, column]
            new = dirty_yes_no(old)
            if new != old:
                out.at[idx, column] = new
                issues[out.at[idx, "RecordID"]].add(f"category_format:{column}")

    # A small amount of whitespace/case noise in non-binary categories.
    for column in ["ProductCategory", "Brand", "ClaimSubmissionChannel"]:
        mask = rng.random(len(out)) < CATEGORY_INCONSISTENCY_RATE
        for idx in out.index[mask]:
            value = out.at[idx, column]
            if pd.isna(value):
                continue
            variants = [str(value).lower(), str(value).upper(), f" {value} "]
            out.at[idx, column] = str(rng.choice(variants))
            issues[out.at[idx, "RecordID"]].add(f"category_format:{column}")

    return out


def inject_invalid_values(df: pd.DataFrame, issues: dict[str, set[str]]) -> pd.DataFrame:
    out = df.copy()

    # Numeric invalids / outliers.
    specs = {
        "OCRConfidence": [-0.25, 1.25, 9.99],
        "RepairCount": [-3, -1, 99],
        "PriorClaimCount": [-2, 50, 999],
        "ClaimAmount": [-500.0, -1.0, 999999.0],
        "PreviousRepairCost": [-100.0, 99999.0],
        "WarrantyDurationMonths": [-12, 0, 240],
    }

    for column, bad_values in specs.items():
        mask = rng.random(len(out)) < INVALID_VALUE_RATE
        for idx in out.index[mask]:
            out.at[idx, column] = rng.choice(bad_values)
            issues[out.at[idx, "RecordID"]].add(f"invalid:{column}")

    # Date corruption: parse errors and impossible ordering.
    date_cols = ["PurchaseDate", "ClaimDate", "FaultDate"]
    for column in date_cols:
        mask = rng.random(len(out)) < DATE_CORRUPTION_RATE
        for idx in out.index[mask]:
            out.at[idx, column] = str(rng.choice(["2026-99-41", "not-a-date", "31/31/2026", ""] ))
            issues[out.at[idx, "RecordID"]].add(f"invalid_date:{column}")

    # A few logically impossible but syntactically valid dates.
    logical_mask = rng.random(len(out)) < DATE_CORRUPTION_RATE
    for idx in out.index[logical_mask]:
        purchase = pd.to_datetime(out.at[idx, "PurchaseDate"], errors="coerce")
        if pd.notna(purchase):
            out.at[idx, "FaultDate"] = (purchase - pd.Timedelta(days=int(rng.integers(1, 90)))).strftime("%Y-%m-%d")
            issues[out.at[idx, "RecordID"]].add("logical_date:FaultBeforePurchase")

    return out


def add_ingestion_duplicates(df: pd.DataFrame, issues: dict[str, set[str]]) -> pd.DataFrame:
    out = df.copy()
    original_n = len(out)
    exact_count = max(1, round(original_n * EXACT_DUPLICATE_RATE))
    near_count = max(1, round(original_n * NEAR_DUPLICATE_RATE))

    source_indices = rng.choice(out.index, size=exact_count + near_count, replace=False)
    extra_rows = []

    for j, idx in enumerate(source_indices, start=1):
        row = out.loc[idx].copy()
        source_record = row["RecordID"]
        new_record_id = f"REC-DUP-{j:04d}"
        row["RecordID"] = new_record_id

        if j <= exact_count:
            issues[new_record_id].add(f"exact_duplicate_of:{source_record}")
        else:
            # Near duplicate of the same claim: only non-business fields change.
            row["ClaimSubmissionChannel"] = str(rng.choice(CLAIM_CHANNELS))
            row["SubmissionMinute"] = int(rng.integers(0, 60))
            row["RandomScore"] = round(float(rng.normal()), 5)
            issues[new_record_id].add(f"near_duplicate_of:{source_record}")

        extra_rows.append(row)

    if extra_rows:
        out = pd.concat([out, pd.DataFrame(extra_rows)], ignore_index=True)

    return out


def build_manifest(df: pd.DataFrame, issues: dict[str, set[str]]) -> pd.DataFrame:
    rows = []
    for _, row in df[["RecordID", "ClaimID"]].iterrows():
        tags = sorted(issues.get(row["RecordID"], set()))
        rows.append({
            "RecordID": row["RecordID"],
            "ClaimID": row["ClaimID"],
            "IssueCount": len(tags),
            "IssueTags": " | ".join(tags),
        })
    return pd.DataFrame(rows)


def main():
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent if script_dir.name == "dataset_generator" else Path.cwd()

    raw_dir = project_root / "data" / "raw"
    audit_dir = project_root / "data" / "audit"
    raw_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 72)
    print("ASSUREX - STEP 1: GENERATE REALISTIC RAW DATA")
    print("=" * 72)

    clean_df, truth_df = build_balanced_clean_dataset()

    # RecordID represents ingestion rows. ClaimID represents the business claim.
    raw_df = clean_df.copy()
    raw_df.insert(0, "RecordID", [f"REC{i:05d}" for i in range(1, len(raw_df) + 1)])
    raw_df = add_noise_columns(raw_df)

    issues: dict[str, set[str]] = defaultdict(set)
    raw_df = inject_missingness(raw_df, issues)
    raw_df = inject_category_inconsistency(raw_df, issues)
    raw_df = inject_invalid_values(raw_df, issues)

    # Keep the raw dataset genuinely raw. Policy-derived/engineered fields are
    # hidden from the model input and will be recreated in Step 5.
    raw_df = raw_df.drop(columns=RAW_ENGINEERED_COLUMNS, errors="ignore")

    raw_df = add_ingestion_duplicates(raw_df, issues)

    # Randomize ingestion row order after duplicates are added.
    raw_df = raw_df.iloc[rng.permutation(len(raw_df))].reset_index(drop=True)
    manifest_df = build_manifest(raw_df, issues)

    raw_path = raw_dir / "assurex_raw.csv"
    truth_path = audit_dir / "assurex_truth_audit.csv"
    manifest_path = audit_dir / "raw_issue_manifest.csv"
    summary_path = audit_dir / "raw_generation_summary.csv"

    raw_df.to_csv(raw_path, index=False, encoding="utf-8-sig")
    truth_df.to_csv(truth_path, index=False, encoding="utf-8-sig")
    manifest_df.to_csv(manifest_path, index=False, encoding="utf-8-sig")

    unique_claims = raw_df["ClaimID"].nunique()
    unique_class_counts = (
        raw_df.drop_duplicates("ClaimID")["ClaimClass"].value_counts().to_dict()
    )
    duplicated_claim_rows = int(raw_df.duplicated("ClaimID", keep=False).sum())
    issue_records = int((manifest_df["IssueCount"] > 0).sum())
    total_missing = int(raw_df.isna().sum().sum())

    summary = pd.DataFrame([
        {"Metric": "RandomSeed", "Value": RANDOM_SEED},
        {"Metric": "RawRows", "Value": len(raw_df)},
        {"Metric": "UniqueClaims", "Value": unique_claims},
        {"Metric": "UniqueValidClaims", "Value": unique_class_counts.get("Valid Claim", 0)},
        {"Metric": "UniqueInvalidClaims", "Value": unique_class_counts.get("Invalid Claim", 0)},
        {"Metric": "UniqueManualReviewClaims", "Value": unique_class_counts.get("Manual Review", 0)},
        {"Metric": "RowsBelongingToDuplicateClaimIDs", "Value": duplicated_claim_rows},
        {"Metric": "RowsWithInjectedIssues", "Value": issue_records},
        {"Metric": "MissingCells", "Value": total_missing},
        {"Metric": "NoiseFeatureCount", "Value": len(NOISE_COLUMNS)},
        {"Metric": "RawColumnCount", "Value": raw_df.shape[1]},
        {"Metric": "EngineeredColumnsDeferred", "Value": " | ".join(RAW_ENGINEERED_COLUMNS)},
    ])
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")

    print(f"Raw rows              : {len(raw_df)}")
    print(f"Unique ClaimIDs        : {unique_claims}")
    print(f"Unique class counts    : {unique_class_counts}")
    print(f"Rows with issue tags   : {issue_records}")
    print(f"Missing cells          : {total_missing}")
    print(f"Duplicate ClaimID rows : {duplicated_claim_rows}")
    print(f"Raw columns            : {raw_df.shape[1]}")
    print(f"Deferred engineered    : {len(RAW_ENGINEERED_COLUMNS)}")
    print()
    print("Created:")
    print(f" - {raw_path}")
    print(f" - {truth_path}  [AUDIT ONLY - DO NOT TRAIN ON THIS]")
    print(f" - {manifest_path} [AUDIT ONLY - DO NOT TRAIN ON THIS]")
    print(f" - {summary_path}")
    print()
    print("IMPORTANT: Step 1 intentionally produces dirty raw data.")
    print("Do not train a model yet. Next step is raw-data profiling and cleaning rules.")


if __name__ == "__main__":
    main()
