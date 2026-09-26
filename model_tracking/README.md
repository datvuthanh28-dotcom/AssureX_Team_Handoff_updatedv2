# AssureX Model Tracking

This registry supplements the locked artifacts under `submission_final/`; it does not replace or rewrite them.

## Python Training

Run from the repository root with the backend environment:

```powershell
.\assurex_web\backend\.venv\Scripts\python.exe .\scripts\train_python_models.py --version-suffix v2
```

The trainer reads the existing train, validation, and test CSVs. It clones the `preprocessor` from `assurex_web/backend/app/ml/assurex_final_model.joblib` and pairs it with exactly Logistic Regression, Random Forest, and Gradient Boosting. `ClaimID` and `ClaimClass` are excluded from feature inputs. Five-fold stratified cross-validation and fitting use training data only. Validation Macro F1 is the primary selection metric; ties use Macro Recall, Macro Precision, then lower CV standard deviation. The locked test split is read only after selection and evaluated once for each candidate's final report. The test metrics never select a model.

Every run requires a new suffix. Artifacts are stored under `model/python/<algorithm>/`; reports and prediction-level confidence outputs are stored under `evaluation/python/`; model metadata and historical/active status are tracked in `python_models.csv`. The trainer refuses to overwrite versioned run outputs or reuse tracked model versions.

`python-gradientboosting-v1` is the newly trained validation-selected model. The pre-existing production model remains untouched and is separately recorded as a retained legacy artifact because its original preprocessing fit and training dataset version are not present. The locked test results differ slightly; see the tracked versions rather than treating the results as interchangeable.

The robustness experiment is reproducible with:

```powershell
.\assurex_web\backend\.venv\Scripts\python.exe .\scripts\run_python_robustness.py --version-suffix v2
```

It trains on the training split, evaluates on validation, excludes rule-derived fields, and does not load the test split.

## Claim Summary Cards

Render the frozen G5 23-field specification from the common locked CSV splits. The renderer keeps ClaimID only in the join manifest and does not draw it into pixels:

```powershell
.\assurex_web\backend\.venv\Scripts\python.exe .\scripts\render_gtm_claim_cards.py --dataset-version G5-v2
```

Cards are separated into train/validation/test folders. Their manifest maps each `ClaimID`, split, actual class, and relative card path. The actual class is stored only in the manifest for scoring and is never drawn on the card. Python predictions, confidence, and final decisions are not card fields.

`G5-v1` is retained as an audit artifact; its images included ClaimID and it must not be used for identifier-leakage-safe model selection. `G5-v2` is the no-ID card set for new Teachable Machine experiments. Neither is asserted to match the missing original training renderer. Compatibility probes of the existing G5 export on G5-v1 and G5-v2 validation predicted Manual Review for 224/225 and 225/225 claims respectively; G5-v2 Macro F1 was 0.166667. The runs are in `evaluation/google/` and are not eligible for model selection. The locked test split was not evaluated with these mismatched representations.

## Google Teachable Machine Variants

Google Teachable Machine must train and export each image model independently. No Python training script in this repository claims to train a Teachable Machine model. Export each variant into its own directory and update its row in `google_models.csv` only with observed settings and measured metrics.

Existing Model A is the frozen G5 export at `submission_final/gtm_model/` (model, metadata, weights). Its metadata records Teachable Machine 2.4.16, TensorFlow.js 1.7.4, and 224-pixel model input. Its original epochs, batch size, learning rate, source-card rendering and per-claim predictions are unavailable. Historical aggregate metrics are retained with that provenance caveat.

Planned independent configurations for the missing variants:

- Model B: same `G5-v2` card fields and train/validation split; epochs 80, batch size 16, learning rate 0.001.
- Model C: same `G5-v2` card fields and train/validation split; epochs 150, batch size 16, learning rate 0.0005.

Use identical card content, split ClaimIDs, image dimensions, and export method for A/B/C comparisons. Record all actual Teachable Machine settings. Select exactly one using validation Macro F1 and secondary validation/class-wise review only. Evaluate the selected model once on the locked test split. Until B/C exports and a reproducible evaluator are available, their tracking metrics remain blank and their status remains `NOT_PROVIDED`.

## Active Runtime Configuration

`active_models.json` records the validation-selected Python version and the historically selected Google G5 version. FastAPI loads the active Python artifact from this registry. Google inference is explicitly `not_connected`; customer claims record the configured Google model/version, null prediction/confidence, and an `Uncertain Result` consistency status. Until Google inference is connected, non-hard-invalid customer claims are routed to Manual Review. Do not produce or persist a synthetic Google prediction. The consistency thresholds remain unset until common validation predictions from eligible models can support calibration.

The cross-model evaluator accepts per-claim CSVs from the selected Python trainer and Google evaluator. It requires at least 30 identical locked test ClaimIDs, matching actual classes, and calibrated validation-only consistency thresholds. Run only after those prerequisites are satisfied:

```powershell
.\assurex_web\backend\.venv\Scripts\python.exe .\scripts\compare_selected_models.py --python-predictions .\evaluation\python\model_predictions_v1.csv --google-predictions <google-test-predictions.csv> --version-suffix v1
```

It refuses to write reports while thresholds are uncalibrated or predictions are missing/mismatched. When enabled, it writes a per-claim comparison CSV and JSON/HTML summary under `model_tracking/` and `evaluation/comparison/`, applying hard warranty invalidation before manual-review conditions.

The application decision engine remains separate from offline evaluation and continues to apply warranty, missing-document, contradiction, duplicate, serial, and repair-authorization rules. Existing claim decisions and source model artifacts are preserved.
