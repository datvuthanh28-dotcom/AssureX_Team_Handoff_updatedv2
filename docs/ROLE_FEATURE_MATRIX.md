# AssureX role and feature matrix

## Customer Portal (`/` or `/customer`)

- Registration, login, profile and password management
- Product registration and product list
- Warranty list, active/expired/expiring status and warranty details
- Receipt, invoice, warranty card and claim evidence upload
- Receipt OCR review and correction before submission
- New claim creation and claim preparation warnings
- Claim list, status timeline and decision explanation
- Additional-information response and customer notifications
- Appeal a rejected claim
- Download the customer's claim information

## Reviewer Workspace (`/reviewer`)

- Assigned/manual-review queue
- Search and filter claims
- Full claim, warranty, evidence and repair-history review
- Python prediction, Google model prediction and confidence comparison
- Model consistency, missing-document, duplicate and contradiction indicators
- Warranty rule validation and decision reasons
- Approve, reject or request additional information
- Reviewer comments and AI decision override
- Appeal processing and reviewer audit history

## Admin Console (`/admin`)

- System dashboard and operational metrics
- User and role management
- Product catalog and warranty policy management
- Expiry-alert and decision-threshold configuration
- ML Pipeline: Audit, Preprocessing, Text Models, Image Model, Compare
- Model version and deployment evidence
- Reports, analytics and CSV export
- Audit logs and system notifications

Admin does not expose the Customer Claims queue. Reviewer does not expose user management, policy management or ML pipeline controls.

## Background services (not primary navigation)

- Data preprocessing and feature engineering
- Claim Summary Card generation
- Python and Google model inference
- Confidence and consistency comparison
- Duplicate claim/document detection
- Serial-number and contradiction checks
- Missing-document detection
- Final decision engine
- Notifications, audit events and retraining data collection

## Service-center access

Service-center accounts should be limited to product/claim intake, document upload and claims assigned to that service center. They must not access system-wide users, policies, ML controls or all customer claims.
