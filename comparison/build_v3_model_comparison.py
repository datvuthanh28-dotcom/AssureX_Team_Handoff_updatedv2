from __future__ import annotations

from pathlib import Path
import json
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PYTHON_PRED = (
    PROJECT_ROOT
    / "data"
    / "final_evaluation_v3"
    / "assurex_v3_test_predictions.csv"
)

GTM_PRED = (
    PROJECT_ROOT
    / "data"
    / "final_evaluation_v3"
    / "gtm"
    / "assurex_v3_gtm_g2_final_test_predictions.csv"
)

TEST_DATA = (
    PROJECT_ROOT
    / "data"
    / "test"
    / "assurex_v3_test.csv"
)

CONFIG_PATH = (
    PROJECT_ROOT
    / "config"
    / "decision_engine_v3.json"
)

OUT_DIR = PROJECT_ROOT / "comparison"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_PATH = OUT_DIR / "assurex_v3_model_comparison_base.csv"
SUMMARY_PATH = OUT_DIR / "assurex_v3_model_comparison_summary.csv"

EXPECTED_ROWS = 225

RULE_COLUMNS = [
    "ProductCategory",
    "WarrantyStatus",
    "WarrantyRemainingDays",
    "ComponentWarrantyEligible",
    "FaultCovered",
    "ClaimReportingDelayDays",
    "ClaimReportingWithinPeriod",
    "RequiredDocumentsComplete",
    "MissingDocumentCount",
    "CriticalDocumentMissing",
    "PreviousRepair",
    "RepairAuthorized",
    "RepairReportAvailable",
    "SerialNumberMatch",
    "ProductIdentityMatch",
    "ProductModelConsistent",
    "DuplicateClaimIndicator",
    "DocumentDuplicateIndicator",
    "ContradictionIndicator",
    "OCRConfidence",
]


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return pd.read_csv(path)


def require_columns(
    df: pd.DataFrame,
    columns: list[str],
    name: str,
) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(
            f"{name} missing columns: {missing}"
        )


def load_thresholds() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Missing config: {CONFIG_PATH}"
        )

    with CONFIG_PATH.open(
        "r",
        encoding="utf-8",
    ) as f:
        config = json.load(f)

    return config["comparison_thresholds"]


def consistency_status(
    row: pd.Series,
    thresholds: dict,
) -> str:
    py_conf = float(row["PythonTopConfidence"])
    gtm_conf = float(row["GTMTopConfidence"])
    diff = float(row["TopConfidenceDifference"])

    min_confidence = float(
        thresholds["minimum_confidence"]
    )

    # Different predictions always count as
    # Model Disagreement.
    if row["PredictedClassMatch"] != "YES":
        return "Model Disagreement"

    if (
        py_conf < min_confidence
        or gtm_conf < min_confidence
    ):
        return "Uncertain Result"

    min_conf = min(py_conf, gtm_conf)

    if (
        min_conf
        >= float(
            thresholds[
                "strong_match_min_confidence"
            ]
        )
        and diff
        <= float(
            thresholds[
                "strong_match_max_confidence_difference"
            ]
        )
    ):
        return "Strong Match"

    if (
        min_conf
        >= float(
            thresholds[
                "acceptable_match_min_confidence"
            ]
        )
        and diff
        <= float(
            thresholds[
                "acceptable_match_max_confidence_difference"
            ]
        )
    ):
        return "Acceptable Match"

    return "Weak Match"


def main() -> None:
    print("=" * 78)
    print(
        "ASSUREX V3 - PYTHON vs GTM "
        "LOCKED TEST COMPARISON"
    )
    print("=" * 78)

    thresholds = load_thresholds()

    py = read_csv(PYTHON_PRED)
    gtm = read_csv(GTM_PRED)
    test = read_csv(TEST_DATA)

    # Actual Python CSV schema
    require_columns(
        py,
        [
            "ClaimID",
            "Actual",
            "Predicted",
            "Correct",
            "Confidence",
            "Probability_Invalid_Claim",
            "Probability_Manual_Review",
            "Probability_Valid_Claim",
        ],
        "Python predictions",
    )

    # Actual GTM CSV schema
    require_columns(
        gtm,
        [
            "ClaimID",
            "ActualClass",
            "CardFilename",
            "PredictedClass",
            "P_Invalid_Claim",
            "P_Manual_Review",
            "P_Valid_Claim",
            "Confidence",
            "Correct",
        ],
        "GTM predictions",
    )

    require_columns(
        test,
        ["ClaimID", "ClaimClass"] + RULE_COLUMNS,
        "Locked test dataset",
    )

    # -------------------------------------------------
    # Integrity checks
    # -------------------------------------------------

    if len(py) != EXPECTED_ROWS:
        raise ValueError(
            f"Python predictions: expected "
            f"{EXPECTED_ROWS}, found {len(py)}"
        )

    if len(gtm) != EXPECTED_ROWS:
        raise ValueError(
            f"GTM predictions: expected "
            f"{EXPECTED_ROWS}, found {len(gtm)}"
        )

    if len(test) != EXPECTED_ROWS:
        raise ValueError(
            f"Test dataset: expected "
            f"{EXPECTED_ROWS}, found {len(test)}"
        )

    for name, df in [
        ("Python", py),
        ("GTM", gtm),
        ("Test", test),
    ]:
        if not df["ClaimID"].is_unique:
            raise ValueError(
                f"{name} ClaimID is not unique."
            )

    py_ids = set(py["ClaimID"])
    gtm_ids = set(gtm["ClaimID"])
    test_ids = set(test["ClaimID"])

    if py_ids != gtm_ids:
        raise ValueError(
            "Python/GTM ClaimID sets do not match. "
            f"Python-only={len(py_ids - gtm_ids)}, "
            f"GTM-only={len(gtm_ids - py_ids)}"
        )

    if py_ids != test_ids:
        raise ValueError(
            "Prediction/Test ClaimID sets do not match. "
            f"Prediction-only={len(py_ids - test_ids)}, "
            f"Test-only={len(test_ids - py_ids)}"
        )

    # -------------------------------------------------
    # Normalize Python columns
    # -------------------------------------------------

    py2 = py.rename(
        columns={
            "Actual":
                "PythonActualClass",
            "Predicted":
                "PythonPredictedClass",
            "Confidence":
                "PythonTopConfidence",
            "Probability_Invalid_Claim":
                "PythonP_InvalidClaim",
            "Probability_Manual_Review":
                "PythonP_ManualReview",
            "Probability_Valid_Claim":
                "PythonP_ValidClaim",
            "Correct":
                "PythonCorrect",
        }
    )

    # -------------------------------------------------
    # Normalize GTM columns
    # -------------------------------------------------

    gtm2 = gtm.rename(
        columns={
            "ActualClass":
                "GTMActualClass",
            "PredictedClass":
                "GTMPredictedClass",
            "Confidence":
                "GTMTopConfidence",
            "P_Invalid_Claim":
                "GTMP_InvalidClaim",
            "P_Manual_Review":
                "GTMP_ManualReview",
            "P_Valid_Claim":
                "GTMP_ValidClaim",
            "Correct":
                "GTMCorrect",
        }
    )

    # -------------------------------------------------
    # Merge predictions
    # -------------------------------------------------

    comparison = py2.merge(
        gtm2,
        on="ClaimID",
        how="inner",
        validate="one_to_one",
    )

    if len(comparison) != EXPECTED_ROWS:
        raise ValueError(
            f"Merged comparison expected "
            f"{EXPECTED_ROWS}, found "
            f"{len(comparison)}"
        )

    # -------------------------------------------------
    # Validate actual labels
    # -------------------------------------------------

    if not (
        comparison["PythonActualClass"].astype(str)
        == comparison["GTMActualClass"].astype(str)
    ).all():
        bad = comparison.loc[
            comparison[
                "PythonActualClass"
            ].astype(str)
            != comparison[
                "GTMActualClass"
            ].astype(str),
            [
                "ClaimID",
                "PythonActualClass",
                "GTMActualClass",
            ],
        ]

        raise ValueError(
            "Actual class mismatch "
            "between Python and GTM:\n"
            + bad.head(20).to_string(index=False)
        )

    comparison["ActualClass"] = (
        comparison["PythonActualClass"]
    )

    # -------------------------------------------------
    # Compare predictions
    # -------------------------------------------------

    comparison["PredictedClassMatch"] = (
        comparison[
            "PythonPredictedClass"
        ].astype(str)
        ==
        comparison[
            "GTMPredictedClass"
        ].astype(str)
    ).map(
        {
            True: "YES",
            False: "NO",
        }
    )

    comparison[
        "TopConfidenceDifference"
    ] = (
        comparison[
            "PythonTopConfidence"
        ].astype(float)
        -
        comparison[
            "GTMTopConfidence"
        ].astype(float)
    ).abs()

    comparison[
        "ModelConsistencyStatus"
    ] = comparison.apply(
        lambda row: consistency_status(
            row,
            thresholds,
        ),
        axis=1,
    )

    # -------------------------------------------------
    # Merge exact locked Test rule data
    # -------------------------------------------------

    test_rules = test[
        ["ClaimID", "ClaimClass"] + RULE_COLUMNS
    ].copy()

    comparison = comparison.merge(
        test_rules,
        on="ClaimID",
        how="left",
        validate="one_to_one",
    )

    if not (
        comparison["ActualClass"].astype(str)
        ==
        comparison["ClaimClass"].astype(str)
    ).all():
        raise ValueError(
            "ActualClass does not match "
            "locked Test ClaimClass."
        )

    comparison = comparison.drop(
        columns=["ClaimClass"]
    )

    # -------------------------------------------------
    # Final ordering
    # -------------------------------------------------

    ordered = [
        "ClaimID",
        "ActualClass",

        "PythonPredictedClass",
        "PythonP_ValidClaim",
        "PythonP_InvalidClaim",
        "PythonP_ManualReview",
        "PythonTopConfidence",

        "CardFilename",

        "GTMPredictedClass",
        "GTMP_ValidClaim",
        "GTMP_InvalidClaim",
        "GTMP_ManualReview",
        "GTMTopConfidence",

        "PredictedClassMatch",
        "TopConfidenceDifference",
        "ModelConsistencyStatus",
    ] + RULE_COLUMNS

    comparison = (
        comparison[ordered]
        .sort_values("ClaimID")
        .reset_index(drop=True)
    )

    comparison.to_csv(
        OUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    # -------------------------------------------------
    # Summary
    # -------------------------------------------------

    consistency_order = [
        "Strong Match",
        "Acceptable Match",
        "Weak Match",
        "Model Disagreement",
        "Uncertain Result",
    ]

    summary_rows = [
        {
            "Metric": "Claims",
            "Value": len(comparison),
        },
        {
            "Metric": "Prediction matches",
            "Value": int(
                (
                    comparison[
                        "PredictedClassMatch"
                    ]
                    == "YES"
                ).sum()
            ),
        },
        {
            "Metric": "Prediction disagreements",
            "Value": int(
                (
                    comparison[
                        "PredictedClassMatch"
                    ]
                    == "NO"
                ).sum()
            ),
        },
        {
            "Metric":
                "Mean top-confidence difference",
            "Value": float(
                comparison[
                    "TopConfidenceDifference"
                ].mean()
            ),
        },
    ]

    for status in consistency_order:
        summary_rows.append(
            {
                "Metric": status,
                "Value": int(
                    (
                        comparison[
                            "ModelConsistencyStatus"
                        ]
                        == status
                    ).sum()
                ),
            }
        )

    summary = pd.DataFrame(summary_rows)

    summary.to_csv(
        SUMMARY_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print(
        f"Claims compared           : "
        f"{len(comparison)}"
    )

    print(
        "Prediction matches        :",
        int(
            (
                comparison[
                    "PredictedClassMatch"
                ]
                == "YES"
            ).sum()
        ),
    )

    print(
        "Prediction disagreements  :",
        int(
            (
                comparison[
                    "PredictedClassMatch"
                ]
                == "NO"
            ).sum()
        ),
    )

    print(
        "Mean confidence difference:",
        f"{comparison['TopConfidenceDifference'].mean():.6f}",
    )

    print()
    print("Consistency:")
    print(
        comparison[
            "ModelConsistencyStatus"
        ]
        .value_counts()
        .reindex(
            consistency_order,
            fill_value=0,
        )
        .to_string()
    )

    print()
    print("PASS: Python/GTM/Test ClaimIDs identical")
    print("PASS: Actual classes identical")
    print("PASS: Locked Test only")
    print("PASS: Configurable comparison thresholds")
    print()

    print("Created:")
    print(f"  {OUT_PATH}")
    print(f"  {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
