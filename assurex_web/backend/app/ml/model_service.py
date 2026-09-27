from pathlib import Path
import hashlib
import json

import joblib
import pandas as pd


WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
LEGACY_MODEL_PATH = Path(__file__).resolve().parent / "assurex_final_model.joblib"
ACTIVE_MODELS_PATH = WORKSPACE_ROOT / "model_tracking" / "active_models.json"

if ACTIVE_MODELS_PATH.is_file():
    ACTIVE_MODELS = json.loads(
        ACTIVE_MODELS_PATH.read_text(encoding="utf-8")
    )
else:
    ACTIVE_MODELS = {}

PYTHON_MODEL_CONFIG = ACTIVE_MODELS.get("python_model", {})
GOOGLE_MODEL_CONFIG = ACTIVE_MODELS.get("google_model", {})

MODEL_PATH = (
    WORKSPACE_ROOT / PYTHON_MODEL_CONFIG["artifact_path"]
    if PYTHON_MODEL_CONFIG.get("artifact_path")
    else LEGACY_MODEL_PATH
)

MODEL_FEATURES = [
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

model = joblib.load(MODEL_PATH)

ARTIFACT_HASH = hashlib.sha256(
    MODEL_PATH.read_bytes()
).hexdigest()[:16]

MODEL_VERSION = PYTHON_MODEL_CONFIG.get("version", ARTIFACT_HASH)
MODEL_NAME = PYTHON_MODEL_CONFIG.get("name", "Python Gradient Boosting V3")

GOOGLE_INFERENCE_STATUS = GOOGLE_MODEL_CONFIG.get(
    "inference_status",
    GOOGLE_MODEL_CONFIG.get("runtime_status", "not_configured"),
)


def predict_claim(input_data: dict) -> dict:
    missing_features = [
        feature for feature in MODEL_FEATURES
        if feature not in input_data
    ]

    if missing_features:
        raise ValueError(
            f"Missing required V3 features: {missing_features}"
        )

    model_input = pd.DataFrame(
        [{
            feature: input_data[feature]
            for feature in MODEL_FEATURES
        }],
        columns=MODEL_FEATURES,
    )

    predicted_class = model.predict(model_input)[0]
    probabilities = model.predict_proba(model_input)[0]

    class_probabilities = {
        str(class_name): float(probability)
        for class_name, probability in zip(
            model.classes_,
            probabilities,
        )
    }

    confidence = max(class_probabilities.values())

    return {
        "predicted_class": str(predicted_class),
        "confidence": float(confidence),
        "probabilities": class_probabilities,
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "feature_count": len(MODEL_FEATURES),
        "google_model": {
            "model_name": GOOGLE_MODEL_CONFIG.get("name"),
            "model_version": GOOGLE_MODEL_CONFIG.get("version"),
            "inference_status": GOOGLE_INFERENCE_STATUS,
            "prediction": None,
            "confidence": None,
        },
    }
