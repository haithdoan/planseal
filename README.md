# PlanSeal

**Cryptographic approval for saved infrastructure plans.**

PlanSeal proves that the Terraform or OpenTofu plan being offered for
execution is exactly the plan a human approved: same file, same Git revision,
same provider lockfile, and same resource-action scope.

```text
saved plan -> sanitized evidence -> owner signature -> exact-input verification -> apply
```

PlanSeal is local-first, has no service or account, does not manage cloud
credentials, and does not persist raw plan JSON. Apply is preview-only unless
the operator explicitly supplies `--execute`.

> [!WARNING]
> PlanSeal is alpha software. It has not received an independent security
> audit. Do not treat it as the only control protecting production systems.

## Why

Saved plans separate review from execution, which is useful for automation and
AI-assisted operations. That separation creates a precise question:

> Is this still the exact artifact I reviewed?

An approval in chat or a CI button does not, by itself, bind the approval to
the plan bytes, source revision, dependency lock, and action list. PlanSeal
creates and verifies that binding.

## Quick start

Requirements: Python 3.11+, Git, and either OpenTofu or Terraform.

```bash
git clone https://github.com/haithdoan/planseal.git
cd planseal
python -m pip install .

planseal keygen \
  --private-key ~/.config/planseal/owner-private.pem \
  --public-key ~/.config/planseal/owner-public.pem

tofu plan -out=change.tfplan

planseal inspect change.tfplan \
  --repo . \
  --lockfile .terraform.lock.hcl \
  --output evidence.json
```

Review the sanitized evidence, copy its digest from the `inspect` output, and
approve only the action classes you intend:

```bash
planseal approve evidence.json \
  --private-key ~/.config/planseal/owner-private.pem \
  --allow create,update \
  --confirm sha256:REPLACE_WITH_EVIDENCE_DIGEST \
  --output certificate.json
```

Verify all bindings and preview the fixed apply command:

```bash
planseal verify \
  --evidence evidence.json \
  --certificate certificate.json \
  --public-key ~/.config/planseal/owner-public.pem \
  --plan change.tfplan \
  --repo . \
  --lockfile .terraform.lock.hcl

planseal apply \
  --evidence evidence.json \
  --certificate certificate.json \
  --public-key ~/.config/planseal/owner-public.pem \
  --plan change.tfplan \
  --repo . \
  --lockfile .terraform.lock.hcl
```

The last command is a preview. Add `--execute` only after reviewing its JSON
output. Execution consumes the certificate nonce before starting the saved
plan, so the certificate cannot be reused.

## What evidence contains

```json
{
  "actions": [
    {"actions": ["update"], "address": "module.edge.example_resource.policy"}
  ],
  "lockfile_checksum": "sha256:...",
  "plan_checksum": "sha256:...",
  "plan_id": "change.tfplan",
  "schema_version": 1,
  "source_revision_digest": "sha256:...",
  "tool": "opentofu"
}
```

It intentionally excludes plan values, provider configuration, state,
environment variables, credentials, command output, and absolute paths.
Resource addresses may still reveal naming conventions; treat evidence as
operational metadata.

## Security properties

- Ed25519 signatures over canonical JSON.
- Five-minute maximum certificate lifetime.
- Exact plan, source revision, lockfile, and action-scope binding.
- Explicit approval for delete and replacement actions.
- Clean tracked Git worktree required at inspection and verification.
- No shell invocation.
- Preview-first execution.
- SQLite-backed one-time certificate consumption.
- Sanitized machine-readable errors.

Read the [threat model](docs/threat-model.md) before using PlanSeal around
sensitive infrastructure.

## Project status

PlanSeal v0.1 is an intentionally narrow proof of the exact-artifact approval
protocol. Planned follow-up work includes encrypted OS-backed key storage,
hardware-backed owner presence, remote receiver profiles, and signed receipts.
Those features are not part of the current security claim.

## Documentation

Start at the [documentation index](docs/README.md).

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md),
[SECURITY.md](SECURITY.md), and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

[MIT](LICENSE)
