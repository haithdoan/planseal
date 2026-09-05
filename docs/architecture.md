# Architecture

## Components

```text
Terraform/OpenTofu saved plan
            |
            v
       Inspector --------> sanitized evidence
                                |
                                v
Owner private key --------> certificate issuer
                                |
                                v
plan + Git + lockfile ----> verifier ----> preview
                                |
                                v
                         replay ledger
                                |
                                v
                    fixed saved-plan apply
```

## Inspector

The inspector invokes only `<tool> show -json <plan>` with an argument vector.
It parses the output in memory and retains only resource addresses and action
names. The saved plan, current Git revision, and dependency lockfile are hashed
with SHA-256.

Evidence is deterministic for the same inputs. It contains no creation time or
machine-specific path.

## Certificate issuer

The issuer validates that every observed action is present in the owner's
explicit allowlist. It signs canonical certificate payload JSON using Ed25519.
The payload binds the evidence digest, signer key ID, audience, approved action
set, random nonce, issue time, and expiry time.

## Verifier

Verification is fail-closed and checks:

1. strict evidence and certificate schemas;
2. certificate audience and five-minute lifetime;
3. evidence digest and approved action scope;
4. signer key ID and Ed25519 signature;
5. current saved-plan checksum;
6. current committed Git revision and clean tracked worktree;
7. current dependency lockfile checksum.

## Executor

The executor supports one operation: apply the existing saved plan. It does not
accept arbitrary arguments and does not invoke a shell. Preview is the default.

With `--execute`, the certificate nonce is inserted into a local SQLite ledger
inside an immediate transaction before the subprocess starts. The fixed vector
is:

```text
tofu|terraform apply -input=false -no-color <saved-plan>
```

The provider process inherits the terminal. PlanSeal does not capture provider
output because it may contain sensitive values.
