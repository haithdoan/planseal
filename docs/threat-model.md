# Threat Model

## Assets

- Infrastructure controlled by Terraform or OpenTofu.
- The owner's approval decision.
- The Ed25519 private key.
- Saved plan integrity and provenance.
- Provider credentials available to the apply process.

## Trust boundaries

PlanSeal treats plan JSON, evidence files, certificate files, resource
addresses, CLI arguments, and agent-generated text as untrusted input. It
trusts the selected public key, the local Git executable, the Terraform or
OpenTofu executable found on `PATH`, the operating system, and the host account.

## In-scope threats

| Threat | Control |
| --- | --- |
| Plan swapped after review | Saved-plan SHA-256 binding |
| Source changed after review | Git revision digest and clean-worktree check |
| Provider selection changed | Lockfile SHA-256 binding |
| Approval reused | Durable nonce ledger |
| Approval used much later | Five-minute maximum TTL |
| Destructive action hidden in scope | Explicit resource/action evidence and allowlist |
| Shell injection through a path | Fixed argument vector; no shell |
| Sensitive plan values written to evidence | Output allowlist; raw plan JSON is not persisted |
| Error output leaks provider data | Stable error codes; tool stderr is not forwarded |

## Out-of-scope threats

- A compromised owner host, kernel, Python runtime, Git, or IaC executable.
- Theft or misuse of the unencrypted v0.1 private key.
- Malicious provider behavior after a valid apply starts.
- Incorrect or incomplete plans produced by Terraform/OpenTofu providers.
- State drift between planning and execution.
- Denial of service.
- Protecting credentials made directly available to an AI agent.
- Independent identity verification or multi-party approval.

## Residual risks

Resource addresses can expose service or environment naming. Certificate
consumption proves only that execution started, not that every provider action
completed. After interruption or a nonzero exit, operators must inspect state
and create a new plan; they must not reuse the certificate.

## Reporting

Report suspected vulnerabilities according to [SECURITY.md](../SECURITY.md).
Do not include credentials, private plans, state files, or production evidence
in a public issue.
