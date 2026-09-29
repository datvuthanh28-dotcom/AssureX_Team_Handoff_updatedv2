from __future__ import annotations
from pathlib import Path
import json
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = (
    ROOT
    / "data"
    / "cleaned"
    / "assurex_v3_clean.csv"
)
OUTPUT_DIR = ROOT / "data" / "engineered"
AUDIT_DIR = ROOT / "data" / "audit"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = (
    OUTPUT_DIR
    / "assurex_v3_engineered.csv"
)
REPORT_PATH = (
    AUDIT_DIR
    / "assurex_v3_feature_engineering_report.csv"
)
MISSING_PATH = (
    AUDIT_DIR
    / "assurex_v3_feature_engineering_missingness.csv"
)
MANIFEST_PATH = (
    AUDIT_DIR
    / "assurex_v3_feature_engineering_manifest.json"
)
POLICY_PATH = (
    ROOT
    / "config"
    / "warranty_policies.json"
)
with POLICY_PATH.open(
    "r",
    encoding="utf-8",
) as f:
    POLICY_DATA = json.load(f)
POLICIES = POLICY_DATA["categories"]
COMMON_POLICY = POLICY_DATA["common"]
TARGET = "ClaimClass"
DATE_COLUMNS = [
    "PurchaseDate",
    "ClaimDate",
    "FaultDate",
]
EVIDENCE_COLUMNS = {
    "identity_evidence":
        "SerialEvidenceAvailable",
    "fault_evidence":
        "FaultEvidenceAvailable",
    "installation_evidence":
        "InstallationEvidenceAvailable",
    "repair_report":
        "RepairReportAvailable",
    "battery_diagnostic":
        "BatteryDiagnosticAvailable",
    "screen_fault_image":
        "ScreenFaultImageAvailable",
    "service_diagnostic":
        "ServiceDiagnosticAvailable",
    "component_identity_evidence":
        "ComponentIdentityEvidenceAvailable",
    "usage_meter_evidence":
        "UsageMeterEvidenceAvailable",
}
COMPONENT_CONDITIONS = {
    "Battery":
        "battery_claim",
    "Display Panel":
        "display_panel_claim",
    "Compressor":
        "compressor_claim",
    "Motor":
        "motor_claim",
    "Lens":
        "lens_claim",
}


def read_data():
    return pd.read_csv(
        INPUT_PATH,
        keep_default_na=False,
        na_values=[""],
    )


def yn(value):
    if pd.isna(value):
        return np.nan
    text = str(value).strip()
    mapping = {
        "yes": "Yes",
        "no": "No",
        "unknown": "Unknown",
        "not applicable": "Not Applicable",
        "n/a": "Not Applicable",
        "na": "Not Applicable",
    }
    return mapping.get(
        text.casefold(),
        text,
    )


def evidence_state(value):
    value = yn(value)
    if pd.isna(value):
        return "Unknown"
    if value == "Yes":
        return "Yes"
    if value in {
        "No",
        "Not Applicable",
    }:
        return "No"
    return "Unknown"


def parse_dates(df):
    out = df.copy()
    for column in DATE_COLUMNS:
        out[column] = pd.to_datetime(
            out[column],
            errors="coerce",
        )
    return out


def get_policy(row):
    category = row.get(
        "ProductCategory"
    )
    if pd.isna(category):
        return None
    return POLICIES.get(
        str(category)
    )


def get_component_cfg(row):
    policy = get_policy(row)
    if policy is None:
        return None
    component = row.get(
        "ClaimedComponent"
    )
    if pd.isna(component):
        return None
    return policy[
        "components"
    ].get(
        str(component)
    )


def primary_component(policy):
    if not policy:
        return None
    return next(
        iter(
            policy["components"]
        ),
        None,
    )


def component_eligible(row):
    cfg = get_component_cfg(row)
    if cfg is None:
        return "Unknown"
    return (
        "Yes"
        if bool(
            cfg["warranty_eligible"]
        )
        else "No"
    )


def applicable_months(row):
    cfg = get_component_cfg(row)
    if cfg is None:
        return np.nan
    return float(
        cfg["warranty_months"]
    )


def reporting_deadline(row):
    policy = get_policy(row)
    if policy is None:
        return np.nan
    return float(
        policy[
            "reporting_deadline_days"
        ]
    )


def warranty_expiry(row):
    if (
        component_eligible(row)
        != "Yes"
    ):
        return pd.NaT
    purchase = row.get(
        "PurchaseDate"
    )
    if pd.isna(purchase):
        return pd.NaT
    months = applicable_months(row)
    if pd.isna(months):
        return pd.NaT
    months = int(months)
    extension = 0
    policy = get_policy(row)
    if (
        policy
        and row.get(
            "ClaimedComponent"
        )
        == primary_component(policy)
        and yn(
            row.get(
                "ExtendedWarranty"
            )
        )
        == "Yes"
    ):
        extension = 12
    return (
        purchase
        + pd.DateOffset(
            months=months + extension
        )
    )


def warranty_status(row):
    eligible = row.get(
        "ComponentWarrantyEligible"
    )
    if eligible == "No":
        return "Not Eligible"
    remaining = row.get(
        "WarrantyRemainingDays"
    )
    if pd.isna(remaining):
        return "Unknown"
    if remaining < 0:
        return "Expired"
    if remaining <= 30:
        return "Nearing Expiry"
    return "Active"


def special_component_status(row):
    policy = get_policy(row)
    if policy is None:
        return "Unknown"
    component = row.get(
        "ClaimedComponent"
    )
    if pd.isna(component):
        return "Unknown"
    if component == primary_component(
        policy
    ):
        return "Not Applicable"
    return row.get(
        "WarrantyStatus",
        "Unknown",
    )


def fault_covered(row):
    policy = get_policy(row)
    if policy is None:
        return "Unknown"
    if (
        row.get(
            "ComponentWarrantyEligible"
        )
        == "No"
    ):
        return "No"
    fault = row.get(
        "FaultType"
    )
    damage = row.get(
        "DamageType"
    )
    if (
        pd.isna(fault)
        or pd.isna(damage)
    ):
        return "Unknown"
    if fault not in policy.get(
        "potentially_covered_faults",
        [],
    ):
        return "No"
    exclusions = set(
        COMMON_POLICY.get(
            "common_excluded_causes",
            [],
        )
    )
    exclusions.update(
        policy.get(
            "additional_excluded_causes",
            [],
        )
    )
    if damage in exclusions:
        return "No"
    return "Yes"


def required_evidence_keys(row):
    policy = get_policy(row)
    if policy is None:
        return []
    required = list(
        policy.get(
            "required_evidence",
            [],
        )
    )
    conditional = policy.get(
        "conditional_evidence",
        {},
    )
    if yn(
        row.get(
            "PreviousRepair"
        )
    ) == "Yes":
        required.extend(
            conditional.get(
                "previous_repair",
                [],
            )
        )
    component = row.get(
        "ClaimedComponent"
    )
    condition = (
        COMPONENT_CONDITIONS.get(
            component
        )
    )
    if condition:
        required.extend(
            conditional.get(
                condition,
                [],
            )
        )
    if (
        policy.get(
            "usage_limit"
        )
        is not None
    ):
        required.extend(
            conditional.get(
                "usage_limited_model",
                [],
            )
        )
    return list(
        dict.fromkeys(required)
    )


def warranty_proof_state(row):
    values = [
        evidence_state(
            row.get(
                "ReceiptAvailable"
            )
        ),
        evidence_state(
            row.get(
                "WarrantyCardAvailable"
            )
        ),
        evidence_state(
            row.get(
                "ElectronicWarrantyAvailable"
            )
        ),
    ]
    if "Yes" in values:
        return "Yes"
    if "Unknown" in values:
        return "Unknown"
    return "No"


def required_evidence_state(
    row,
    key,
):
    if key == "warranty_proof":
        return warranty_proof_state(
            row
        )
    column = EVIDENCE_COLUMNS.get(
        key
    )
    if column is None:
        return "Unknown"
    return evidence_state(
        row.get(column)
    )


def document_metrics(row):
    keys = required_evidence_keys(
        row
    )
    if not keys:
        return pd.Series({
            "RequiredDocumentCount":
                0.0,
            "AvailableRequiredDocumentCount":
                0.0,
            "MissingRequiredDocumentCount":
                0.0,
            "UnknownRequiredDocumentCount":
                0.0,
            "RequiredDocumentCoverageRatio":
                1.0,
            "RequiredDocumentsComplete":
                "Yes",
            "CriticalDocumentMissing":
                "No",
        })
    states = {
        key:
        required_evidence_state(
            row,
            key,
        )
        for key in keys
    }
    available = sum(
        v == "Yes"
        for v in states.values()
    )
    missing = sum(
        v == "No"
        for v in states.values()
    )
    unknown = sum(
        v == "Unknown"
        for v in states.values()
    )
    total = len(keys)
    if missing > 0:
        complete = "No"
    elif unknown > 0:
        complete = "Unknown"
    else:
        complete = "Yes"
    critical = {
        "warranty_proof",
        "identity_evidence",
    }
    policy = get_policy(row)
    if (
        policy
        and policy.get(
            "installation_required",
            False,
        )
    ):
        critical.add(
            "installation_evidence"
        )
    critical_states = [
        states[key]
        for key in critical
        if key in states
    ]
    if any(
        v == "No"
        for v in critical_states
    ):
        critical_missing = "Yes"
    elif any(
        v == "Unknown"
        for v in critical_states
    ):
        critical_missing = "Unknown"
    else:
        critical_missing = "No"
    return pd.Series({
        "RequiredDocumentCount":
            float(total),
        "AvailableRequiredDocumentCount":
            float(available),
        "MissingRequiredDocumentCount":
            float(missing),
        "UnknownRequiredDocumentCount":
            float(unknown),
        "RequiredDocumentCoverageRatio":
            float(
                available / total
            ),
        "RequiredDocumentsComplete":
            complete,
        "CriticalDocumentMissing":
            critical_missing,
    })


def customer_damage_indicator(row):
    fields = [
        "PhysicalDamageReported",
        "LiquidExposureReported",
        "ForeignObjectIncidentReported",
    ]
    values = [
        yn(row.get(field))
        for field in fields
    ]
    applicable = [
        value
        for value in values
        if (
            not pd.isna(value)
            and value
            != "Not Applicable"
        )
    ]
    if not applicable:
        return "Not Applicable"
    if "Yes" in applicable:
        return "Yes"
    if "Unknown" in applicable:
        return "Unknown"
    return "No"


def main():
    print("=" * 72)
    print("ASSUREX V3 - POLICY-AWARE FEATURE ENGINEERING")
    print("=" * 72)
    df = read_data()
    if len(df) != 1500:
        raise ValueError(
            f"Expected 1500 rows, found {len(df)}"
        )
    if df["ClaimID"].duplicated().any():
        raise ValueError(
            "ClaimID must be unique."
        )
    original_target = (
        df[TARGET].copy()
    )
    out = parse_dates(df)
    engineered = []
    out["ProductAgeDays"] = (
        out["ClaimDate"]
        - out["PurchaseDate"]
    ).dt.days.astype(float)
    engineered.append(
        "ProductAgeDays"
    )
    out[
        "ClaimReportingDelayDays"
    ] = (
        out["ClaimDate"]
        - out["FaultDate"]
    ).dt.days.astype(float)
    engineered.append(
        "ClaimReportingDelayDays"
    )
    out[
        "ApplicableWarrantyMonths"
    ] = out.apply(
        applicable_months,
        axis=1,
    )
    engineered.append(
        "ApplicableWarrantyMonths"
    )
    out[
        "ComponentWarrantyEligible"
    ] = out.apply(
        component_eligible,
        axis=1,
    )
    engineered.append(
        "ComponentWarrantyEligible"
    )
    out[
        "WarrantyExpiryDate"
    ] = out.apply(
        warranty_expiry,
        axis=1,
    )
    engineered.append(
        "WarrantyExpiryDate"
    )
    out[
        "WarrantyRemainingDays"
    ] = (
        out["WarrantyExpiryDate"]
        - out["ClaimDate"]
    ).dt.days.astype(float)
    engineered.append(
        "WarrantyRemainingDays"
    )
    out[
        "WarrantyStatus"
    ] = out.apply(
        warranty_status,
        axis=1,
    )
    engineered.append(
        "WarrantyStatus"
    )
    out[
        "SpecialComponentWarrantyStatus"
    ] = out.apply(
        special_component_status,
        axis=1,
    )
    engineered.append(
        "SpecialComponentWarrantyStatus"
    )
    out[
        "ReportingDeadlineDays"
    ] = out.apply(
        reporting_deadline,
        axis=1,
    )
    engineered.append(
        "ReportingDeadlineDays"
    )
    def reporting_ok(row):
        delay = row[
            "ClaimReportingDelayDays"
        ]
        deadline = row[
            "ReportingDeadlineDays"
        ]
        if (
            pd.isna(delay)
            or pd.isna(deadline)
        ):
            return "Unknown"
        return (
            "Yes"
            if delay <= deadline
            else "No"
        )
    out[
        "ClaimReportingWithinPeriod"
    ] = out.apply(
        reporting_ok,
        axis=1,
    )
    engineered.append(
        "ClaimReportingWithinPeriod"
    )
    out[
        "FaultCovered"
    ] = out.apply(
        fault_covered,
        axis=1,
    )
    engineered.append(
        "FaultCovered"
    )
    metrics = out.apply(
        document_metrics,
        axis=1,
    )
    for column in metrics.columns:
        out[column] = metrics[column]
        engineered.append(column)
    out[
        "MissingDocumentCount"
    ] = out[
        "MissingRequiredDocumentCount"
    ]
    out[
        "AvailableDocumentCount"
    ] = out[
        "AvailableRequiredDocumentCount"
    ]
    engineered.extend([
        "MissingDocumentCount",
        "AvailableDocumentCount",
    ])
    out[
        "PurchaseProofAvailable"
    ] = out[
        "ReceiptAvailable"
    ].map(yn)
    engineered.append(
        "PurchaseProofAvailable"
    )
    out[
        "WarrantyProofAvailable"
    ] = out.apply(
        warranty_proof_state,
        axis=1,
    )
    engineered.append(
        "WarrantyProofAvailable"
    )
    out[
        "ProductIdentityMatch"
    ] = out[
        "SerialNumberMatch"
    ].map(yn)
    engineered.append(
        "ProductIdentityMatch"
    )
    out[
        "HasRepairHistory"
    ] = out[
        "PreviousRepair"
    ].map(yn)
    engineered.append(
        "HasRepairHistory"
    )
    out[
        "HasPreviousReplacement"
    ] = out[
        "PreviousReplacement"
    ].map(yn)
    engineered.append(
        "HasPreviousReplacement"
    )
    out[
        "CustomerReportedDamageIndicator"
    ] = out.apply(
        customer_damage_indicator,
        axis=1,
    )
    engineered.append(
        "CustomerReportedDamageIndicator"
    )
    claim_amount = pd.to_numeric(
        out["ClaimAmount"],
        errors="coerce",
    )
    purchase_price = pd.to_numeric(
        out["ProductPurchasePrice"],
        errors="coerce",
    )
    out[
        "ClaimAmountRatio"
    ] = np.where(
        (
            purchase_price.notna()
            & (purchase_price > 0)
            & claim_amount.notna()
        ),
        claim_amount
        / purchase_price,
        np.nan,
    )
    engineered.append(
        "ClaimAmountRatio"
    )
    ocr = pd.to_numeric(
        out["OCRConfidence"],
        errors="coerce",
    )
    out[
        "OCRQualityBand"
    ] = pd.cut(
        ocr,
        bins=[
            -np.inf,
            0.70,
            0.85,
            np.inf,
        ],
        labels=[
            "Low",
            "Medium",
            "High",
        ],
        right=False,
    ).astype(object)
    out.loc[
        ocr.isna(),
        "OCRQualityBand",
    ] = "Unknown"
    engineered.append(
        "OCRQualityBand"
    )
    out[
        "ClaimMonth"
    ] = out[
        "ClaimDate"
    ].dt.month.astype(float)
    out[
        "ClaimDayOfWeek"
    ] = out[
        "ClaimDate"
    ].dt.dayofweek.astype(float)
    engineered.extend([
        "ClaimMonth",
        "ClaimDayOfWeek",
    ])
    if not out[TARGET].equals(
        original_target
    ):
        raise RuntimeError(
            "ClaimClass changed."
        )
    if len(out) != len(df):
        raise RuntimeError(
            "Row count changed."
        )
    for column in [
        "PurchaseDate",
        "ClaimDate",
        "FaultDate",
        "WarrantyExpiryDate",
    ]:
        out[column] = (
            out[column]
            .dt.strftime(
                "%Y-%m-%d"
            )
        )
    out.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )
    report = pd.DataFrame([
        {
            "Metric": "InputRows",
            "Value": len(df),
        },
        {
            "Metric": "OutputRows",
            "Value": len(out),
        },
        {
            "Metric": "InputColumns",
            "Value": df.shape[1],
        },
        {
            "Metric": "OutputColumns",
            "Value": out.shape[1],
        },
        {
            "Metric": "EngineeredFeatureCount",
            "Value": len(engineered),
        },
        {
            "Metric": "TargetUsed",
            "Value": "NO",
        },
        {
            "Metric": "ImputationPerformed",
            "Value": "NO",
        },
        {
            "Metric": "FeatureSelectionPerformed",
            "Value": "NO",
        },
    ])
    report.to_csv(
        REPORT_PATH,
        index=False,
        encoding="utf-8-sig",
    )
    missing = pd.DataFrame([
        {
            "Feature": feature,
            "MissingCount":
                int(
                    out[
                        feature
                    ].isna().sum()
                ),
            "UnknownCount":
                int(
                    (
                        out[
                            feature
                        ]
                        == "Unknown"
                    ).sum()
                )
                if (
                    feature in out
                    and out[
                        feature
                    ].dtype
                    == object
                )
                else 0,
        }
        for feature in engineered
    ])
    missing.to_csv(
        MISSING_PATH,
        index=False,
        encoding="utf-8-sig",
    )
    manifest = {
        "input":
            str(INPUT_PATH),
        "output":
            str(OUTPUT_PATH),
        "rows":
            len(out),
        "policy_version":
            POLICY_DATA.get(
                "policy_version"
            ),
        "engineered_features":
            engineered,
        "rules": {
            "target_used": False,
            "target_modified": False,
            "imputation": False,
            "scaling": False,
            "encoding": False,
            "feature_selection": False,
            "training": False,
        },
    }
    MANIFEST_PATH.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(
        "Input rows                  :",
        len(df),
    )
    print(
        "Output rows                 :",
        len(out),
    )
    print(
        "Engineered features         :",
        len(engineered),
    )
    print(
        "Target used                 : NO"
    )
    print(
        "Imputation                  : NO"
    )
    print()
    print("Created:")
    print(" -", OUTPUT_PATH)
    print(" -", REPORT_PATH)
    print(" -", MISSING_PATH)
    print(" -", MANIFEST_PATH)
if __name__ == "__main__":
    main()
