# Submission Test Input Records

Generated at: 2026-09-28T22:34:02.691829Z

Password for all customer accounts: `TestPass123!`

Use these records in the Customer Portal to submit new claims yourself.

| Case | Customer Login | Registration Code | Expected Result |
|---|---|---|---|
| `submit-valid` | `submit.valid.20260928223402@assurex.local` | `REG-00023` | Valid / WARRANTY candidate |
| `submit-invalid` | `submit.invalid.20260928223402@assurex.local` | `REG-00024` | Invalid / NOT_WARRANTY because Liquid Damage is excluded |
| `submit-manual-review` | `submit.manual.20260928223402@assurex.local` | `REG-00025` | Manual Review / REVIEW_REQUIRED because required evidence answers are missing |

## submit-valid

- Login: `submit.valid.20260928223402@assurex.local` / `TestPass123!`
- Registered Product Code: `REG-00023`
- Product: Submit Test Laptop Valid (Laptop)
- Expected: Valid / WARRANTY candidate
- Submit Claim inputs:
  - Incident Date: `2026-09-27`
  - Fault Category: `Power Failure`
  - Fault Description: `Not required because category is predefined`
  - Previous Repair: `No`
  - Purchase proof?: `Yes`
  - Serial/product identity proof?: `Yes`
  - Fault evidence?: `Yes`

## submit-invalid

- Login: `submit.invalid.20260928223402@assurex.local` / `TestPass123!`
- Registered Product Code: `REG-00024`
- Product: Submit Test Smartphone Invalid (Smartphone)
- Expected: Invalid / NOT_WARRANTY because Liquid Damage is excluded
- Submit Claim inputs:
  - Incident Date: `2026-09-28`
  - Fault Category: `Liquid Damage`
  - Fault Description: `Not required because category is predefined`
  - Previous Repair: `No`
  - Purchase proof?: `Yes`
  - Serial/product identity proof?: `Yes`
  - Fault evidence?: `Yes`

## submit-manual-review

- Login: `submit.manual.20260928223402@assurex.local` / `TestPass123!`
- Registered Product Code: `REG-00025`
- Product: Submit Test Laptop Manual Review (Laptop)
- Expected: Manual Review / REVIEW_REQUIRED because required evidence answers are missing
- Submit Claim inputs:
  - Incident Date: `2026-09-24`
  - Fault Category: `Battery Problem`
  - Fault Description: `Not required because category is predefined`
  - Previous Repair: `No`
  - Purchase proof?: `Yes`
  - Serial/product identity proof?: `No`
  - Fault evidence?: `No`

