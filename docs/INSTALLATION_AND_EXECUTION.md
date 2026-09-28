# Installation and Execution Guide

## Prerequisites

- macOS, Windows, or Linux
- Python 3.11 or later
- Node.js 20 or later
- npm
- Git

## Install Frontend Dependencies

```bash
npm install
npm --prefix ./assurex_web/frontend install
```

## Install GTM Runtime Dependencies

```bash
npm run install:gtm
```

The GTM runtime uses local Node dependencies to load the Google Teachable Machine image model. If this step fails on macOS due to native `canvas` dependencies, install the Xcode command line tools and retry.

## Install Backend Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r assurex_web/backend/requirements.txt
```

On Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r assurex_web/backend/requirements.txt
```

## Initialize Database

The repository includes `assurex_web/backend/assurex.db` and seed scripts. If a fresh database is required:

```bash
cd assurex_web/backend
python -m app.init_db
```

## Run Backend

```bash
cd assurex_web/backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Run Frontend

```bash
npm run dev
```

Open the Vite URL shown in the terminal.

## Default Workspaces

Use the seeded accounts in the database or seed script. Update this section with final evaluator credentials before submission:

| Role | Email | Password |
|---|---|---|
| Admin | username `admin` | `123` |
| Reviewer | username `reviewer` | `reviewer123` |
| Service Center | create from Admin > Users | create from Admin > Users |
| Customer | register from Customer Portal | chosen during registration |

## Run ML Validation

```bash
python3 tests_ml/validate_ml_v3.py
```

## Run GTM Runtime Smoke Test

```bash
npm run install:gtm
python3 tests_ml/smoke_gtm_g2_runtime.py
```

## Run Frontend Build

```bash
npm --prefix ./assurex_web/frontend run build
```

## Manual Execution Flow

1. Log in as customer.
2. Select or register a product.
3. Enter incident date, fault description, repair history, and evidence.
4. Submit claim.
5. Review Python prediction, GTM prediction, consistency status, confidence difference, and decision reasons.
6. Log in as reviewer.
7. Open manual-review queue.
8. Approve, reject, or add reviewer comments.
9. Log in as admin.
10. Review dashboards, audit logs, ML reports, and CSV exports.

## Troubleshooting

| Problem | Fix |
|---|---|
| GTM runtime says `canvas` missing | Run `npm run install:gtm` |
| Native canvas build fails on macOS | Install Xcode command line tools, then retry |
| Backend cannot import packages | Activate `.venv` and reinstall backend requirements |
| Frontend cannot reach backend | Confirm backend is running on port 8000 and frontend API base URL is correct |
| Model prediction unavailable | Confirm `model/assurex_v3_final_model.joblib` exists |
| GTM prediction unavailable | Confirm `gtm/frozen_G2_V3` exists and Node dependencies are installed |
