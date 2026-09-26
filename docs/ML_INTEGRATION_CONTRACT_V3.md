# AssureX V3 ML Integration Contract

## Scope
This document defines the handoff between the AssureX V3 ML/Decision pipeline and the application layer.
It does not define or modify React UI, FastAPI routes, authentication, or SQL/database design.

## Python Model
- Algorithm: Gradient Boosting
- Artifact: `model/assurex_v3_final_model.joblib`
- Feature definition: `model/assurex_v3_final_features.csv`
- Locked Test: 225 claims
- Test Accuracy: 0.991111
- Test Macro F1: 0.991110

Frozen feature order:
1. RepairAuthorized
2. SerialNumberMatch
3. ProductModelConsistent
4. DuplicateClaimIndicator
5. ContradictionIndicator
6. OCRConfidence
7. ClaimReportingDelayDays
8. WarrantyRemainingDays
9. ClaimReportingWithinPeriod
10. FaultCovered
11. RequiredDocumentsComplete
12. MissingDocumentCount
13. ProductIdentityMatch
14. OCRQualityBand

Python output must retain predicted class, top confidence, and all three class probabilities.

## GTM Model
- Final iteration: G2 V3
- Artifact directory: `gtm/frozen_G2_V3`
- Locked Test: 225 claims
- Test Accuracy: 0.862222
- Test Macro F1: 0.861017

Required frozen artifacts:
- `model.json`
- `weights.bin`
- `metadata.json`
- `g2_card_features_v3.json`
- `SHA256SUMS.txt`

Claim Summary Cards must not contain Python prediction, Python confidence, or final application decision.

## Model Comparison
Confidence difference:
`abs(Python top confidence - GTM top confidence)`

Allowed statuses:
- Strong Match
- Acceptable Match
- Weak Match
- Model Disagreement
- Uncertain Result

Locked snapshot:
- Claims: 225
- Matches: 196
- Disagreements: 29
- Mean top-confidence difference: 0.088500
- Strong Match: 126
- Acceptable Match: 52
- Weak Match: 14
- Model Disagreement: 29
- Uncertain Result: 4

## Warranty Rules
Configurable policies are under `config/warranty_policies/`.

Rule inputs may include:
WarrantyStatus, WarrantyRemainingDays, ComponentWarrantyEligible, FaultCovered,
ClaimReportingDelayDays, ClaimReportingWithinPeriod, RequiredDocumentsComplete,
MissingDocumentCount, CriticalDocumentMissing, PreviousRepair, RepairAuthorized,
RepairReportAvailable, SerialNumberMatch, ProductIdentityMatch,
ProductModelConsistent, DuplicateClaimIndicator, DocumentDuplicateIndicator,
ContradictionIndicator, OCRConfidence.

## Decision Engine
The Decision Engine is deterministic application logic, not a third trained classifier.

Allowed final decisions:
- Likely Valid
- Likely Invalid
- Manual Review Required

Locked decision snapshot:
- Likely Valid: 69
- Likely Invalid: 22
- Manual Review Required: 134

Manual-review triggers include disagreement, low confidence, large confidence difference,
missing/unknown evidence, contradictions, duplicate indicators, identity/serial issues,
and previous repair with missing/unknown repair report.

Regression cases `CLM01148` and `CLM01188` must both result in `Manual Review Required`.

## Application Handoff
The application team may map these outputs to its own API and database:
- python_prediction
- python_confidence
- python_probabilities
- gtm_prediction
- gtm_confidence
- gtm_probabilities
- predicted_class_match
- confidence_difference
- model_consistency_status
- warranty_rule_result
- final_decision
- requires_manual_review
- decision_reasons

The application layer must not retrain either model during inference, tune on the locked Test set,
insert Python/GTM predictions into GTM cards, or replace the Decision Engine with an external generative-AI decision service.
