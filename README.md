# AssureX Claim Engine – Team Handoff Architecture
> Customer Input → Product Lookup → Feature Engineering (14 Features) → Python Model V3

## Runtime setup
After cloning the repository, install the frontend and GTM G2 V3 runtime dependencies:

```bash
npm install
npm run install:gtm
```

The second command installs the local Teachable Machine runtime used by the backend for image inference. Without it, GTM claims are routed to Manual Review because image inference is unavailable.

## 1. Design Principles & Scope
- **UX Goal**: Minimize manual customer inputs. Customer provides basic identity and enters **Product Code**.
- **Database Lookup**: Backend verifies ownership and queries `sold_products` + `product_catalog` + `users`. The product and warranty details are displayed read-only on the frontend.
- **Customer Claim Information**: Customer only fills in:
  1. `IncidentDate`: When defect occurred.
  2. `FaultDescription`: Detailed symptoms.
  3. `PreviousRepair`: Yes/No (`RepairCentre` and `RepairDate` if Yes).
  4. Evidence Uploads: `PurchaseInvoice`, `SerialImage`, `FaultEvidence` (and `RepairReport` if repaired).
- **Core Principle**: **Customers NEVER manually enter technical ML features** (e.g. `RepairAuthorized`, `FaultCovered`, `OCRConfidence`, `SerialNumberMatch`, etc.). The backend derives and validates these 14 features automatically.

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
3. **Incident & Evidence**: Enter defect description, incident date, repair history, and upload documents.
4. **Feature Engineering**: Backend derives the 14 features in real-time.
5. **Python Model V3**: Gradient Boosting classifier evaluates the 14 features (`WARRANTY`, `REVIEW_REQUIRED`, `NOT_WARRANTY`).
6. **Reviewer Ground Truth**: Reviewer inspects inputs, evidence, and 14 features, then records official Ground Truth (`Valid Claim` / `Invalid Claim`).
