from pathlib import Path
import hashlib
import json

import joblib
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent

MODEL_PATH = (
    ROOT
    / "model/assurex_v3_final_model.joblib"
)

FEATURES_PATH = (
    ROOT
    / "model/assurex_v3_final_features.csv"
)

FREEZE_PATH = (
    ROOT
    / "data/audit"
    / "assurex_v3_model_freeze_manifest.json"
)

FINAL_MANIFEST_PATH = (
    ROOT
    / "data/audit"
    / "assurex_v3_final_evaluation_manifest.json"
)

PRED_PATH = (
    ROOT
    / "data/final_evaluation_v3"
    / "assurex_v3_test_predictions.csv"
)

TEST_PATH = (
    ROOT
    / "data/test/assurex_v3_test.csv"
)

IMPORTANCE_PATH = (
    ROOT
    / "data/final_evaluation_v3"
    / "assurex_v3_final_feature_importance.csv"
)

SANITY_PATH = (
    ROOT
    / "data/audit"
    / "assurex_v3_model_sanity_check.json"
)

REGRESSION_PATH = (
    ROOT
    / "data/audit"
    / "assurex_v3_decision_engine_regression_cases.csv"
)


def sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            block = f.read(1024 * 1024)

            if not block:
                break

            h.update(block)

    return h.hexdigest()


def aggregate_feature_importance(
    pipeline,
):
    prep = pipeline.named_steps[
        "preprocessor"
    ]

    model = pipeline.named_steps[
        "model"
    ]

    raw_importance = (
        model.feature_importances_
    )

    rows = []
    cursor = 0

    for name, transformer, columns in (
        prep.transformers_
    ):
        if (
            name == "remainder"
            and transformer == "drop"
        ):
            continue

        columns = list(columns)

        if name == "numeric":

            for column in columns:
                value = float(
                    raw_importance[cursor]
                )

                rows.append({
                    "Feature":
                        column,
                    "FinalImportance":
                        value,
                })

                cursor += 1

        elif name == "categorical":

            encoder = (
                transformer
                .named_steps["encoder"]
            )

            for column, categories in zip(
                columns,
                encoder.categories_,
            ):
                count = len(categories)

                value = float(
                    raw_importance[
                        cursor:
                        cursor + count
                    ].sum()
                )

                rows.append({
                    "Feature":
                        column,
                    "FinalImportance":
                        value,
                })

                cursor += count

    if cursor != len(
        raw_importance
    ):
        raise RuntimeError(
            "Transformed feature importance "
            "mapping is incomplete."
        )

    result = pd.DataFrame(rows)

    result = (
        result
        .groupby(
            "Feature",
            as_index=False,
        )["FinalImportance"]
        .sum()
        .sort_values(
            "FinalImportance",
            ascending=False,
        )
        .reset_index(drop=True)
    )

    total = result[
        "FinalImportance"
    ].sum()

    result[
        "ImportancePercent"
    ] = np.where(
        total > 0,
        result[
            "FinalImportance"
        ]
        / total
        * 100,
        0,
    )

    return result


def main():
    print("=" * 72)
    print("ASSUREX V3 - FINAL PYTHON MODEL AUDIT")
    print("=" * 72)

    freeze = json.loads(
        FREEZE_PATH.read_text(
            encoding="utf-8"
        )
    )

    final_manifest = json.loads(
        FINAL_MANIFEST_PATH.read_text(
            encoding="utf-8"
        )
    )

    model_hash = sha256(
        MODEL_PATH
    )

    assert (
        model_hash
        == freeze["model_sha256"]
    )

    assert (
        final_manifest[
            "model_changed_after_test"
        ]
        is False
    )

    features_df = pd.read_csv(
        FEATURES_PATH
    )

    features = (
        features_df[
            "Feature"
        ]
        .astype(str)
        .tolist()
    )

    assert len(features) == 14
    assert len(set(features)) == 14

    forbidden = [
        f
        for f in features
        if (
            f == "ClaimClass"
            or f == "ClaimID"
            or "truth"
            in f.casefold()
            or "target"
            in f.casefold()
            or "label"
            in f.casefold()
        )
    ]

    assert not forbidden, forbidden

    pipeline = joblib.load(
        MODEL_PATH
    )

    importance = (
        aggregate_feature_importance(
            pipeline
        )
    )

    assert set(
        importance["Feature"]
    ) == set(features)

    importance.to_csv(
        IMPORTANCE_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    pred = pd.read_csv(
        PRED_PATH
    )

    assert len(pred) == 225

    errors = pred[
        pred["Actual"]
        != pred["Predicted"]
    ].copy()

    assert len(errors) == 2

    probability_columns = [
        c
        for c in pred.columns
        if c.startswith(
            "Probability_"
        )
    ]

    probability_sum = (
        pred[
            probability_columns
        ]
        .sum(axis=1)
    )

    assert np.allclose(
        probability_sum,
        1.0,
        atol=1e-6,
    )

    assert abs(
        float(
            final_manifest[
                "test_macro_f1"
            ]
        )
        - 0.991110
    ) < 0.00001

    # --------------------------------------------------------
    # Decision Engine regression cases
    # Read-only: NEVER used to retrain Python model.
    # --------------------------------------------------------

    test = pd.read_csv(
        TEST_PATH
    )

    regression = test[
        test["ClaimID"].isin(
            errors["ClaimID"]
        )
    ].copy()

    regression = regression.merge(
        errors[
            [
                "ClaimID",
                "Actual",
                "Predicted",
                "Confidence",
            ]
        ],
        on="ClaimID",
        how="left",
        suffixes=(
            "",
            "_Prediction",
        ),
    )

    def repair_report_state(value):
        if pd.isna(value):
            return "Unknown"

        text = str(value).strip()

        if not text:
            return "Unknown"

        return text

    regression[
        "RepairReportState"
    ] = regression[
        "RepairReportAvailable"
    ].apply(
        repair_report_state
    )

    regression[
        "DecisionEngineRegressionTrigger"
    ] = np.where(
        (
            regression[
                "PreviousRepair"
            ].eq("Yes")
            &
            regression[
                "RepairReportState"
            ].eq("Unknown")
        ),
        (
            "Manual Review: previous repair exists "
            "but repair report availability is unknown"
        ),
        "Review other rule trigger",
    )

    regression[
        "ExpectedDecisionEngineOutcome"
    ] = "Manual Review"

    keep = [
        "ClaimID",
        "ClaimClass",
        "Predicted",
        "Confidence",
        "PreviousRepair",
        "RepairAuthorized",
        "RepairReportAvailable",
        "RepairReportState",
        "RequiredDocumentsComplete",
        "MissingDocumentCount",
        "CriticalDocumentMissing",
        "DecisionEngineRegressionTrigger",
        "ExpectedDecisionEngineOutcome",
    ]

    regression[
        [
            c
            for c in keep
            if c in regression.columns
        ]
    ].to_csv(
        REGRESSION_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    sanity = {
        "status":
            "PASS",

        "model_sha256":
            model_hash,

        "model_matches_freeze_hash":
            True,

        "model_changed_after_test":
            False,

        "frozen_feature_count":
            len(features),

        "forbidden_features":
            forbidden,

        "test_predictions":
            len(pred),

        "test_errors":
            len(errors),

        "test_macro_f1":
            final_manifest[
                "test_macro_f1"
            ],

        "probabilities_sum_to_one":
            True,

        "decision_engine_regression_cases":
            errors[
                "ClaimID"
            ].tolist(),

        "python_model_modified":
            False,
    }

    SANITY_PATH.write_text(
        json.dumps(
            sanity,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("Final feature importance:")
    print(
        importance.to_string(
            index=False
        )
    )

    print()
    print(
        "Frozen feature count       :",
        len(features),
    )

    print(
        "Test errors                :",
        len(errors),
    )

    print(
        "Model hash unchanged       : YES"
    )

    print(
        "Probability sanity         : PASS"
    )

    print(
        "Target/truth leakage       : NONE"
    )

    print(
        "Regression cases captured  :",
        ", ".join(
            errors[
                "ClaimID"
            ].tolist()
        ),
    )

    print()
    print(
        "PASS - FINAL PYTHON MODEL SANITY CHECK"
    )

    print()
    print("Created:")
    print(" -", IMPORTANCE_PATH)
    print(" -", SANITY_PATH)
    print(" -", REGRESSION_PATH)


if __name__ == "__main__":
    main()
