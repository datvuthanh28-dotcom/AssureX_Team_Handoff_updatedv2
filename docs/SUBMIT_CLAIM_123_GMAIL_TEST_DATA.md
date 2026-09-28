# Submit Claim Test Data for 123@gmail.com

Generated at: 2026-09-28T22:37:35.904490Z

Login with your existing customer account: `123@gmail.com`.

| Case | Registered Product Code | Expected Result |
|---|---|---|
| `VALID` | `REG-00026` | WARRANTY → Claim Status: Waiting to proceed |
| `INVALID` | `REG-00027` | NOT_WARRANTY / Invalid Claim |
| `MANUAL_REVIEW` | `REG-00028` | REVIEW_REQUIRED / Manual Review |

## VALID

- Registered Product Code: `REG-00026`
- Product: 123 Test Laptop Valid (Laptop)
- Expected Result: WARRANTY → Claim Status: Waiting to proceed
- Fill Submit Claim fields:
  - Incident Date: `2026-09-27`
  - Fault Category: `Power Failure`
  - Fault Description: `Leave blank / not required`
  - Previous Repair: `No`
  - Purchase proof?: `Yes`
  - Serial/product identity proof?: `Yes`
  - Fault evidence?: `Yes`

## INVALID

- Registered Product Code: `REG-00027`
- Product: 123 Test Phone Invalid (Smartphone)
- Expected Result: NOT_WARRANTY / Invalid Claim
- Fill Submit Claim fields:
  - Incident Date: `2026-09-28`
  - Fault Category: `Liquid Damage`
  - Fault Description: `Leave blank / not required`
  - Previous Repair: `No`
  - Purchase proof?: `Yes`
  - Serial/product identity proof?: `Yes`
  - Fault evidence?: `Yes`

## MANUAL_REVIEW

- Registered Product Code: `REG-00028`
- Product: 123 Test Laptop Manual Review (Laptop)
- Expected Result: REVIEW_REQUIRED / Manual Review
- Fill Submit Claim fields:
  - Incident Date: `2026-09-24`
  - Fault Category: `Battery Problem`
  - Fault Description: `Leave blank / not required`
  - Previous Repair: `No`
  - Purchase proof?: `Yes`
  - Serial/product identity proof?: `No`
  - Fault evidence?: `No`

