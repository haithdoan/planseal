# Getting Started

## Prerequisites

- Python 3.11 or newer
- Git
- OpenTofu (`tofu`) or Terraform (`terraform`)
- A repository with a committed `.terraform.lock.hcl`

PlanSeal requires a clean tracked worktree. Untracked files are ignored so the
saved plan and local evidence files do not need to be committed.

`pipx` is recommended for installing the published CLI in an isolated Python
environment.

## Install

Install the latest published release:

```bash
pipx install planseal
planseal --version
```

To install from a source checkout instead:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install .
```

## Install for development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Create an owner key

```bash
planseal keygen \
  --private-key ~/.config/planseal/owner-private.pem \
  --public-key ~/.config/planseal/owner-public.pem
```

The private key is written with mode `0600`. v0.1 stores an unencrypted PEM
file; protect the host account and never commit the key. OS-backed encrypted
key storage is future work.

To exercise the complete preview-only flow without credentials or external
providers, follow the [minimal synthetic example](../examples/minimal/README.md).

## Inspect

Create the plan from the exact committed revision you intend to approve:

```bash
tofu init
tofu plan -out=change.tfplan
planseal inspect change.tfplan --output evidence.json
```

`inspect` runs `tofu show -json` or `terraform show -json`, keeps the raw JSON
in memory only, and emits the sorted resource addresses and action names.

A no-op saved plan produces valid evidence with an empty `actions` list. It
cannot be approved or executed because there is no change to authorize.

## Approve

Read `evidence.json` and the evidence digest printed by `inspect`. Then bind an
approval to that exact digest:

```bash
planseal approve evidence.json \
  --private-key ~/.config/planseal/owner-private.pem \
  --allow create,update \
  --confirm sha256:REPLACE_WITH_EVIDENCE_DIGEST \
  --ttl 300 \
  --output certificate.json
```

If the plan contains `delete`, `forget`, or a replacement represented by both
`delete` and `create`, those action names must be present in `--allow`.

## Verify and apply

`verify` recomputes every local binding. `apply` performs the same checks and
prints the command it would run:

```bash
planseal apply \
  --evidence evidence.json \
  --certificate certificate.json \
  --public-key ~/.config/planseal/owner-public.pem \
  --plan change.tfplan
```

To perform the apply, repeat the command with `--execute`. PlanSeal consumes
the certificate before starting Terraform/OpenTofu. A crash after that point
leaves the result uncertain and requires normal infrastructure reconciliation;
the certificate remains consumed.
