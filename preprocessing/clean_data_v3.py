from __future__ import annotations

"""AssureX - DATA CLEANING for generate_raw_dataset_v2.py.

Run from the project directory:
    python3 preprocessing/clean_data.py

Input:  data/raw/assurex_raw.csv (read only)
Output: data/cleaned/assurex_clean.csv and data/audit/cleaning_* reports.

This script does NOT read truth/issue manifests, recompute ClaimClass, impute
missing values, remove noise columns, create ML features, split data or fit a
model. Fixed schema rules are applied without learning dataset statistics.

A positive extreme value is a REVIEW flag, not automatically an error.
Parseable but contradictory dates are retained and flagged, not guessed.
Missing values are exported as empty CSV cells. Read subsequent CSVs with
keep_default_na=False, na_values=[''] to preserve 'Not Applicable'.

Reference documentation:
https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html
https://scikit-learn.org/stable/common_pitfalls.html
"""

import argparse
import csv
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = (
    Path(__file__).resolve().parent.parent
)

POLICY_PATH = (
    PROJECT_ROOT
    / "config"
    / "warranty_policies.json"
)

CLIENT_FORM_PATH = (
    PROJECT_ROOT
    / "config"
    / "client_claim_form.json"
)

with POLICY_PATH.open(
    "r",
    encoding="utf-8",
) as f:
    WARRANTY_CONFIG = json.load(f)

with CLIENT_FORM_PATH.open(
    "r",
    encoding="utf-8",
) as f:
    CLIENT_FORM_CONFIG = json.load(f)

WARRANTY_POLICIES = (
    WARRANTY_CONFIG["categories"]
)

CLIENT_CATEGORIES = (
    CLIENT_FORM_CONFIG["categories"]
)


VERSION = "assurex-cleaning-v3.0"
TARGET = "ClaimClass"
LABELS = {"Valid Claim", "Invalid Claim", "Manual Review"}
IDENTIFIERS = {"RecordID", "ClaimID", "CustomerID", "ProductID",
               "ModelNumber", "SerialNumber", "InternalBatchCode"}
NOISE_COLUMNS = {"BrowserFamily", "SubmissionMinute", "UiTheme",
                 "RandomScore", "InternalBatchCode"}
DATE_COLUMNS = ("PurchaseDate", "ClaimDate", "FaultDate")

# These six fields belong to the later FEATURE ENGINEERING step.
DEFERRED_COLUMNS = {
    "WarrantyExpiryDate",
    "WarrantyStatus",
    "FaultCovered",
    "ClaimReportingWithinPeriod",
    "RequiredDocumentsComplete",
    "PurchaseProofAvailable",
    "ComponentWarrantyEligible",
    "ReportingDeadlineDays",
    "RequiredDocumentCoverageRatio",
    "CriticalDocumentMissing",
}
AUDIT_ONLY_COLUMNS = {"PolicyClass", "HardInvalidReasons", "ManualReviewReasons",
                      "WarrantyRemainingDaysTruth", "ReportingDelayDaysTruth",
                      "IssueCount", "IssueTags", "ScenarioID"}

BINARY_COLUMNS = {
    "ExtendedWarranty",

    "ReceiptAvailable",
    "WarrantyCardAvailable",
    "ElectronicWarrantyAvailable",
    "ProductImageAvailable",
    "SerialEvidenceAvailable",
    "FaultEvidenceAvailable",

    "InstallationEvidenceAvailable",
    "BatteryDiagnosticAvailable",
    "ScreenFaultImageAvailable",
    "ServiceDiagnosticAvailable",
    "ComponentIdentityEvidenceAvailable",
    "UsageMeterEvidenceAvailable",

    "RepairReportAvailable",

    "PreviousRepair",
    "RepairAuthorized",
    "PreviousReplacement",
    "ReplacementWithinWarranty",

    "SerialNumberMatch",
    "ProductModelConsistent",
    "DuplicateClaimIndicator",
    "DocumentDuplicateIndicator",
    "ContradictionIndicator",

    # Customer-friendly answers
    "PhysicalDamageReported",
    "LiquidExposureReported",
    "BatterySymptomReported",
    "ErrorCodeAvailable",
    "IntermittentIssueReported",
    "ForeignObjectIncidentReported",
    "RecentReinstallationReported",
}

NOT_APPLICABLE_COLUMNS = {
    "RepairAuthorized",
    "RepairReportAvailable",
    "ReplacementWithinWarranty",

    "InstallationEvidenceAvailable",
    "BatteryDiagnosticAvailable",
    "ScreenFaultImageAvailable",
    "ServiceDiagnosticAvailable",
    "ComponentIdentityEvidenceAvailable",
    "UsageMeterEvidenceAvailable",

    "PhysicalDamageReported",
    "LiquidExposureReported",
    "BatterySymptomReported",
    "ErrorCodeAvailable",
    "IntermittentIssueReported",
    "ForeignObjectIncidentReported",
    "RecentReinstallationReported",
}


# ============================================================
# V3 category vocabulary comes from the same configs used by
# the generator and client form.
# ============================================================

PRODUCT_SUBTYPES = sorted({
    subtype
    for cfg in CLIENT_CATEGORIES.values()
    for subtype in cfg["product_subtypes"]
})

CUSTOMER_ISSUE_AREAS = sorted({
    area
    for cfg in CLIENT_CATEGORIES.values()
    for area in cfg["issue_areas"]
})

CLAIMED_COMPONENTS = sorted({
    component
    for cfg in WARRANTY_POLICIES.values()
    for component in cfg["components"]
})

FAULT_TYPES = [
    "Power Failure",
    "Display Failure",
    "Battery Problem",
    "Overheating",
    "Connectivity Issue",
    "Audio Failure",
    "Cooling Failure",
    "Water Leakage",
    "Noise",
    "Mechanical Failure",
    "Lens Failure",
    "Paper Feed Failure",
]

BASE_COVERED_DAMAGE_TYPES = {
    "Manufacturing Defect",
    "Electrical Failure",
    "Internal Component Failure",
}

BASE_EXCLUDED_DAMAGE_TYPES = {
    "Accidental Damage",
    "Water Damage",
    "Physical Damage",
    "Normal Wear",
    "Misuse",
}

POLICY_DAMAGE_TYPES = (
    BASE_COVERED_DAMAGE_TYPES
    | BASE_EXCLUDED_DAMAGE_TYPES
    | set(
        WARRANTY_CONFIG
        .get("common", {})
        .get("common_excluded_causes", [])
    )
    | {
        cause
        for cfg in WARRANTY_POLICIES.values()
        for cause in cfg.get(
            "additional_excluded_causes",
            [],
        )
    }
)

CATEGORY_VALUES = {
    "ProductCategory":
        list(WARRANTY_POLICIES.keys()),

    "ProductSubtype":
        PRODUCT_SUBTYPES,

    "ClaimedComponent":
        CLAIMED_COMPONENTS,

    "CustomerIssueArea":
        CUSTOMER_ISSUE_AREAS,

    "Brand": [
        "NovaTech",
        "Aster",
        "ZenCore",
        "PrimeView",
        "HomePro",
    ],

    "FaultType":
        FAULT_TYPES,

    "DamageType":
        sorted(POLICY_DAMAGE_TYPES),

    "UsageType": [
        "Household",
        "Business",
        "Other",
        "Not Applicable",
    ],

    "AffectedUnit": [
        "Indoor Unit",
        "Outdoor Unit",
        "Both",
        "Not Sure",
        "Not Applicable",
    ],

    "ConsumableTypeUsed": [
        "Original",
        "Compatible",
        "Unknown",
        "Not Applicable",
    ],

    "ClaimSubmissionChannel": [
        "Web",
        "Mobile App",
        "Service Center",
        "Email",
    ],

    "BrowserFamily": [
        "Chrome",
        "Safari",
        "Edge",
        "Firefox",
        "MobileWebView",
    ],

    "UiTheme": [
        "Light",
        "Dark",
        "System",
    ],
}

NUMERIC_COLUMNS = {
    "WarrantyDurationMonths",
    "RepairCount",
    "PriorClaimCount",

    "ProductPurchasePrice",
    "ClaimAmount",
    "PreviousRepairCost",

    "OCRConfidence",
    "SubmissionMinute",
    "RandomScore",
}
INTEGER_COLUMNS = {"WarrantyDurationMonths", "RepairCount", "PriorClaimCount",
                   "SubmissionMinute"}

# V3 warranty duration is category/component-policy driven.
# Examples include 0, 6, 12, 24, 60 and 120 months.
# Fixed review thresholds; values above these are RETAINED, not erased.
REVIEW_LIMITS = {"RepairCount": 10, "PriorClaimCount": 20,
                 "ClaimAmount": 100000, "PreviousRepairCost": 20000}

REQUIRED_COLUMNS = (IDENTIFIERS | set(DATE_COLUMNS) | BINARY_COLUMNS
                    | set(CATEGORY_VALUES) | NUMERIC_COLUMNS | {TARGET})
# Differences in these fields alone do not change the underlying claim facts.
INGESTION_ONLY_COLUMNS = NOISE_COLUMNS | {"ClaimSubmissionChannel"}
MISSING_TOKENS = {"", "null", "none", "nan"}

CHANGE_COLUMNS = ["SourceCSVRow", "RecordID", "ClaimID", "Column",
                  "Before", "After", "Action", "Reason"]
REVIEW_COLUMNS = ["SourceCSVRow", "RecordID", "ClaimID", "Columns",
                  "ObservedValues", "Reason", "Action"]
DUPLICATE_COLUMNS = ["ClaimID", "InputRows", "DuplicateType", "KeptRecordID",
                     "RemovedRecordIDs", "DifferingColumns", "Action"]


@dataclass
class CleaningResult:
    cleaned: pd.DataFrame
    changes: pd.DataFrame
    duplicates: pd.DataFrame
    review: pd.DataFrame
    quarantine: pd.DataFrame
    missing: pd.DataFrame
    summary: pd.DataFrame


def printable(value: Any) -> str:
    return "<MISSING>" if pd.isna(value) else str(value)


def normalize_key(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


def same_value(left: Any, right: Any) -> bool:
    if pd.isna(left) or pd.isna(right):
        return bool(pd.isna(left) and pd.isna(right))
    return str(left) == str(right)


def clean_number(value: str, column: str) -> tuple[Any, str]:
    """No quantiles, clipping, percentile thresholds or learned imputers."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return pd.NA, "Numeric value cannot be parsed unambiguously"
    if not math.isfinite(number):
        return pd.NA, "Numeric value must be finite"
    if column in INTEGER_COLUMNS:
        if not number.is_integer():
            return pd.NA, "Count/duration/minute must be an integer"
        if abs(number) >= 2**63:
            return pd.NA, "Integer exceeds the supported int64 storage range"
    if column == "OCRConfidence" and not 0 <= number <= 1:
        return pd.NA, "OCRConfidence must be between 0 and 1 inclusive"
    if column in {"RepairCount", "PriorClaimCount", "PreviousRepairCost"} and number < 0:
        return pd.NA, "This field cannot be negative"
    if column in {
        "ClaimAmount",
        "ProductPurchasePrice",
    } and number <= 0:
        return (
            pd.NA,
            f"{column} must be positive"
        )

    if (
        column == "WarrantyDurationMonths"
        and (
            number < 0
            or number > 120
        )
    ):
        return (
            pd.NA,
            "Warranty duration must be between 0 and 120 months"
        )
    if column == "SubmissionMinute" and not 0 <= number <= 59:
        return pd.NA, "SubmissionMinute must be between 0 and 59"
    return (int(number) if column in INTEGER_COLUMNS else number), ""


def clean_date(value: str) -> tuple[Any, str]:
    # Only the declared ISO format is accepted. Ambiguous day/month formats
    # are not silently guessed. Later schema versions can add explicit formats.
    try:
        date = datetime.strptime(value, "%Y-%m-%d")
    except (ValueError, TypeError):
        return pd.NA, "Date is invalid or is not in the declared YYYY-MM-DD format"
    return date.strftime("%Y-%m-%d"), ""


def clean_category(value: str, column: str) -> tuple[Any, str]:
    key = normalize_key(value)
    if column in BINARY_COLUMNS:
        aliases = {"yes": "Yes", "y": "Yes", "true": "Yes", "1": "Yes",
                   "no": "No", "n": "No", "false": "No", "0": "No",
                   "unknown": "Unknown", "unk": "Unknown",
                   "not applicable": "Not Applicable", "n/a": "Not Applicable",
                   "na": "Not Applicable", "not_applicable": "Not Applicable"}
        canonical = aliases.get(key)
        if canonical is None:
            return pd.NA, "Unrecognized categorical token; no fuzzy correction applied"
        if canonical == "Not Applicable" and column not in NOT_APPLICABLE_COLUMNS:
            return pd.NA, "Not Applicable is not allowed for this field in schema V2"
        return canonical, ""
    lookup = {normalize_key(item): item for item in CATEGORY_VALUES[column]}
    if key not in lookup:
        return pd.NA, "Category is outside the declared V2 vocabulary"
    return lookup[key], ""


def validate_schema(df: pd.DataFrame) -> None:
    if df.empty:
        raise ValueError("The raw dataset contains no records.")
    if not df.columns.is_unique:
        raise ValueError("Duplicate column names are not permitted.")
    leaked = sorted(set(df.columns) & AUDIT_ONLY_COLUMNS)
    if leaked:
        raise ValueError("Audit-only columns found in raw input: " + ", ".join(leaked))
    deferred = sorted(set(df.columns) & DEFERRED_COLUMNS)
    if deferred:
        raise ValueError(
            "Input is not the agreed V2 raw schema. Deferred features found: "
            + ", ".join(deferred)
            + ". Run the updated generator; do not use the earlier raw CSV."
        )
    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        raise ValueError("Required raw columns are missing: " + ", ".join(missing))


def clean_frame(raw: pd.DataFrame) -> CleaningResult:
    """Deterministic, schema-only cleaning. No access to generator truth."""
    raw = raw.reset_index(drop=True).copy()
    validate_schema(raw)
    df = raw.copy().astype(object)
    changes: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    duplicate_log: list[dict[str, Any]] = []
    quarantined: dict[int, str] = {}

    def log_change(idx: int, col: str, before: Any, after: Any,
                   action: str, reason: str) -> None:
        changes.append({
            "SourceCSVRow": idx + 2, "RecordID": printable(raw.at[idx, "RecordID"]),
            "ClaimID": printable(raw.at[idx, "ClaimID"]), "Column": col,
            "Before": printable(before), "After": printable(after),
            "Action": action, "Reason": reason,
        })

    def log_review(idx: int, cols: list[str], reason: str) -> None:
        reviews.append({
            "SourceCSVRow": idx + 2, "RecordID": printable(df.at[idx, "RecordID"]),
            "ClaimID": printable(df.at[idx, "ClaimID"]),
            "Columns": " | ".join(cols),
            "ObservedValues": json.dumps({col: printable(df.at[idx, col]) for col in cols}),
            "Reason": reason, "Action": "RETAIN_AND_REVIEW",
        })

    # Labels are left untouched. They are never used to repair any feature.
    for col in df.columns:
        if col == TARGET:
            continue
        for idx in df.index:
            before = df.at[idx, col]
            if pd.isna(before):
                df.at[idx, col] = pd.NA
                continue
            text = str(before).strip()
            if normalize_key(text) in MISSING_TOKENS:
                after, reason, action = pd.NA, "Explicit missing token", "MISSING_TOKEN_TO_NA"
            elif col in NUMERIC_COLUMNS:
                after, reason = clean_number(text, col)
                action = "INVALID_TO_NA" if reason else "PARSE_NUMBER"
            elif col in DATE_COLUMNS:
                after, reason = clean_date(text)
                action = "INVALID_TO_NA" if reason else "NORMALIZE_DATE"
            elif col in BINARY_COLUMNS or col in CATEGORY_VALUES:
                after, reason = clean_category(text, col)
                action = "INVALID_TO_NA" if reason else "NORMALIZE_CATEGORY"
            else:
                after, reason, action = text, "", "TRIM_WHITESPACE"
            df.at[idx, col] = after
            if not same_value(before, after):
                log_change(idx, col, before, after, action,
                           reason or "Fixed schema normalization; no learned statistics")

    for col in NUMERIC_COLUMNS:
        df[col] = pd.array(
            df[col],
            dtype=(
                "Int64"
                if col in INTEGER_COLUMNS
                else "Float64"
            ),
        )

    # --------------------------------------------------------
    # Deterministic V3 policy/schema validation.
    # No ClaimClass or audit truth is used.
    # --------------------------------------------------------

    for idx in df.index:

        category = df.at[
            idx,
            "ProductCategory",
        ]

        component = df.at[
            idx,
            "ClaimedComponent",
        ]

        subtype = df.at[
            idx,
            "ProductSubtype",
        ]

        issue_area = df.at[
            idx,
            "CustomerIssueArea",
        ]

        if pd.notna(category):

            category_cfg = (
                CLIENT_CATEGORIES.get(
                    category
                )
            )

            policy_cfg = (
                WARRANTY_POLICIES.get(
                    category
                )
            )

            if (
                category_cfg
                and pd.notna(subtype)
                and subtype
                not in category_cfg[
                    "product_subtypes"
                ]
            ):
                before = subtype
                df.at[
                    idx,
                    "ProductSubtype",
                ] = pd.NA

                log_change(
                    idx,
                    "ProductSubtype",
                    before,
                    pd.NA,
                    "INVALID_TO_NA",
                    "Subtype is not valid for this product category",
                )

            if (
                category_cfg
                and pd.notna(issue_area)
                and issue_area
                not in category_cfg[
                    "issue_areas"
                ]
            ):
                before = issue_area

                df.at[
                    idx,
                    "CustomerIssueArea",
                ] = pd.NA

                log_change(
                    idx,
                    "CustomerIssueArea",
                    before,
                    pd.NA,
                    "INVALID_TO_NA",
                    "Issue area is not valid for this product category",
                )

            if (
                policy_cfg
                and pd.notna(component)
                and component
                not in policy_cfg[
                    "components"
                ]
            ):
                before = component

                df.at[
                    idx,
                    "ClaimedComponent",
                ] = pd.NA

                log_change(
                    idx,
                    "ClaimedComponent",
                    before,
                    pd.NA,
                    "INVALID_TO_NA",
                    "Component is not valid for this product category",
                )

        # WarrantyDurationMonths is validated against configured
        # category/component policy.
        category = df.at[
            idx,
            "ProductCategory",
        ]

        component = df.at[
            idx,
            "ClaimedComponent",
        ]

        duration = df.at[
            idx,
            "WarrantyDurationMonths",
        ]

        if (
            pd.notna(category)
            and pd.notna(component)
            and pd.notna(duration)
            and category in WARRANTY_POLICIES
            and component
            in WARRANTY_POLICIES[
                category
            ]["components"]
        ):
            expected = int(
                WARRANTY_POLICIES[
                    category
                ]["components"][
                    component
                ]["warranty_months"]
            )

            if int(duration) != expected:

                before = duration

                df.at[
                    idx,
                    "WarrantyDurationMonths",
                ] = pd.NA

                log_change(
                    idx,
                    "WarrantyDurationMonths",
                    before,
                    pd.NA,
                    "INVALID_TO_NA",
                    (
                        "Duration does not match configured "
                        "category/component warranty policy"
                    ),
                )

    # Ingestion IDs must uniquely identify rows for a trustworthy change log.
    present_record_ids = df["RecordID"].dropna()
    if present_record_ids.duplicated().any():
        raise ValueError("RecordID repeats in the input. Resolve ingestion IDs before cleaning.")

    bad_identity = df["RecordID"].isna() | df["ClaimID"].isna()
    bad_label = ~df[TARGET].isin(LABELS)
    for idx in df.index[bad_identity | bad_label]:
        quarantined[idx] = (
            "Missing RecordID/ClaimID" if bad_identity.at[idx]
            else "Missing or unrecognized ClaimClass; label was not inferred"
        )
    # A bad label/identity on one record makes its entire ClaimID group ambiguous.
    bad_claim_ids = set(df.loc[list(quarantined), "ClaimID"].dropna()) if quarantined else set()
    for idx in df.index[df["ClaimID"].isin(bad_claim_ids)]:
        quarantined.setdefault(idx, "Same ClaimID as an untrusted identity/label record")

    candidates = df.loc[~df.index.isin(quarantined)]
    kept_indices: list[int] = []
    removed_duplicates = 0
    comparable_cols = [col for col in df.columns if col != "RecordID"]
    business_cols = [col for col in comparable_cols if col not in INGESTION_ONLY_COLUMNS]

    for claim_id, group in candidates.groupby("ClaimID", sort=True):
        if len(group) == 1:
            kept_indices.append(int(group.index[0]))
            continue
        differing = [col for col in comparable_cols if group[col].nunique(dropna=False) > 1]
        conflicts = [col for col in differing if col in business_cols]
        if conflicts:
            reason = "Same ClaimID has conflicting business facts or labels: " + ", ".join(conflicts)
            for idx in group.index:
                quarantined[int(idx)] = reason
            duplicate_log.append({
                "ClaimID": claim_id, "InputRows": len(group),
                "DuplicateType": "CONFLICTING_CLAIM", "KeptRecordID": "",
                "RemovedRecordIDs": "", "DifferingColumns": " | ".join(differing),
                "Action": "QUARANTINE_ALL_VERSIONS",
            })
            continue
        # No timestamp is available: use a stable ID tie-break, NOT the label,
        # truth manifest, class balance, or a fabricated 'latest record'.
        chosen = int(group.sort_values("RecordID", kind="mergesort").index[0])
        kept_indices.append(chosen)
        removed = group.drop(index=chosen)
        removed_duplicates += len(removed)
        duplicate_log.append({
            "ClaimID": claim_id, "InputRows": len(group),
            "DuplicateType": "EXACT_AFTER_NORMALIZATION" if not differing else "INGESTION_METADATA_ONLY",
            "KeptRecordID": df.at[chosen, "RecordID"],
            "RemovedRecordIDs": " | ".join(removed["RecordID"].astype(str)),
            "DifferingColumns": " | ".join(differing), "Action": "KEEP_ONE",
        })

    cleaned = df.loc[kept_indices].sort_values("ClaimID", kind="mergesort").copy()
    if cleaned.empty:
        raise ValueError("No unambiguous claims remain; inspect raw identities and labels.")

    # Positive extremes are REVIEW flags. Do not erase statistical tails.
    for col, limit in REVIEW_LIMITS.items():
        for idx in cleaned.index[(cleaned[col] > limit).fillna(False)]:
            log_review(int(idx), [col],
                       f"Above review threshold {limit}; not proven invalid, so retained")

    # Relational contradictions do not identify which source value is wrong.
    # Preserve parseable observations and flag them instead of inventing dates.
    date_pairs = [
        ("PurchaseDate", "ClaimDate", "Claim date is before purchase date"),
        ("PurchaseDate", "FaultDate", "Fault date is before purchase date"),
        ("FaultDate", "ClaimDate", "Fault date is after claim date"),
    ]
    for left, right, reason in date_pairs:
        for idx in cleaned.index:
            a, b = cleaned.at[idx, left], cleaned.at[idx, right]
            if pd.notna(a) and pd.notna(b) and a > b:
                log_review(int(idx), [left, right], reason + "; correct source value is unknown")

    for idx in cleaned.index:
        repair = cleaned.at[idx, "PreviousRepair"]
        count = cleaned.at[idx, "RepairCount"]
        cost = cleaned.at[idx, "PreviousRepairCost"]
        auth = cleaned.at[idx, "RepairAuthorized"]
        report = cleaned.at[idx, "RepairReportAvailable"]
        replacement = cleaned.at[idx, "PreviousReplacement"]
        replacement_status = cleaned.at[idx, "ReplacementWithinWarranty"]
        if pd.notna(repair) and repair == "No":
            if pd.notna(count) and count != 0:
                log_review(int(idx), ["PreviousRepair", "RepairCount"], "No repair history but nonzero repair count")
            if pd.notna(cost) and cost != 0:
                log_review(int(idx), ["PreviousRepair", "PreviousRepairCost"], "No repair history but nonzero repair cost")
            if pd.notna(auth) and auth != "Not Applicable":
                log_review(int(idx), ["PreviousRepair", "RepairAuthorized"], "No repair history but authorization is applicable")
        elif pd.notna(repair) and repair == "Yes":
            if pd.notna(count) and count == 0:
                log_review(int(idx), ["PreviousRepair", "RepairCount"], "Repair history exists but repair count is zero")
            if pd.notna(auth) and auth == "Not Applicable":
                log_review(int(idx), ["PreviousRepair", "RepairAuthorized"], "Repair history exists but authorization is Not Applicable")
            if pd.notna(report) and report == "Not Applicable":
                log_review(int(idx), ["PreviousRepair", "RepairReportAvailable"], "Repair history exists but report field is Not Applicable")
        if pd.notna(replacement) and pd.notna(replacement_status):
            inconsistent = ((replacement == "No" and replacement_status != "Not Applicable")
                            or (replacement == "Yes" and replacement_status == "Not Applicable"))
            if inconsistent:
                log_review(int(idx), ["PreviousReplacement", "ReplacementWithinWarranty"],
                           "Replacement fields disagree; no value inferred")

    # Conservation and target-protection checks (not model feature construction).
    if len(raw) != len(cleaned) + removed_duplicates + len(quarantined):
        raise RuntimeError("Row conservation failed.")
    if not cleaned["ClaimID"].is_unique:
        raise RuntimeError("Canonical ClaimID values are not unique.")
    if not (cleaned[TARGET] == raw.loc[cleaned.index, TARGET]).all():
        raise RuntimeError("Target labels were unexpectedly changed.")
    if list(cleaned.columns) != list(raw.columns):
        raise RuntimeError("Cleaning must preserve the raw feature columns.")

    quarantine = raw.loc[sorted(quarantined)].copy()
    quarantine["QuarantineReason"] = [quarantined[idx] for idx in quarantine.index]
    review_df = pd.DataFrame(reviews, columns=REVIEW_COLUMNS)
    changes_df = pd.DataFrame(changes, columns=CHANGE_COLUMNS)
    duplicate_df = pd.DataFrame(duplicate_log, columns=DUPLICATE_COLUMNS)

    def missing_count(series: pd.Series) -> int:
        return int(series.map(lambda v: pd.isna(v) or normalize_key(str(v)) in MISSING_TOKENS).sum())

    missing_report = pd.DataFrame([
        {"Column": col, "RawRows": len(raw), "RawMissingCount": missing_count(raw[col]),
         "CleanRows": len(cleaned), "CleanMissingCount": int(cleaned[col].isna().sum()),
         "CleanMissingPercent": round(100 * cleaned[col].isna().mean(), 4)}
        for col in raw.columns
    ])
    original_missing = sum(missing_count(raw[col]) for col in raw.columns)
    invalidated = int(changes_df["Action"].eq("INVALID_TO_NA").sum())
    summary_items = [
        ("CleanerVersion", VERSION), ("RawRows", len(raw)),
        ("RawColumns", raw.shape[1]), ("CleanRows", len(cleaned)),
        ("CleanColumns", cleaned.shape[1]), ("UniqueClaimIDs", cleaned["ClaimID"].nunique()),
        ("DuplicateRowsRemoved", removed_duplicates), ("QuarantinedRows", len(quarantined)),
        ("InvalidCellsConvertedToMissing", invalidated),
        ("MissingCellsBeforeCleaning", original_missing),
        ("MissingCellsAfterCleaning", int(cleaned.isna().sum().sum())),
        ("ReviewFlags", len(reviews)),
        ("ClaimsWithReviewFlags", review_df["ClaimID"].nunique()),
        ("NoiseColumnsRetained", len(NOISE_COLUMNS & set(cleaned.columns))),
        ("ImputationApplied", False), ("FeatureEngineeringApplied", False),
        ("FeatureSelectionApplied", False), ("TruthOrManifestUsed", False),
        ("ClaimClassModified", False),
    ]
    summary_items.extend(("CleanClassCount_" + name, int(cleaned[TARGET].eq(name).sum()))
                         for name in sorted(LABELS))
    summary = pd.DataFrame(summary_items, columns=["Metric", "Value"])
    return CleaningResult(cleaned.reset_index(drop=True), changes_df, duplicate_df,
                          review_df, quarantine.reset_index(drop=True), missing_report, summary)


def read_raw(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Raw CSV not found: {path}\nRun the V3 raw generator first.")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        header = next(csv.reader(stream), [])
    if len(header) != len(set(header)):
        raise ValueError("Raw CSV contains duplicate header names.")
    return pd.read_csv(path, encoding="utf-8-sig", dtype="string",
                       keep_default_na=False, on_bad_lines="error")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False, encoding="utf-8-sig", na_rep="", lineterminator="\n")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="AssureX V3: schema-only data cleaning")
    parser.add_argument("--project-root", type=Path,
                        default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--input", type=Path, default=None,
                        help="Optional raw CSV path; output remains under project-root.")
    args = parser.parse_args()
    root = args.project_root.expanduser().resolve()
    raw_path = (
        args.input.expanduser().resolve()
        if args.input
        else root
        / "data/raw/assurex_v3_raw.csv"
    )

    clean_path = (
        root
        / "data/cleaned/assurex_v3_clean.csv"
    )
    audit_dir = root / "data/audit"
    if raw_path == clean_path:
        raise ValueError("Input and clean output paths must be different; raw is read-only.")
    original_hash = file_hash(raw_path) if raw_path.is_file() else ""
    raw = read_raw(raw_path)
    result = clean_frame(raw)
    outputs = {
        clean_path: result.cleaned,
        audit_dir / "assurex_v3_cleaning_summary.csv":
            result.summary,

        audit_dir / "assurex_v3_cleaning_changes.csv":
            result.changes,

        audit_dir / "assurex_v3_cleaning_duplicates.csv":
            result.duplicates,

        audit_dir / "assurex_v3_cleaning_review_flags.csv":
            result.review,

        audit_dir / "assurex_v3_cleaning_quarantine.csv":
            result.quarantine,

        audit_dir / "assurex_v3_cleaning_missing_before_after.csv":
            result.missing,
    }
    if raw_path in outputs:
        raise ValueError("Input cannot be any generated report path.")
    for path, frame in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_csv(frame, path)
    if file_hash(raw_path) != original_hash:
        raise RuntimeError("The raw file changed while cleaning. Rerun on a stable input.")

    manifest = {
        "cleaner_version": VERSION, "raw_sha256": original_hash,
        "clean_sha256": file_hash(clean_path), "script_sha256": file_hash(Path(__file__)),
        "pandas_version": pd.__version__, "python_version": sys.version.split()[0],
        "input": str(raw_path), "output": str(clean_path),
        "data_is_synthetic": True, "schema": "generate_raw_dataset_v2",
        "allowed_warranty_months_schema_only": sorted(
            {
                int(component["warranty_months"])
                for policy in WARRANTY_CONFIG["categories"].values()
                for component in policy["components"].values()
            }
        ),
        "high_value_review_thresholds_not_deletion_rules": REVIEW_LIMITS,
        "date_format": "%Y-%m-%d", "date_conflicts": "retain_and_review",
        "duplicate_policy": "same ClaimID and business facts; stable RecordID tie-break",
        "duplicate_conflicts": "quarantine all versions; no label majority voting",
        "target_used_to_repair_features": False, "truth_manifest_read": False,
        "noise_columns_retained": sorted(NOISE_COLUMNS),
        "read_clean_csv": "pd.read_csv(path, keep_default_na=False, na_values=[''])",
        "learned_statistics": "none; imputation/scaling/feature selection deferred to train folds",
        "next_step": "lock holdout groups before target-guided EDA/feature selection",
        "warning": "Cleaned means normalized, not complete or guaranteed correct. Review flags remain.",
    }
    manifest_path = audit_dir / "cleaning_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    metrics = dict(zip(result.summary["Metric"], result.summary["Value"]))
    print("=" * 72)
    print("ASSUREX - DATA CLEANING (V3 RAW SCHEMA)")
    print("=" * 72)
    for title, key in [
        ("Raw rows", "RawRows"), ("Clean rows", "CleanRows"),
        ("Unique ClaimIDs", "UniqueClaimIDs"), ("Duplicate rows removed", "DuplicateRowsRemoved"),
        ("Quarantined rows", "QuarantinedRows"),
        ("Invalid cells -> missing", "InvalidCellsConvertedToMissing"),
        ("Missing cells retained", "MissingCellsAfterCleaning"),
        ("Review flags (not deleted)", "ReviewFlags"),
        ("Noise columns retained", "NoiseColumnsRetained"),
    ]:
        print(f"{title:30s}: {metrics[key]}")
    print("Class counts                  :", result.cleaned[TARGET].value_counts().to_dict())
    print("Raw file unchanged            : YES")
    print("Imputation / feature selection: NOT PERFORMED")
    print("\nCreated:")
    for path in [*outputs, manifest_path]:
        print(" -", path)
    print("\nReview flags are unresolved observations, not rows to delete automatically.")
    print("Missing values are intentionally retained. Do not train yet.")
    print("Preserve ClaimID for split alignment; identifiers are not ML predictors.")
    print("Lock train/validation/test groups before target-guided EDA/feature selection.")
    if not result.quarantine.empty:
        print("WARNING: Some claims were quarantined. Review cleaning_quarantine.csv before proceeding.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, FileNotFoundError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
