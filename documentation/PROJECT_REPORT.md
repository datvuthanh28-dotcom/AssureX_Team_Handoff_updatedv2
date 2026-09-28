# AssureX Claim Engine Project Report

## Problem Definition

Warranty claim processing is slow and inconsistent when staff manually inspect purchase details, warranty status, product evidence, previous repairs, and policy exclusions. AssureX Claim Engine automates claim triage with a Python classification model, a Google Teachable Machine image model, and a deterministic warranty rule engine.

## Proposed Solution

The application collects claim details and supporting evidence, derives structured claim features, predicts claim class using Python Gradient Boosting V3, renders a Claim Summary Card for GTM G2 V3, compares both predictions, applies warranty rules, and routes the claim to Likely Valid, Likely Invalid, or Manual Review Required.

## Architecture

```text
React UI
  -> FastAPI routes
  -> Feature engineering
  -> Python V3 model
  -> GTM G2 V3 claim-card inference
  -> Decision engine
  -> SQLite database
  -> Reviewer/admin/customer dashboards
```

## Main Modules

| Module | Responsibility |
|---|---|
| `assurex_web/frontend` | Customer, reviewer, admin, ML dashboard UI |
| `assurex_web/backend/app/customer_routes.py` | Customer claim workflow |
| `assurex_web/backend/app/warranty_ticket_routes.py` | Warranty ticket workflow and retraining export |
| `assurex_web/backend/app/ml/feature_service.py` | Feature derivation and policy signals |
| `assurex_web/backend/app/ml/model_service.py` | Python V3 model loading and prediction |
| `assurex_web/backend/app/ml/gtm_service.py` | Claim-card rendering and GTM runtime bridge |
| `assurex_web/backend/app/ml/decision_service.py` | Warranty rule validation and final decision |
| `training/` | Python model selection/finalization scripts |
| `gtm/` | GTM card rendering, exported models, and evaluation artifacts |
| `comparison/` | Python/GTM comparison and decision summary |

## Dataset

The V3 dataset contains 1,500 locked records after split:

| Split | Records | Class Balance |
|---|---:|---|
| Train | 1,050 | 350 per class |
| Validation | 225 | 75 per class |
| Test | 225 | 75 per class |

Classes:

- Valid Claim
- Invalid Claim
- Manual Review

## Python Model

- Final model: Gradient Boosting V3
- Feature count: 14
- Test records: 225
- Accuracy: 0.991111
- Macro F1: 0.991110
- Artifact: `model/assurex_v3_final_model.joblib`

## Google Teachable Machine Model

- Final model: GTM G2 V3
- Artifact directory: `gtm/frozen_G2_V3`
- Test records: 225
- Accuracy: 0.862222
- Macro F1: 0.861017

## Decision Engine

The decision engine combines:

- Python prediction and confidence
- GTM prediction and confidence
- Confidence difference
- Model consistency status
- Warranty status
- Fault coverage
- Reporting period
- Required evidence
- Serial/product identity
- Duplicate indicators
- Contradictions
- OCR confidence

Output decisions:

- Likely Valid
- Likely Invalid
- Manual Review Required

## Security and Privacy

- Role-based workspace access for admin, reviewer, service center, and customer.
- Audit trail for important actions.
- Evidence files are linked to claim records.
- No external generative AI API is used for final claim decisions.

## Known Limitations

- Full public deployment URL, video demo, and blog link must be added before final submission.
- Full GTM claim-card image dataset should be generated/committed with train/validation/test split folders and mapping files.
- Additional automated tests should be added for OCR, file upload security, API authorization, and database edge cases.
- Detailed downloadable per-claim PDF/HTML reports can be added as a final polish feature.

## Future Enhancements

- Add richer anomaly monitoring.
- Add reviewer request-for-additional-information workflow.
- Add scheduled warranty-expiry notifications.
- Add per-claim downloadable report with evidence and reviewer comments.
- Add deployment pipeline and production environment configuration.

