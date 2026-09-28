# Test Case Matrix

This file lists the SRS-required test cases and the current repository evidence or planned verification path.

## Automated Commands

```bash
python3 tests_ml/validate_ml_v3.py
python3 tests_ml/validate_srs_deliverables.py
python3 tests/role_flow_e2e.py
python3 tests_ml/smoke_gtm_g2_runtime.py
npm --prefix ./assurex_web/frontend run build
python3 -m py_compile assurex_web/backend/app/ml/model_service.py assurex_web/backend/app/ml/gtm_service.py assurex_web/backend/app/ml/decision_service.py assurex_web/backend/app/customer_routes.py assurex_web/backend/app/warranty_ticket_routes.py
```

`tests_ml/smoke_gtm_g2_runtime.py` requires GTM Node dependencies:

```bash
npm run install:gtm
```

## Functional Test Cases

| ID | Scenario | Expected Result | Evidence / Status |
|---|---|---|---|
| TC-F01 | Admin/reviewer/service login | Role-specific workspace opens | Automated API role-flow + manual UI |
| TC-F02 | Customer registers product and creates warranty ticket | Ticket ID created, 14 features derived, status enters reviewer queue | Automated API role-flow |
| TC-F03 | Customer answers evidence Yes/No questions | Evidence completeness features are derived without requiring file upload | Automated API role-flow + manual UI |
| TC-F04 | Reviewer approves claim | Status becomes Approved, audit entry recorded, retraining export includes ground truth | Automated API role-flow |
| TC-F05 | Reviewer rejects claim | Status becomes Rejected, customer can appeal | Manual UI/API test |
| TC-F06 | Customer submits appeal | Appeal enters reviewer queue | Manual UI/API test |

## ML Test Cases

| ID | Scenario | Expected Result | Evidence / Status |
|---|---|---|---|
| TC-ML01 | Python V3 artifact loads | Model path resolves to V3 artifact | Automated validation |
| TC-ML02 | Python V3 feature order | 14 frozen features match artifact | Automated validation |
| TC-ML03 | Python locked test metrics | Accuracy >= 0.85, Macro F1 >= 0.85 | Automated validation, observed 0.991111 / 0.991110 |
| TC-ML04 | GTM artifact exists | model.json, weights.bin, metadata.json, config, SHA256SUMS exist | Automated validation |
| TC-ML05 | GTM locked test metrics | Accuracy >= 0.85, Macro F1 >= 0.85 | Stored metrics, observed 0.862222 / 0.861017 |
| TC-ML06 | Python/GTM comparison | 225 common Claim IDs compared | Automated validation |
| TC-ML07 | Model disagreement | Disagreement routes to Manual Review | Comparison report + rule-engine test |
| TC-ML08 | Low-confidence prediction | Manual Review trigger appears | Rule-engine test |

## Boundary and Negative Test Cases

| ID | Scenario | Expected Result | Evidence / Status |
|---|---|---|---|
| TC-B01 | Claim on warranty expiry date | Reporting/warranty rule handles boundary correctly | Add API test |
| TC-B02 | Fault date before purchase date | ContradictionIndicator = Yes | Existing feature logic, add API test |
| TC-B03 | Claim date before purchase date | Contradiction warning and manual review | Existing logic, add API test |
| TC-B04 | Missing purchase proof question = No | MissingDocumentCount > 0, manual review signal | Existing logic, add API test |
| TC-B05 | Unsupported upload type | Upload rejected with safe error | Add API test |
| TC-B06 | Duplicate document hash | Duplicate warning or manual review | Partial implementation, add API test |
| TC-B07 | Duplicate product/claim | DuplicateClaimIndicator = Yes | Existing logic, add API test |
| TC-B08 | Serial-number mismatch | ProductIdentityMatch = No, manual review | Existing logic, add API test |
| TC-B09 | Unauthorized repair | Invalid or manual review trigger | Existing rule logic |
| TC-B10 | Missing GTM runtime | Manual review reason says GTM unavailable | Existing rule logic |

## Security Test Cases

| ID | Scenario | Expected Result | Evidence / Status |
|---|---|---|---|
| TC-S01 | Unauthenticated retraining/admin data access | Request rejected | Automated API role-flow |
| TC-S02 | Reviewer accesses admin-only users | Request rejected | Automated API role-flow |
| TC-S03 | Admin attempts to create non-reviewer workspace user | Request rejected | Automated API role-flow |
| TC-S04 | Invalid JWT/session token | Request rejected safely | Add API test |
| TC-S05 | Oversized file upload | Rejected with understandable error | Add API test |

## Demonstration Cases Required by SRS

| Case | Current Evidence |
|---|---|
| One valid claim | Dataset and UI flow available |
| One invalid claim | Dataset and UI flow available |
| One manual-review claim | Dataset and UI flow available |
| Expired warranty claim | Dataset/rules available |
| Missing-document claim | Feature/rules available |
| Duplicate claim | Feature/rules available |
| Contradictory claim | Feature/rules available |
| Serial-number mismatch | Feature/rules available |
| Unauthorized repair claim | Feature/rules available |
| Boundary-date claim | Dataset/rules available |
| Python/GTM disagreement | Comparison report contains 29 disagreements |
