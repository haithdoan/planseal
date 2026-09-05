# Minimal Synthetic Example

This example exercises PlanSeal without a cloud account, external provider, or
real infrastructure. It uses only the built-in `terraform_data` resource.

Copy the example before running it so generated plans and keys stay outside the
source checkout:

```bash
cp -R examples/minimal /tmp/planseal-example
cd /tmp/planseal-example

git init -b main
git config user.name "PlanSeal Example"
git config user.email "planseal@example.invalid"
terraform init -backend=false
git add main.tf
git add -f .terraform.lock.hcl
git commit -m "test: initialize synthetic example"

terraform plan -out=change.tfplan
planseal inspect change.tfplan --tool terraform --output evidence.json
```

The final `inspect` command prints an `evidence_digest`. Review `evidence.json`,
then substitute that digest below:

```bash
planseal keygen \
  --private-key owner-private.pem \
  --public-key owner-public.pem

planseal approve evidence.json \
  --private-key owner-private.pem \
  --allow create \
  --confirm sha256:REPLACE_WITH_EVIDENCE_DIGEST \
  --output certificate.json

planseal verify \
  --evidence evidence.json \
  --certificate certificate.json \
  --public-key owner-public.pem \
  --plan change.tfplan

planseal apply \
  --evidence evidence.json \
  --certificate certificate.json \
  --public-key owner-public.pem \
  --plan change.tfplan
```

The last command previews the fixed apply command. This example deliberately
does not use `--execute`.

To use OpenTofu instead, replace `terraform` with `tofu` and pass
`--tool opentofu` to `planseal inspect`.
