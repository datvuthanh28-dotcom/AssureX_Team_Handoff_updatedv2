from __future__ import annotations

from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "assurex_web" / "backend"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.ml.gtm_service import predict_gtm_claim

test_path = ROOT / "data" / "test" / "assurex_v3_test.csv"
pred_path = (
    ROOT / "data" / "final_evaluation_v3" / "gtm"
    / "assurex_v3_gtm_g2_final_test_predictions.csv"
)

test_df = pd.read_csv(test_path)
pred_df = pd.read_csv(pred_path)

row = test_df.iloc[0]
claim_id = str(row["ClaimID"])
context = row.to_dict()

runtime = predict_gtm_claim(
    raw_input=context,
    model_features=context,
    rule_data=context,
    derived=context,
)

expected_row = pred_df[
    pred_df["ClaimID"].astype(str) == claim_id
].iloc[0]

expected_pred = str(expected_row["PredictedClass"])
expected_conf = float(expected_row["Confidence"])

print("=" * 72)
print("ASSUREX V3 - GTM G2 RUNTIME SMOKE TEST")
print("=" * 72)
print("ClaimID        :", claim_id)
print("Expected class :", expected_pred)
print("Runtime class  :", runtime.get("predicted_class"))
print("Expected conf  :", round(expected_conf, 6))
print("Runtime conf   :", round(float(runtime.get("confidence") or 0), 6))
print("Runtime status :", runtime.get("inference_status"))

if runtime.get("inference_status") != "connected":
    raise SystemExit(
        "FAIL: GTM runtime inference did not connect.\n"
        + str(runtime.get("error"))
    )

if runtime.get("predicted_class") != expected_pred:
    raise SystemExit(
        "FAIL: runtime class does not match frozen Test prediction."
    )

diff = abs(float(runtime["confidence"]) - expected_conf)

print("Confidence diff:", round(diff, 6))

if diff > 0.05:
    raise SystemExit(
        "FAIL: confidence difference > 0.05"
    )

print("PASS: GTM G2 V3 runtime matches frozen Test prediction.")
