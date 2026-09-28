# Manual Test Records

Generated at: 2026-09-28T21:31:40.399054Z

Password for all seeded customer accounts: `TestPass123!`

| Case | Customer Login | Registration Code | Ticket ID | Category | AI/ML Result | What to test |
|---|---|---|---|---|---|---|
| `valid` | `test.valid@assurex.local` | `REG-00014` | `TCK-SEED01-213140` | Power Failure | WARRANTY / Valid Claim (0.9481) | Valid path / reviewer approval candidate |
| `missing-evidence` | `test.missing.evidence@assurex.local` | `REG-00015` | `TCK-SEED02-213140` | Battery Problem | REVIEW_REQUIRED / Manual Review (0.9903) | Manual review due to missing serial/fault evidence |
| `liquid-damage` | `test.liquid.damage@assurex.local` | `REG-00016` | `TCK-SEED03-213140` | Liquid Damage | NOT_WARRANTY / Invalid Claim (0.9635) | Invalid / not covered because Liquid Damage is excluded |
| `unauthorized-repair` | `test.unauthorized.repair@assurex.local` | `REG-00017` | `TCK-SEED04-213140` | Keyboard & Trackpad Failure | NOT_WARRANTY / Invalid Claim (0.8723) | Manual/invalid review trigger due to unauthorized repair |
| `other-category` | `test.other.category@assurex.local` | `REG-00018` | `TCK-SEED05-213140` | Other | WARRANTY / Valid Claim (0.9481) | Other category validation path; description provided |

Reviewer queue: log in as `reviewer` / `reviewer123` and open the warranty reviewer queue.
Admin can also inspect these records in the claim/audit views.
