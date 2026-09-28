# AI Usage Declaration

This project used AI assistance during development. All generated suggestions were reviewed, edited, tested, and integrated by the team before submission.

## Tool

- Tool name: OpenAI ChatGPT / Codex
- Purpose: Code review, implementation assistance, documentation drafting, ML pipeline explanation, and test/checklist preparation.

## Affected Modules

- Backend ML runtime configuration and V3 alignment:
  - `assurex_web/backend/app/ml/model_service.py`
  - `assurex_web/backend/app/ml/gtm_service.py`
  - `assurex_web/backend/app/ml/decision_service.py`
  - `model_tracking/active_models.json`
- Claim and reviewer workflow review:
  - `assurex_web/backend/app/customer_routes.py`
  - `assurex_web/backend/app/warranty_ticket_routes.py`
  - `assurex_web/frontend/src/App.jsx`
  - `assurex_web/frontend/src/WarrantyClaimSystem.jsx`
- Documentation and SRS readiness:
  - `README.md`
  - `docs/SRS_COMPLIANCE_MATRIX.md`
  - `docs/TEST_CASE_MATRIX.md`
  - `docs/INSTALLATION_AND_EXECUTION.md`
  - `documentation/PROJECT_REPORT.md`

## Team Review and Modification

The team reviewed the AI-assisted output, checked it against the official SRS, and modified the codebase to use the active V3 Python and GTM artifacts end to end. Runtime paths, feature contracts, visible UI labels, and model metadata were checked against repository artifacts.

## Testing Performed

- Python backend files were compiled with `python3 -m py_compile`.
- Python V3 model was loaded from `model/assurex_v3_final_model.joblib`.
- Python V3 locked-test metrics were rechecked on 225 test claims:
  - Accuracy: 0.991111
  - Macro F1: 0.991110
- GTM service import was checked and confirmed to reference `gtm/frozen_G2_V3`.
- React frontend production build was run with `npm --prefix ./assurex_web/frontend run build`.

## Known AI-Assisted Limitations

- Public deployment URL, demo video URL, and blog URL must be created and added by the team before final submission.
- GTM runtime smoke test requires Node dependencies, including `canvas`, to be installed locally with `npm run install:gtm`.

## Verifier

- Team member responsible for final verification: NextWave AssureX team lead
