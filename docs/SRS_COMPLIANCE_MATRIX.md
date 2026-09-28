# SRS Compliance Matrix

This matrix maps the official AssureX Claim Engine SRS requirements to the current repository implementation.

## Overall Status

| Area | Status | Evidence |
|---|---|---|
| Structured Python dataset | Complete | `data/train/assurex_v3_train.csv`, `data/validation/assurex_v3_validation.csv`, `data/test/assurex_v3_test.csv` |
| Python model training and evaluation | Complete | `training/`, `data/final_evaluation_v3/`, `model/assurex_v3_final_model.joblib` |
| Python model accuracy >= 85% | Complete | Accuracy 0.991111, Macro F1 0.991110 |
| GTM model artifact | Complete | `gtm/frozen_G2_V3/` |
| GTM model accuracy >= 85% | Complete | Accuracy 0.862222, Macro F1 0.861017 |
| Dual-model comparison | Complete | `comparison/assurex_v3_model_comparison_final.csv` |
| Decision engine | Complete | `assurex_web/backend/app/ml/decision_service.py` |
| Warranty policies | Complete | `config/warranty_policies/*.json` |
| FastAPI + React application | Complete | `assurex_web/backend`, `assurex_web/frontend` |
| OCR/document parsing | Partial | OCR modules exist; full extracted-data correction workflow needs final demo evidence |
| Claim-card image dataset | Partial | GTM artifacts and sample cards exist; full committed 2,100+ training-image dataset is not present |
| Automated test suite | Partial | `tests_ml/` validates ML package; full SRS test suite is documented in `docs/TEST_CASE_MATRIX.md` |
| Deployment URL | Missing | Add final public URL before submission |
| Demo video | Missing | Add final video link before submission |
| Technical blog | Missing | Add final blog link before submission |

## Functional Requirements

| # | Requirement | Status | Notes |
|---|---|---|---|
| i | User registration and authentication | Partial | Workspace login and role checks exist. Public self-registration should be demonstrated or documented if not exposed. |
| ii | User profile management | Partial | Workspace profile UI exists; complete edit/update flow should be verified. |
| iii | Product registration | Partial | Product/catalog/registered product data model exists; final demo should show product registration or seeded equivalent. |
| iv | Warranty record management | Partial | Warranty records and policy data exist; extended warranty and expiry UI should be verified in demo. |
| v | Receipt and invoice upload | Partial | Evidence upload is implemented; final test should cover PDF/JPG/JPEG/PNG. |
| vi | Receipt scanning and data extraction | Partial | OCR/parser modules exist; complete invoice-field extraction evidence should be added. |
| vii | Extracted data verification | Partial | Document comparison exists; user correction before save is not fully proven. |
| viii | Warranty tracking | Complete | Warranty dates and remaining days are derived and displayed. |
| ix | Warranty expiry alerts | Partial | Notification/settings UI exists; scheduled expiry-alert automation should be validated. |
| x | Claim registration | Complete | Customer claims and warranty tickets create unique IDs. |
| xi | Claim information collection | Complete | Claim, fault, repair, warranty, and evidence fields are collected. |
| xii | Fault and evidence collection | Complete | The primary customer flow records evidence availability through Yes/No questions; the legacy upload endpoint remains available for optional file evidence. |
| xiii | Repair history management | Complete | Previous repair data and authorization signals are tracked. |
| xiv | Document organization | Partial | Documents are linked to claims; replace/remove/download evidence should be tested. |
| xv | Data validation | Complete | Backend schemas, date checks, duplicate checks, Yes/No evidence completeness checks, Other-category description validation, and UI readiness checks exist. |
| xvi | Data preprocessing | Complete | Python preprocessing, feature engineering, imputation, encoding, and scaling exist. |
| xvii | Common warranty claim dataset | Complete for CSV, partial for images | CSV split is complete; full image dataset deliverable must be added or generated. |
| xviii | Python classification model | Complete | Gradient Boosting V3 selected after candidate comparison. |
| xix | Python confidence scores | Complete | `predict_proba` returns all class probabilities. |
| xx | Claim Summary Card generation | Complete in code, partial in dataset evidence | Renderer and configs exist; full generated image dataset should be committed or documented. |
| xxi | GTM classification | Complete in artifact, partial runtime verification | G2 V3 export exists; local runtime requires Node dependencies. |
| xxii | Model prediction comparison | Complete | Class match is reported. |
| xxiii | Confidence score comparison | Complete | Absolute top-confidence difference is calculated. |
| xxiv | Model consistency status | Complete | Strong/Acceptable/Weak/Disagreement/Uncertain implemented. |
| xxv | Warranty rule validation | Complete | Rules cover expiry, fault, reporting, repair, documents, identity, duplicates, contradictions. |
| xxvi | Configurable warranty policies | Complete | Category JSON policies exist. |
| xxvii | Serial-number verification | Complete | Serial matching feeds model and review logic. |
| xxviii | Contradiction detection | Complete | Purchase/fault/claim/repair contradictions are checked. |
| xxix | Missing document detection | Complete | Missing count and required-evidence checks exist. |
| xxx | Duplicate claim detection | Partial | Duplicate claim indicator exists; broader comparison by invoice/fault/customer should be extended. |
| xxxi | Document duplicate detection | Partial | Document hashes are stored; cross-claim duplicate alert should be fully tested. |
| xxxii | AI-generated claim summary | Partial | Claim analysis panels exist; a formal generated summary export should be added. |
| xxxiii | Claim preparation assistance | Partial | Readiness checks exist; corrective actions can be more detailed. |
| xxxiv | Final claim decision | Complete | Decision engine outputs Likely Valid, Likely Invalid, Manual Review Required. |
| xxxv | Decision explanation | Complete | Decision reasons and consistency status are stored. |
| xxxvi | Manual review workflow | Complete | Reviewer queue and approve/reject workflow exist; request-additional-info should be added if required. |
| xxxvii | Reviewer comments and override | Complete | Reviewer comments and override status are stored. |
| xxxviii | Claim status tracking | Complete | Customer/reviewer/admin status views exist. |
| xxxix | Notifications and alerts | Partial | Notifications exist; expiry/missing-document scheduled alerts should be demonstrated. |
| xl | Claim dashboard | Complete | Customer/admin dashboard views exist. |
| xli | Administrator dashboard | Partial | Metrics exist; trends and model disagreement analytics can be richer. |
| xlii | Search and filtering | Partial | Search/filter exists; confidence/risk/reviewer/date filters should be added if time permits. |
| xliii | Data analysis and reporting | Partial | ML analytics and CSV reports exist; business analytics should be expanded. |
| xliv | Downloadable claim report | Partial | CSV export exists; per-claim detailed downloadable report should be added. |
| xlv | Data export | Complete | Claim CSV and retraining export exist. |
| xlvi | Data storage | Complete | SQLite and SQLAlchemy models store accounts, claims, decisions, notifications, audit. |
| xlvii | Audit trail | Complete | Audit routes and records exist. |
| xlviii | Model version tracking | Complete | Python and GTM versions are stored per decision. |
| xlix | Error handling | Partial | Error messages exist; security-oriented error tests should be added. |
| l | Monitoring and anomaly alerts | Partial | Some warnings exist; full monitoring dashboard is not complete. |

## Highest Priority Remaining Work

1. Generate or commit the complete GTM claim-card image dataset with split folders and mapping file.
2. Add public deployment URL, demo video link, and technical blog link.
3. Expand automated tests from ML-only validation into full app, OCR, security, database, and rule-engine tests.
4. Add a detailed downloadable per-claim report.
5. Complete extracted-data verification and request-additional-information workflows.

