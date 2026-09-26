from pathlib import Path
import hashlib

import joblib
import pandas as pd


MODEL_PATH = Path(__file__).resolve().parent / "assurex_final_model.joblib"


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


model = joblib.load(MODEL_PATH)
MODEL_VERSION = hashlib.sha256(
    MODEL_PATH.read_bytes()
).hexdigest()[:16]


def predict_claim(input_data: dict) -> dict:
    missing_features = [
        feature
        for feature in MODEL_FEATURES
        if feature not in input_data
    ]

    if missing_features:
        raise ValueError(
            f"Missing required features: {missing_features}"
        )

    model_input = pd.DataFrame(
        [
            {
                feature: input_data[feature]
                for feature in MODEL_FEATURES
            }
        ]
    )

    predicted_class = model.predict(model_input)[0]

    probabilities = model.predict_proba(model_input)[0]

    class_probabilities = {
        class_name: float(probability)
        for class_name, probability in zip(
            model.classes_,
            probabilities,
        )
    }

    confidence = max(class_probabilities.values())

    return {
        "predicted_class": predicted_class,
        "confidence": confidence,
        "probabilities": class_probabilities,
        "model_name": "Python Gradient Boosting",
        "model_version": MODEL_VERSION,
    }
