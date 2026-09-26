from pathlib import Path
import json

import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    GradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    OneHotEncoder,
    StandardScaler,
)


ROOT = Path(__file__).resolve().parent.parent

TRAIN_PATH = (
    ROOT
    / "data/train/assurex_v3_train.csv"
)

VAL_PATH = (
    ROOT
    / "data/validation/assurex_v3_validation.csv"
)

SELECTED_PATH = (
    ROOT
    / "data/feature_selection_v3"
    / "assurex_v3_selected_features.csv"
)

OUT_DIR = (
    ROOT
    / "data/model_comparison_v3"
)

MODEL_DIR = (
    ROOT
    / "model"
)

AUDIT_DIR = (
    ROOT
    / "data/audit"
)

for folder in [
    OUT_DIR,
    MODEL_DIR,
    AUDIT_DIR,
]:
    folder.mkdir(
        parents=True,
        exist_ok=True,
    )


TARGET = "ClaimClass"

RESULT_PATH = (
    OUT_DIR
    / "assurex_v3_model_comparison.csv"
)

PREDICTION_PATH = (
    OUT_DIR
    / "assurex_v3_validation_predictions.csv"
)

MANIFEST_PATH = (
    AUDIT_DIR
    / "assurex_v3_model_comparison_manifest.json"
)

WINNER_MODEL_PATH = (
    MODEL_DIR
    / "assurex_v3_validation_winner.joblib"
)

RANDOM_SEED = 20260926


def read_csv(path):
    return pd.read_csv(
        path,
        keep_default_na=False,
        na_values=[""],
    )


def load_selected():
    df = pd.read_csv(
        SELECTED_PATH
    )

    return (
        df.loc[
            df["Selected"]
            .astype(str)
            .str.lower()
            .isin(["true", "1", "yes"]),
            "Feature",
        ]
        .tolist()
    )


def infer_types(
    df,
    features,
):
    numeric = []
    categorical = []

    for column in features:
        series = df[column]
        non_missing = int(
            series.notna().sum()
        )

        parsed = pd.to_numeric(
            series,
            errors="coerce",
        )

        if (
            non_missing > 0
            and parsed.notna().sum()
            / non_missing
            >= 0.95
        ):
            numeric.append(column)
        else:
            categorical.append(column)

    return numeric, categorical


def build_pipeline(
    train,
    features,
    model,
):
    numeric, categorical = (
        infer_types(
            train,
            features,
        )
    )

    numeric_pipe = Pipeline([
        (
            "imputer",
            SimpleImputer(
                strategy="median"
            ),
        ),
        (
            "scaler",
            StandardScaler(),
        ),
    ])

    categorical_pipe = Pipeline([
        (
            "imputer",
            SimpleImputer(
                strategy="most_frequent"
            ),
        ),
        (
            "encoder",
            OneHotEncoder(
                handle_unknown="ignore",
                sparse_output=False,
            ),
        ),
    ])

    prep = ColumnTransformer([
        (
            "numeric",
            numeric_pipe,
            numeric,
        ),
        (
            "categorical",
            categorical_pipe,
            categorical,
        ),
    ])

    return Pipeline([
        ("preprocessor", prep),
        ("model", model),
    ])


def main():
    train = read_csv(
        TRAIN_PATH
    )

    val = read_csv(
        VAL_PATH
    )

    features = load_selected()

    if set(train["ClaimID"]) & set(val["ClaimID"]):
        raise RuntimeError(
            "Train/Validation ClaimID overlap."
        )

    X_train = train[features]
    y_train = train[TARGET]

    X_val = val[features]
    y_val = val[TARGET]

    models = {
        "Logistic Regression":
            LogisticRegression(
                max_iter=3000,
                random_state=RANDOM_SEED,
            ),

        "Random Forest":
            RandomForestClassifier(
                n_estimators=400,
                random_state=RANDOM_SEED,
                n_jobs=-1,
            ),

        "Gradient Boosting":
            GradientBoostingClassifier(
                n_estimators=150,
                learning_rate=0.05,
                max_depth=3,
                random_state=RANDOM_SEED,
            ),
    }

    results = []
    predictions = []

    fitted = {}

    for name, model in models.items():

        pipeline = build_pipeline(
            train,
            features,
            model,
        )

        pipeline.fit(
            X_train,
            y_train,
        )

        pred = pipeline.predict(
            X_val
        )

        fitted[name] = pipeline

        accuracy = accuracy_score(
            y_val,
            pred,
        )

        precision = precision_score(
            y_val,
            pred,
            average="macro",
            zero_division=0,
        )

        recall = recall_score(
            y_val,
            pred,
            average="macro",
            zero_division=0,
        )

        macro_f1 = f1_score(
            y_val,
            pred,
            average="macro",
        )

        results.append({
            "Model": name,
            "ValidationAccuracy":
                accuracy,
            "ValidationMacroPrecision":
                precision,
            "ValidationMacroRecall":
                recall,
            "ValidationMacroF1":
                macro_f1,
            "SelectedFeatureCount":
                len(features),
        })

        for claim_id, actual, predicted in zip(
            val["ClaimID"],
            y_val,
            pred,
        ):
            predictions.append({
                "Model": name,
                "ClaimID": claim_id,
                "Actual": actual,
                "Predicted": predicted,
                "Correct":
                    actual == predicted,
            })

    results_df = (
        pd.DataFrame(results)
        .sort_values(
            [
                "ValidationMacroF1",
                "ValidationAccuracy",
            ],
            ascending=False,
        )
        .reset_index(drop=True)
    )

    winner = results_df.iloc[0]["Model"]

    joblib.dump(
        fitted[winner],
        WINNER_MODEL_PATH,
    )

    results_df.to_csv(
        RESULT_PATH,
        index=False,
    )

    pd.DataFrame(
        predictions
    ).to_csv(
        PREDICTION_PATH,
        index=False,
    )

    manifest = {
        "train_rows":
            len(train),

        "validation_rows":
            len(val),

        "test_loaded":
            False,

        "selected_feature_count":
            len(features),

        "selected_features":
            features,

        "winner":
            winner,

        "selection_metric":
            "Validation Macro F1",

        "models_compared":
            list(models),

        "test_used":
            False,
    }

    MANIFEST_PATH.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print("=" * 72)
    print("ASSUREX V3 - MODEL COMPARISON")
    print("=" * 72)

    print()
    print(
        results_df.to_string(
            index=False
        )
    )

    print()
    print(
        "Selected features:",
        len(features),
    )

    print(
        "Validation winner:",
        winner,
    )

    print(
        "Test loaded       : NO"
    )

    print(
        "Test used         : NO"
    )


if __name__ == "__main__":
    main()
