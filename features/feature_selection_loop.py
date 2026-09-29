from __future__ import annotations
from pathlib import Path
import json
import warnings
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRAIN_PATH = PROJECT_ROOT / "data" / "train" / "assurex_train.csv"
VALIDATION_PATH = PROJECT_ROOT / "data" / "validation" / "assurex_validation.csv"
OUT_DIR = PROJECT_ROOT / "data" / "feature_selection"
AUDIT_DIR = PROJECT_ROOT / "data" / "audit"
MODEL_DIR = PROJECT_ROOT / "model"
for folder in [OUT_DIR, AUDIT_DIR, MODEL_DIR]:
    folder.mkdir(parents=True, exist_ok=True)
HISTORY_PATH = OUT_DIR / "feature_selection_history.csv"
IMPORTANCE_PATH = OUT_DIR / "feature_importance_by_iteration.csv"
SELECTED_PATH = OUT_DIR / "selected_features.csv"
REJECTED_PATH = OUT_DIR / "rejected_removals.csv"
FINAL_IMPORTANCE_PATH = OUT_DIR / "selected_feature_importance.csv"
MANIFEST_PATH = AUDIT_DIR / "feature_selection_manifest.json"
SELECTOR_MODEL_PATH = MODEL_DIR / "feature_selector_model.joblib"
TARGET = "ClaimClass"
ALIGNMENT_COLUMNS = {"ClaimID"}
RANDOM_SEED = 20260925
IMPORTANCE_CANDIDATE_THRESHOLD = 0.002
LOCAL_F1_TOLERANCE = 0.003
BASELINE_F1_TOLERANCE = 0.005
MAX_ACCEPTED_REMOVALS = 25
MAX_TOTAL_ATTEMPTS = 60
PERMUTATION_REPEATS = 8
KNOWN_NOISE_FEATURES = {
    "BrowserFamily",
    "SubmissionMinute",
    "UiTheme",
    "RandomScore",
}
REDUNDANCY_GROUPS = [
    {"PreviousReplacement", "ReplacementWithinWarranty"},
    {"RepairReportAvailable", "PreviousRepair"},
    {"PreviousRepair", "RepairAuthorized"},
    {"RepairCount", "PreviousRepairCost"},
    {"ReceiptAvailable", "PurchaseProofAvailable"},
    {"PreviousRepair", "HasRepairHistory"},
    {"PreviousReplacement", "HasPreviousReplacement"},
    {"WarrantyStatus", "WarrantyRemainingDays"},
    {"ClaimReportingWithinPeriod", "ClaimReportingDelayDays"},
    {"DamageType", "FaultCovered"},
    {"MissingDocumentCount", "AvailableDocumentCount"},
    {"RequiredDocumentsComplete", "MissingDocumentCount"},
]


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        keep_default_na=False,
        na_values=[""],
    )


def validate_inputs(train: pd.DataFrame, validation: pd.DataFrame) -> None:
    for name, df in [("Train", train), ("Validation", validation)]:
        if df.empty:
            raise ValueError(f"{name} dataset is empty.")
        if TARGET not in df.columns:
            raise ValueError(f"{name}: missing target {TARGET}.")
        if "ClaimID" not in df.columns:
            raise ValueError(f"{name}: missing ClaimID.")
        if df["ClaimID"].duplicated().any():
            raise ValueError(f"{name}: duplicate ClaimID found.")
    overlap = set(train["ClaimID"]) & set(validation["ClaimID"])
    if overlap:
        raise ValueError(
            f"Train/Validation ClaimID overlap detected: {len(overlap)}."
        )
    if set(train.columns) != set(validation.columns):
        raise ValueError("Train and Validation schemas do not match.")


def predictor_columns(df: pd.DataFrame) -> list[str]:
    return [
        c for c in df.columns
        if c != TARGET and c not in ALIGNMENT_COLUMNS
    ]


def infer_feature_types(
    train: pd.DataFrame,
    features: list[str],
) -> tuple[list[str], list[str]]:
    numeric_features = []
    categorical_features = []
    for column in features:
        series = train[column]
        non_missing = int(series.notna().sum())
        if non_missing == 0:
            categorical_features.append(column)
            continue
        numeric = pd.to_numeric(series, errors="coerce")
        numeric_ratio = float(numeric.notna().sum()) / float(non_missing)
        if numeric_ratio >= 0.95:
            numeric_features.append(column)
        else:
            categorical_features.append(column)
    return numeric_features, categorical_features


def build_pipeline(
    train: pd.DataFrame,
    features: list[str],
) -> Pipeline:
    numeric_features, categorical_features = infer_feature_types(
        train,
        features,
    )
    numeric_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    categorical_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        (
            "onehot",
            OneHotEncoder(
                handle_unknown="ignore",
                sparse_output=False,
            ),
        ),
    ])
    transformers = []
    if numeric_features:
        transformers.append(
            ("num", numeric_pipe, numeric_features)
        )
    if categorical_features:
        transformers.append(
            ("cat", categorical_pipe, categorical_features)
        )
    preprocessor = ColumnTransformer(
        transformers=transformers,
        remainder="drop",
    )
    model = GradientBoostingClassifier(
        n_estimators=150,
        learning_rate=0.05,
        max_depth=3,
        random_state=RANDOM_SEED,
    )
    return Pipeline([
        ("preprocessor", preprocessor),
        ("model", model),
    ])


def evaluate_pipeline(
    pipeline: Pipeline,
    X_validation: pd.DataFrame,
    y_validation: pd.Series,
) -> tuple[float, float]:
    pred = pipeline.predict(X_validation)
    accuracy = accuracy_score(
        y_validation,
        pred,
    )
    macro_f1 = f1_score(
        y_validation,
        pred,
        average="macro",
    )
    return float(accuracy), float(macro_f1)


def fit_and_evaluate(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    features: list[str],
) -> tuple[Pipeline, float, float]:
    pipeline = build_pipeline(
        train,
        features,
    )
    pipeline.fit(
        train[features],
        train[TARGET],
    )
    accuracy, macro_f1 = evaluate_pipeline(
        pipeline,
        validation[features],
        validation[TARGET],
    )
    return pipeline, accuracy, macro_f1


def compute_importance(
    pipeline: Pipeline,
    validation: pd.DataFrame,
    features: list[str],
    iteration: int,
) -> pd.DataFrame:
    result = permutation_importance(
        pipeline,
        validation[features],
        validation[TARGET],
        scoring="f1_macro",
        n_repeats=PERMUTATION_REPEATS,
        random_state=RANDOM_SEED + iteration,
        n_jobs=-1,
    )
    frame = pd.DataFrame({
        "Iteration": iteration,
        "Feature": features,
        "ImportanceMean": result.importances_mean,
        "ImportanceStd": result.importances_std,
    })
    frame["ImportanceLower"] = (
        frame["ImportanceMean"]
        - frame["ImportanceStd"]
    )
    frame["CandidateWeak"] = (
        frame["ImportanceMean"]
        <= IMPORTANCE_CANDIDATE_THRESHOLD
    )
    frame["KnownNoise"] = frame["Feature"].isin(
        KNOWN_NOISE_FEATURES
    )
    redundancy_features = set().union(*REDUNDANCY_GROUPS)
    frame["KnownRedundancyCandidate"] = frame["Feature"].isin(
        redundancy_features
    )
    return frame.sort_values(
        ["ImportanceMean", "Feature"],
        ascending=[True, True],
    ).reset_index(drop=True)


def redundancy_partner_present(
    feature: str,
    active_features: list[str],
) -> bool:
    active = set(active_features)
    for group in REDUNDANCY_GROUPS:
        if feature in group and len(group & active) >= 2:
            return True
    return False


def choose_candidate(
    importance: pd.DataFrame,
    active_features: list[str],
    protected_features: set[str],
) -> tuple[str | None, str]:
    candidates = importance[
        ~importance["Feature"].isin(protected_features)
    ].copy()
    if candidates.empty:
        return None, "No unprotected features remain."
    noise = candidates[
        (candidates["KnownNoise"])
        & (
            candidates["ImportanceMean"]
            <= IMPORTANCE_CANDIDATE_THRESHOLD
        )
    ]
    if not noise.empty:
        row = noise.iloc[0]
        return str(row["Feature"]), "Known noise + low permutation importance"
    redundant = candidates[
        candidates["KnownRedundancyCandidate"]
        & (
            candidates["ImportanceMean"]
            <= IMPORTANCE_CANDIDATE_THRESHOLD
        )
    ]
    for _, row in redundant.iterrows():
        feature = str(row["Feature"])
        if redundancy_partner_present(
            feature,
            active_features,
        ):
            return (
                feature,
                "Known redundancy + low permutation importance",
            )
    weak = candidates[
        candidates["ImportanceMean"]
        <= IMPORTANCE_CANDIDATE_THRESHOLD
    ]
    if not weak.empty:
        row = weak.iloc[0]
        return (
            str(row["Feature"]),
            "Low permutation importance",
        )
    return None, (
        "No feature meets the low-importance threshold."
    )


def main():
    print("=" * 72)
    print("ASSUREX - FEATURE SELECTION LOOP")
    print("=" * 72)
    if not TRAIN_PATH.exists():
        raise FileNotFoundError(
            f"Train dataset not found:\n{TRAIN_PATH}"
        )
    if not VALIDATION_PATH.exists():
        raise FileNotFoundError(
            f"Validation dataset not found:\n{VALIDATION_PATH}"
        )
    train = read_csv(TRAIN_PATH)
    validation = read_csv(VALIDATION_PATH)
    validate_inputs(
        train,
        validation,
    )
    active_features = predictor_columns(train)
    if not active_features:
        raise ValueError("No predictor candidates found.")
    history_rows = []
    rejected_rows = []
    all_importance = []
    protected_features: set[str] = set()
    current_pipeline, current_accuracy, current_f1 = fit_and_evaluate(
        train,
        validation,
        active_features,
    )
    baseline_accuracy = current_accuracy
    baseline_f1 = current_f1
    history_rows.append({
        "Iteration": 0,
        "Attempt": 0,
        "FeatureCount": len(active_features),
        "CandidateRemoved": "",
        "CandidateReason": "Baseline",
        "Decision": "BASELINE",
        "ValidationAccuracy": current_accuracy,
        "ValidationMacroF1": current_f1,
        "DeltaVsPreviousF1": 0.0,
        "DeltaVsBaselineF1": 0.0,
    })
    print(f"Baseline features             : {len(active_features)}")
    print(f"Baseline validation accuracy  : {baseline_accuracy:.6f}")
    print(f"Baseline validation Macro F1  : {baseline_f1:.6f}")
    accepted_removals = 0
    total_attempts = 0
    iteration = 0
    while (
        accepted_removals < MAX_ACCEPTED_REMOVALS
        and total_attempts < MAX_TOTAL_ATTEMPTS
    ):
        importance = compute_importance(
            current_pipeline,
            validation,
            active_features,
            iteration,
        )
        all_importance.append(
            importance.copy()
        )
        candidate, candidate_reason = choose_candidate(
            importance,
            active_features,
            protected_features,
        )
        if candidate is None:
            print(
                f"\nStopping: {candidate_reason}"
            )
            break
        total_attempts += 1
        trial_features = [
            feature
            for feature in active_features
            if feature != candidate
        ]
        if not trial_features:
            print("\nStopping: cannot remove final predictor.")
            break
        trial_pipeline, trial_accuracy, trial_f1 = fit_and_evaluate(
            train,
            validation,
            trial_features,
        )
        delta_previous = trial_f1 - current_f1
        delta_baseline = trial_f1 - baseline_f1
        local_ok = (
            trial_f1
            >= current_f1 - LOCAL_F1_TOLERANCE
        )
        baseline_ok = (
            trial_f1
            >= baseline_f1 - BASELINE_F1_TOLERANCE
        )
        accepted = bool(local_ok and baseline_ok)
        if accepted:
            accepted_removals += 1
            iteration += 1
            history_rows.append({
                "Iteration": iteration,
                "Attempt": total_attempts,
                "FeatureCount": len(trial_features),
                "CandidateRemoved": candidate,
                "CandidateReason": candidate_reason,
                "Decision": "ACCEPT_REMOVE",
                "ValidationAccuracy": trial_accuracy,
                "ValidationMacroF1": trial_f1,
                "DeltaVsPreviousF1": delta_previous,
                "DeltaVsBaselineF1": delta_baseline,
            })
            print(
                f"\nIteration {iteration}: REMOVE {candidate}"
            )
            print(f"Reason                        : {candidate_reason}")
            print(f"Features remaining            : {len(trial_features)}")
            print(f"Validation accuracy           : {trial_accuracy:.6f}")
            print(f"Validation Macro F1           : {trial_f1:.6f}")
            print(f"Delta vs previous F1          : {delta_previous:+.6f}")
            print(f"Delta vs baseline F1          : {delta_baseline:+.6f}")
            print("Decision                      : ACCEPT")
            active_features = trial_features
            current_pipeline = trial_pipeline
            current_accuracy = trial_accuracy
            current_f1 = trial_f1
            continue
        protected_features.add(candidate)
        rejected_rows.append({
            "Attempt": total_attempts,
            "Feature": candidate,
            "CandidateReason": candidate_reason,
            "ValidationAccuracyAfterRemoval": trial_accuracy,
            "ValidationMacroF1AfterRemoval": trial_f1,
            "CurrentValidationMacroF1": current_f1,
            "BaselineValidationMacroF1": baseline_f1,
            "DeltaVsCurrentF1": delta_previous,
            "DeltaVsBaselineF1": delta_baseline,
            "ReasonRejected": (
                "Removal exceeded local and/or baseline Macro-F1 tolerance."
            ),
        })
        history_rows.append({
            "Iteration": iteration,
            "Attempt": total_attempts,
            "FeatureCount": len(active_features),
            "CandidateRemoved": candidate,
            "CandidateReason": candidate_reason,
            "Decision": "REJECT_REMOVE",
            "ValidationAccuracy": current_accuracy,
            "ValidationMacroF1": current_f1,
            "DeltaVsPreviousF1": 0.0,
            "DeltaVsBaselineF1": current_f1 - baseline_f1,
        })
        print(
            f"\nAttempt {total_attempts}: TRY REMOVE {candidate}"
        )
        print(f"Reason                        : {candidate_reason}")
        print(f"Trial Validation Macro F1     : {trial_f1:.6f}")
        print(f"Delta vs current F1           : {delta_previous:+.6f}")
        print(f"Delta vs baseline F1          : {delta_baseline:+.6f}")
        print("Decision                      : REJECT / RESTORE")
    final_importance = compute_importance(
        current_pipeline,
        validation,
        active_features,
        iteration + 1,
    )
    final_importance.to_csv(
        FINAL_IMPORTANCE_PATH,
        index=False,
        encoding="utf-8-sig",
    )
    if all_importance:
        pd.concat(
            all_importance,
            ignore_index=True,
        ).to_csv(
            IMPORTANCE_PATH,
            index=False,
            encoding="utf-8-sig",
        )
    else:
        pd.DataFrame().to_csv(
            IMPORTANCE_PATH,
            index=False,
            encoding="utf-8-sig",
        )
    pd.DataFrame(history_rows).to_csv(
        HISTORY_PATH,
        index=False,
        encoding="utf-8-sig",
    )
    pd.DataFrame(
        rejected_rows,
        columns=[
            "Attempt",
            "Feature",
            "CandidateReason",
            "ValidationAccuracyAfterRemoval",
            "ValidationMacroF1AfterRemoval",
            "CurrentValidationMacroF1",
            "BaselineValidationMacroF1",
            "DeltaVsCurrentF1",
            "DeltaVsBaselineF1",
            "ReasonRejected",
        ],
    ).to_csv(
        REJECTED_PATH,
        index=False,
        encoding="utf-8-sig",
    )
    selected_df = pd.DataFrame({
        "Feature": active_features,
        "Selected": True,
    })
    selected_df.to_csv(
        SELECTED_PATH,
        index=False,
        encoding="utf-8-sig",
    )
    joblib.dump(
        current_pipeline,
        SELECTOR_MODEL_PATH,
    )
    manifest = {
        "selector_model": "GradientBoostingClassifier",
        "random_seed": RANDOM_SEED,
        "train_rows": int(len(train)),
        "validation_rows": int(len(validation)),
        "test_loaded": False,
        "initial_feature_count": int(
            len(predictor_columns(train))
        ),
        "selected_feature_count": int(
            len(active_features)
        ),
        "accepted_removals": int(
            accepted_removals
        ),
        "rejected_removals": int(
            len(rejected_rows)
        ),
        "baseline_validation_accuracy": baseline_accuracy,
        "baseline_validation_macro_f1": baseline_f1,
        "final_validation_accuracy": current_accuracy,
        "final_validation_macro_f1": current_f1,
        "importance_method": "permutation importance on validation, scoring=f1_macro",
        "thresholds": {
            "importance_candidate_threshold": IMPORTANCE_CANDIDATE_THRESHOLD,
            "local_f1_tolerance": LOCAL_F1_TOLERANCE,
            "baseline_f1_tolerance": BASELINE_F1_TOLERANCE,
        },
        "selected_features": active_features,
        "protected_after_failed_removal": sorted(
            protected_features
        ),
        "rules": {
            "test_used": False,
            "one_feature_removed_per_attempt": True,
            "importance_recomputed_after_accepted_removal": True,
            "rollback_on_excessive_validation_drop": True,
        },
    }
    MANIFEST_PATH.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("\n" + "=" * 72)
    print("FEATURE SELECTION COMPLETE")
    print("=" * 72)
    print(f"Initial features              : {len(predictor_columns(train))}")
    print(f"Selected features             : {len(active_features)}")
    print(f"Accepted removals             : {accepted_removals}")
    print(f"Rejected removals             : {len(rejected_rows)}")
    print(f"Baseline Validation Macro F1  : {baseline_f1:.6f}")
    print(f"Final Validation Macro F1     : {current_f1:.6f}")
    print(f"Final Validation Accuracy     : {current_accuracy:.6f}")
    print("Test used                     : NO")
    print("\nSelected features:")
    for feature in active_features:
        print(f" - {feature}")
    print("\nCreated:")
    for path in [
        HISTORY_PATH,
        IMPORTANCE_PATH,
        FINAL_IMPORTANCE_PATH,
        SELECTED_PATH,
        REJECTED_PATH,
        MANIFEST_PATH,
        SELECTOR_MODEL_PATH,
    ]:
        print(f" - {path}")
    print("\nIMPORTANT:")
    print(" - TEST was never loaded.")
    print(" - Selected features are based only on Train + Validation.")
    print(" - feature_selector_model.joblib is NOT the final Python model.")
    print(" - Next stage: train 3 algorithms using the selected feature set.")
if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=UserWarning)
    main()
