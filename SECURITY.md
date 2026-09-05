# Security Policy

## Supported versions

PlanSeal is pre-release software. Security fixes are applied to the latest
release only.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub's private
vulnerability reporting feature for this repository.

Include the affected version, expected invariant, minimal synthetic
reproduction, and impact. Do not attach real plans, state, credentials,
provider output, internal URLs, or identifying infrastructure metadata.

## Operational warning

PlanSeal v0.1 uses an unencrypted local Ed25519 private key and has not received
an independent audit. Restrict key access, use least-privilege provider
credentials, retain normal policy-as-code and CI protections, and test in a
disposable environment before considering sensitive workloads.
