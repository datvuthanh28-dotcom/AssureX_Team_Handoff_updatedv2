from pathlib import Path
import hashlib
import json
import logging

import joblib
import pandas as pd


logger = logging.getLogger("model_service")

WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
ACTIVE_MODELS_PATH = WORKSPACE_ROOT / "model_tracking" / "active_models.json"

if ACTIVE_MODELS_PATH.is_file():
    try:
        ACTIVE_MODELS = json.loads(
            ACTIVE_MODELS_PATH.read_text(encoding="utf-8")
        )
    except Exception:
        ACTIVE_MODELS = {}
else:
    ACTIVE_MODELS = {}

PYTHON_MODEL_CONFIG = ACTIVE_MODELS.get("python_model", {})
GOOGLE_MODEL_CONFIG = ACTIVE_MODELS.get("google_model", {})

# Candidates for 14-feature finalized model
V3_MODEL_PATH = WORKSPACE_ROOT / "model" / "assurex_v3_final_model.joblib"
FROZEN_V3_MODEL_PATH = WORKSPACE_ROOT / "frozen_v3" / "assurex_v3_final_model.joblib"
CONFIG_MODEL_PATH = (
    WORKSPACE_ROOT / PYTHON_MODEL_CONFIG["artifact_path"]
    if PYTHON_MODEL_CONFIG.get("artifact_path")
    else None
)
LEGACY_MODEL_PATH = Path(__file__).resolve().parent / "assurex_final_model.joblib"

MODEL_PATH = None
for candidate in [V3_MODEL_PATH, FROZEN_V3_MODEL_PATH, CONFIG_MODEL_PATH, LEGACY_MODEL_PATH]:
    if candidate and candidate.is_file():
        MODEL_PATH = candidate
        break

# The 14 Features finalized during model training (V3 Gradient Boosting)
MODEL_14_FEATURES = [
    "RepairAuthorized",
    "SerialNumberMatch",
    "ProductModelConsistent",
    "DuplicateClaimIndicator",
    "ContradictionIndicator",
    "OCRConfidence",
    "ClaimReportingDelayDays",
    "WarrantyRemainingDays",
    "ClaimReportingWithinPeriod",
    "FaultCovered",
    "RequiredDocumentsComplete",
    "MissingDocumentCount",
    "ProductIdentityMatch",
    "OCRQualityBand",
]

# Legacy 22 features for backward compatibility
MODEL_FEATURES = [
    "WarrantyCardAvailable",
    "RepairReportAvailable",
    "PreviousRepair",
    "RepairCount",
    "SerialNumberMatch",
    "ProductModelConsistent",
    "DuplicateClaimIndicator",
    "ContradictionIndicator",
    "PriorClaimCount",
    "ClaimAmount",
    "OCRConfidence",
    "ClaimSubmissionChannel",
    "ClaimReportingDelayDays",
    "WarrantyRemainingDays",
    "WarrantyStatus",
    "ClaimReportingWithinPeriod",
    "FaultCovered",
    "MissingDocumentCount",
    "AvailableDocumentCount",
    "RequiredDocumentsComplete",
    "PurchaseProofAvailable",
    "HasRepairHistory",
]

model = None
model_feature_count = 14
if MODEL_PATH and MODEL_PATH.is_file():
    try:
        model = joblib.load(MODEL_PATH)
        ARTIFACT_HASH = hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()[:16]
    except Exception as e:
        logger.warning(f"Could not load model at {MODEL_PATH}: {e}")
        model = None
        ARTIFACT_HASH = "mock-model"
else:
    ARTIFACT_HASH = "mock-model"

MODEL_VERSION = PYTHON_MODEL_CONFIG.get("version", "v3-final-14feat")
MODEL_NAME = PYTHON_MODEL_CONFIG.get("name", "Gradient Boosting (14 Features)")
GOOGLE_INFERENCE_STATUS = GOOGLE_MODEL_CONFIG.get(
    "inference_status",
    "not_configured",
)


def evaluate_14_features_rule_fallback(input_data: dict) -> dict:
    """
    Deterministic rule-based evaluation based on the 14 features
    when the serialized scikit-learn model is unavailable.
    Accurately maps to ['Valid Claim', 'Invalid Claim', 'Manual Review'].
    """
    dup = str(input_data.get("DuplicateClaimIndicator", "No")).strip().lower()
    contra = str(input_data.get("ContradictionIndicator", "No")).strip().lower()
    fault_cov = str(input_data.get("FaultCovered", "Yes")).strip().lower()
    docs_comp = str(input_data.get("RequiredDocumentsComplete", "Yes")).strip().lower()
    sn_match = str(input_data.get("SerialNumberMatch", "Yes")).strip().lower()
    model_match = str(input_data.get("ProductModelConsistent", "Yes")).strip().lower()
    id_match = str(input_data.get("ProductIdentityMatch", "Yes")).strip().lower()
    rep_auth = str(input_data.get("RepairAuthorized", "Not Applicable")).strip().lower()

    try:
        w_days = float(input_data.get("WarrantyRemainingDays", 100))
    except Exception:
        w_days = 100.0

    try:
        delay = float(input_data.get("ClaimReportingDelayDays", 5))
    except Exception:
        delay = 5.0

    try:
        ocr_conf = float(input_data.get("OCRConfidence", 0.9))
    except Exception:
        ocr_conf = 0.9

    try:
        missing_docs = float(input_data.get("MissingDocumentCount", 0))
    except Exception:
        missing_docs = 0.0

    # 1. Hard Invalidation Conditions
    if dup == "yes" or contra == "yes" or w_days < 0 or fault_cov == "no":
        probs = {"Invalid Claim": 0.94, "Manual Review": 0.05, "Valid Claim": 0.01}
        return {
            "predicted_class": "Invalid Claim",
            "confidence": 0.94,
            "probabilities": probs,
        }

    # 2. Manual Review Conditions
    if (
        missing_docs > 0
        or docs_comp in {"no", "unknown"}
        or sn_match in {"no", "unknown"}
        or model_match == "no"
        or id_match == "no"
        or rep_auth == "no"
        or delay > 30
        or ocr_conf < 0.65
    ):
        probs = {"Invalid Claim": 0.10, "Manual Review": 0.88, "Valid Claim": 0.02}
        return {
            "predicted_class": "Manual Review",
            "confidence": 0.88,
            "probabilities": probs,
        }

    # 3. Valid Claim
    probs = {"Invalid Claim": 0.02, "Manual Review": 0.06, "Valid Claim": 0.92}
    return {
        "predicted_class": "Valid Claim",
        "confidence": 0.92,
        "probabilities": probs,
    }


def predict_claim(input_data: dict) -> dict:
    """
    Predict warranty claim using the 14 finalized features.
    Accepts only the finalized V3 14-feature contract.
    """
    missing_features = [feature for feature in MODEL_14_FEATURES if feature not in input_data]
    if missing_features:
        raise ValueError(f"Missing required V3 features: {missing_features}")

    # The active model always receives the frozen 14-feature contract.
    has_14_features = True

    if has_14_features:
        # Prepare 14-feature DataFrame
        row_data = {}
        for feat in MODEL_14_FEATURES:
            val = input_data.get(feat)
            if feat in {"OCRConfidence", "ClaimReportingDelayDays", "WarrantyRemainingDays", "MissingDocumentCount"}:
                try:
                    row_data[feat] = float(val) if val is not None else 0.0
                except (ValueError, TypeError):
                    row_data[feat] = 0.0
            else:
                row_data[feat] = str(val if val is not None else "Unknown")

        model_input = pd.DataFrame([row_data])

        if model is not None:
            try:
                predicted_class = model.predict(model_input)[0]
                probabilities = model.predict_proba(model_input)[0]
                class_probabilities = {
                    class_name: float(prob)
                    for class_name, prob in zip(model.classes_, probabilities)
                }
                confidence = float(max(class_probabilities.values()))

                return {
                    "predicted_class": str(predicted_class),
                    "confidence": confidence,
                    "probabilities": class_probabilities,
                    "model_name": MODEL_NAME,
                    "model_version": MODEL_VERSION,
                    "google_model": {
                        "model_name": GOOGLE_MODEL_CONFIG.get("name"),
                        "model_version": GOOGLE_MODEL_CONFIG.get("version"),
                        "inference_status": GOOGLE_INFERENCE_STATUS,
                        "prediction": None,
                        "confidence": None,
                    },
                }
            except Exception as exc:
                logger.warning(f"Inference error on model: {exc}. Using 14-feature rule fallback.")

        # Fallback to deterministic policy evaluation
        fallback = evaluate_14_features_rule_fallback(row_data)
        return {
            "predicted_class": fallback["predicted_class"],
            "confidence": fallback["confidence"],
            "probabilities": fallback["probabilities"],
            "model_name": f"{MODEL_NAME} (Policy Engine)",
            "model_version": MODEL_VERSION,
            "google_model": {
                "model_name": GOOGLE_MODEL_CONFIG.get("name"),
                "model_version": GOOGLE_MODEL_CONFIG.get("version"),
                "inference_status": GOOGLE_INFERENCE_STATUS,
                "prediction": None,
                "confidence": None,
            },
        }

    # Backward compatibility for legacy 22-feature inputs
    missing_features = [
        feature
        for feature in MODEL_FEATURES
        if feature not in input_data
    ]
    if missing_features:
        # Default missing features rather than crashing
        for mf in missing_features:
            input_data[mf] = 0 if "Count" in mf or "Amount" in mf or "Days" in mf or "Confidence" in mf else "Unknown"

    model_input = pd.DataFrame([
        {feature: input_data.get(feature) for feature in MODEL_FEATURES}
    ])

    if model is not None:
        try:
            predicted_class = model.predict(model_input)[0]
            probabilities = model.predict_proba(model_input)[0]
            class_probabilities = {
                class_name: float(probability)
                for class_name, probability in zip(model.classes_, probabilities)
            }
            confidence = max(class_probabilities.values())

            return {
                "predicted_class": predicted_class,
                "confidence": confidence,
                "probabilities": class_probabilities,
                "model_name": MODEL_NAME,
                "model_version": MODEL_VERSION,
                "google_model": {
                    "model_name": GOOGLE_MODEL_CONFIG.get("name"),
                    "model_version": GOOGLE_MODEL_CONFIG.get("version"),
                    "inference_status": GOOGLE_INFERENCE_STATUS,
                    "prediction": None,
                    "confidence": None,
                },
            }
        except Exception:
            pass

    # Generic fallback
    return {
        "predicted_class": "Manual Review",
        "confidence": 0.85,
        "probabilities": {"Valid Claim": 0.05, "Invalid Claim": 0.10, "Manual Review": 0.85},
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "google_model": {
            "model_name": GOOGLE_MODEL_CONFIG.get("name"),
            "model_version": GOOGLE_MODEL_CONFIG.get("version"),
            "inference_status": GOOGLE_INFERENCE_STATUS,
            "prediction": None,
            "confidence": None,
        },
    }
