# AssureX Claim Engine – Team Handoff Architecture
> Customer Input → Product Lookup → Feature Engineering (14 Features) → Python Model V3 + GTM G2 V3 → Decision Engine

## Current Production Models

| Component | Active Version | Locked-Test Accuracy | Macro F1 |
|---|---|---:|---:|
| Python structured model | Gradient Boosting V3, 14 features | 99.11% | 99.11% |
| Google Teachable Machine | G2 V3 image model | 86.22% | 86.10% |
| Decision Engine | V3 deterministic rules | N/A | N/A |

The active runtime registry is `model_tracking/active_models.json`.

## Runtime Setup
After cloning the repository, install the frontend and GTM G2 V3 runtime dependencies:

```bash
npm install
npm run install:gtm
```

The second command installs the local Teachable Machine runtime used by the backend for image inference. Without it, GTM claims are routed to Manual Review because image inference is unavailable.

Full installation and execution instructions are in `docs/INSTALLATION_AND_EXECUTION.md`.

## SRS Readiness Documents

| Document | Purpose |
|---|---|
| `docs/SRS_COMPLIANCE_MATRIX.md` | Requirement-by-requirement status against the official SRS |
| `docs/TEST_CASE_MATRIX.md` | Functional, ML, boundary, negative, and security test matrix |
| `reports/SRS_COMPLIANCE_REPORT.md` | Submission-readiness summary |
| `documentation/PROJECT_REPORT.md` | Project report draft |
| `AI_USAGE.md` | Required AI tool usage declaration |
| `docs/DEMO_AND_BLOG_PLACEHOLDERS.md` | Deployment, video, and blog links to fill before final submission |

## Validation Commands

```bash
python3 tests_ml/validate_ml_v3.py
python3 tests_ml/validate_srs_deliverables.py
python3 tests/role_flow_e2e.py
npm --prefix ./assurex_web/frontend run build
python3 -m py_compile assurex_web/backend/app/ml/model_service.py assurex_web/backend/app/ml/gtm_service.py assurex_web/backend/app/ml/decision_service.py assurex_web/backend/app/customer_routes.py assurex_web/backend/app/warranty_ticket_routes.py
```

GTM runtime smoke test:

```bash
npm run install:gtm
python3 tests_ml/smoke_gtm_g2_runtime.py
```

## 1. Design Principles & Scope
- **UX Goal**: Minimize manual customer inputs. Customer provides basic identity and enters **Product Code**.
- **Database Lookup**: Backend verifies ownership and queries `sold_products` + `product_catalog` + `users`. The product and warranty details are displayed read-only on the frontend.
- **Customer Claim Information**: Customer only fills in:
  1. `IncidentDate`: When defect occurred.
  2. `ProblemCategory`: selected fault category, including `Other`.
  3. `FaultDescription`: required only when `ProblemCategory = Other`.
  4. `PreviousRepair`: Yes/No (`RepairCentre` and `RepairDate` if Yes).
  5. Evidence availability questions: Yes/No for purchase proof, serial/product identity proof, fault evidence, and repair report if repaired.
- **Core Principle**: **Customers NEVER manually enter technical ML features** (e.g. `RepairAuthorized`, `FaultCovered`, `WarrantyRemainingDays`, etc.). The backend derives and validates the active 14-feature V3 contract automatically.

---

## 2. The 14 Engineered ML Features
| # | Feature Name | Derivation Source / Rule |
|---|---|---|
| 1 | `RepairAuthorized` | `PreviousRepair` + `RepairCentre` + `RepairReport` + authorized service center records |
| 2 | `SerialNumberMatch` | OCR serial from evidence compared to `sold_products.serial_number` |
| 3 | `ProductModelConsistent` | OCR model detected from evidence compared to `product_catalog.model_number` |
| 4 | `DuplicateClaimIndicator` | History check for existing open claims with matching serial/equipment |
| 5 | `ContradictionIndicator` | Rule check for date contradictions (e.g. incident before purchase, future dates) |
| 6 | `OCRConfidence` | OCR confidence extraction score (0.0 to 1.0) |
| 7 | `ClaimReportingDelayDays` | `ClaimCreatedAt − IncidentDate` (elapsed days) |
| 8 | `WarrantyRemainingDays` | `WarrantyExpiryDate − ClaimCreatedAt` (remaining days; negative if expired) |
| 9 | `ClaimReportingWithinPeriod` | Delay within statutory 30-day reporting window (`Yes` / `No`) |
| 10 | `FaultCovered` | `FaultDescription` analyzed against warranty exclusions (water, physical drop) |
| 11 | `RequiredDocumentsComplete` | Verification that all mandatory evidence documents are attached |
| 12 | `MissingDocumentCount` | Count of required documents missing (0, 1, 2...) |
| 13 | `ProductIdentityMatch` | Composite match of serial, model, OCR, and invoice |
| 14 | `OCRQualityBand` | Categorical band derived from `OCRConfidence` (`High`, `Medium`, `Low`) |

---

## 3. Database Schema & Demo Bundle
The demo data bundle includes:
- `assurex_demo_schema_and_seed.sql`: SQLite / PostgreSQL schema and seed data.
- `users.csv`: 20 demo customer accounts.
- `product_catalog.csv`: 10 product models across categories (Laptop, Smartphone, Monitor, Printer, Tablet).
- `sold_products.csv`: 50 registered product units.
- `sold_products_lookup.csv`: Denormalized lookup view.

### Database Lookup Query
```sql
SELECT
  sp.product_code, sp.serial_number, sp.purchase_date,
  sp.warranty_start_date, sp.warranty_expiry_date,
  u.user_code, u.full_name, u.email, u.phone,
  pc.product_name, pc.category, pc.brand, pc.model_number,
  pc.standard_warranty_months
FROM sold_products sp
JOIN users u ON sp.user_id = u.id
JOIN product_catalog pc ON sp.catalog_id = pc.id
WHERE sp.product_code = ?;
```

---

## 4. End-to-End Runtime Flow
1. **Customer Identification**: Enter email or customer code (e.g. `ngoc.mai07@example.com`).
2. **Product Code Lookup**: Enter `AX26-00001` → System retrieves NovaBook 14, active warranty, serial number `NB142026-00001`.
3. **Incident & Evidence**: Enter incident date, choose a fault category, answer evidence availability Yes/No questions, and provide a description only when category is Other.
4. **Feature Engineering**: Backend derives the active 14 V3 features in real-time.
5. **Python Model V3**: Gradient Boosting classifier evaluates the 14 features (`Valid Claim`, `Invalid Claim`, `Manual Review`) while GTM G2 V3 evaluates the rendered claim-card image.
6. **Reviewer Ground Truth**: Reviewer inspects inputs, evidence, and model features, then records official Ground Truth (`Valid Claim` / `Invalid Claim`).
