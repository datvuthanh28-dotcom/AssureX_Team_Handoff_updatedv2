from __future__ import annotations

import hashlib
import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PYTHON_MODEL = ROOT / "model" / "assurex_v3_final_model.joblib"
FEATURES = ROOT / "model" / "assurex_v3_final_features.csv"
PYTHON_PRED = ROOT / "data" / "final_evaluation_v3" / "assurex_v3_test_predictions.csv"
GTM_PRED = ROOT / "data" / "final_evaluation_v3" / "gtm" / "assurex_v3_gtm_g2_final_test_predictions.csv"
GTM_DIR = ROOT / "gtm" / "frozen_G2_V3"
COMPARISON = ROOT / "comparison" / "assurex_v3_model_comparison_final.csv"
COMPARISON_SUMMARY = ROOT / "comparison" / "assurex_v3_model_comparison_summary.csv"
DECISION_SUMMARY = ROOT / "comparison" / "assurex_v3_decision_engine_summary.csv"
POLICY_DIR = ROOT / "config" / "warranty_policies"

EXPECTED_FEATURES = [
    "RepairAuthorized","SerialNumberMatch","ProductModelConsistent",
    "DuplicateClaimIndicator","ContradictionIndicator","OCRConfidence",
    "ClaimReportingDelayDays","WarrantyRemainingDays",
    "ClaimReportingWithinPeriod","FaultCovered","RequiredDocumentsComplete",
    "MissingDocumentCount","ProductIdentityMatch","OCRQualityBand",
]
EXPECTED_CONSISTENCY = {
    "Strong Match":126,
    "Acceptable Match":52,
    "Weak Match":14,
    "Model Disagreement":29,
    "Uncertain Result":4,
}
EXPECTED_DECISIONS = {
    "Likely Valid":69,
    "Likely Invalid":22,
    "Manual Review Required":134,
}
REQUIRED_GTM_FILES = [
    "model.json","weights.bin","metadata.json","g2_card_features_v3.json","SHA256SUMS.txt"
]

def check(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print("PASS:", msg)

def metrics(path):
    df = pd.read_csv(path)
    return {str(r["Metric"]): float(r["Value"]) for _, r in df.iterrows()}

def main():
    print("=" * 72)
    print("ASSUREX V3 ML VALIDATION")
    print("=" * 72)

    check(PYTHON_MODEL.is_file(), "Python frozen model exists")
    check(FEATURES.is_file(), "Frozen Python feature file exists")

    fdf = pd.read_csv(FEATURES)
    selected = (
        fdf[fdf["Selected"].astype(str).str.lower().eq("true")]
        .sort_values("FrozenOrder")["Feature"].astype(str).tolist()
    )
    check(selected == EXPECTED_FEATURES, "Frozen 14-feature order is exact")

    for name in REQUIRED_GTM_FILES:
        check((GTM_DIR / name).is_file(), f"GTM artifact exists: {name}")

    manifest_lines = [
        x.strip()
        for x in (GTM_DIR / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]
    verified = 0
    for filename in [x for x in REQUIRED_GTM_FILES if x != "SHA256SUMS.txt"]:
        fp = GTM_DIR / filename
        actual = hashlib.sha256(fp.read_bytes()).hexdigest().lower()
        matches = [
            line for line in manifest_lines
            if filename in line and actual in line.lower()
        ]
        check(bool(matches), f"GTM SHA256 matches: {filename}")
        verified += 1
    check(verified >= 3, "GTM checksum manifest verified")

    py = pd.read_csv(PYTHON_PRED)
    gtm = pd.read_csv(GTM_PRED)
    check(len(py) == 225, "Python Test predictions = 225")
    check(len(gtm) == 225, "GTM Test predictions = 225")
    check(py["ClaimID"].is_unique, "Python Test ClaimIDs unique")
    check(gtm["ClaimID"].is_unique, "GTM Test ClaimIDs unique")
    check(set(py["ClaimID"]) == set(gtm["ClaimID"]), "Python/GTM locked Test IDs identical")

    df = pd.read_csv(COMPARISON)
    check(len(df) == 225, "Final comparison = 225 claims")
    check(df["ClaimID"].is_unique, "Final comparison ClaimIDs unique")
    check(int((df["PredictedClassMatch"] == "YES").sum()) == 196, "Prediction matches = 196")
    check(int((df["PredictedClassMatch"] == "NO").sum()) == 29, "Prediction disagreements = 29")

    c = df["ModelConsistencyStatus"].value_counts().to_dict()
    for label, n in EXPECTED_CONSISTENCY.items():
        check(int(c.get(label, 0)) == n, f"{label} = {n}")

    d = df["FinalApplicationDecision"].value_counts().to_dict()
    for label, n in EXPECTED_DECISIONS.items():
        check(int(d.get(label, 0)) == n, f"{label} = {n}")

    reg = df[df["ClaimID"].isin(["CLM01148", "CLM01188"])]
    check(len(reg) == 2, "Both regression claims exist")
    check(set(reg["FinalApplicationDecision"]) == {"Manual Review Required"},
          "Regression claims route to Manual Review Required")

    cs = metrics(COMPARISON_SUMMARY)
    ds = metrics(DECISION_SUMMARY)
    for label in EXPECTED_CONSISTENCY:
        check(int(cs[label]) == int(ds[label]), f"Comparison/Decision agree on {label}")

    policies = sorted(p for p in POLICY_DIR.glob("*.json") if p.name != "policy_index.json")
    check(len(policies) >= 3, "At least 3 warranty policy files exist")

    print("=" * 72)
    print("PASS: ASSUREX V3 ML PACKAGE VALIDATED")
    print("=" * 72)

if __name__ == "__main__":
    main()
