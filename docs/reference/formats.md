# Evidence and Certificate Formats

All protocol documents use UTF-8 JSON. Digests and signatures are computed over
canonical JSON with sorted object keys, no insignificant whitespace, and no
NaN values.

## Evidence v1

| Field | Meaning |
| --- | --- |
| `schema_version` | Integer `1` |
| `tool` | `opentofu` or `terraform` |
| `plan_id` | Saved-plan basename; never an absolute path |
| `plan_checksum` | SHA-256 of saved-plan bytes |
| `source_revision_digest` | SHA-256 of canonical JSON containing Git `HEAD` |
| `lockfile_checksum` | SHA-256 of dependency lockfile bytes |
| `actions` | Sorted resource addresses with their exact action vectors |

No-op resource changes are omitted. Empty `actions` therefore means the saved
plan is a no-op.

The evidence file contains the object above. The `inspect` command writes a
stdout envelope containing both `evidence` and its computed `evidence_digest`,
so the owner can bind `approve --confirm` without modifying the evidence file.

## Certificate v1

The certificate contains a `payload` and a base64url Ed25519 `signature` over
the canonical payload JSON.

| Payload field | Meaning |
| --- | --- |
| `evidence_digest` | SHA-256 of complete evidence v1 |
| `signer_key_id` | SHA-256 fingerprint of the raw Ed25519 public key |
| `audience` | Fixed value `planseal.apply` |
| `approved_actions` | Sorted action allowlist approved by the owner |
| `nonce` | Random 128-bit single-use value encoded as lowercase hex |
| `issued_at` | UTC RFC 3339 timestamp |
| `expires_at` | UTC RFC 3339 timestamp, at most five minutes later |

Readers must reject unknown fields, unsupported schema versions, malformed
digests, noncanonical action order, invalid signatures, expired certificates,
and incomplete action authorization.
