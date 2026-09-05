# Repository Instructions

## Purpose

PlanSeal provides cryptographic, exact-artifact approval for saved Terraform
and OpenTofu plans. Keep the project small, local-first, and deterministic.

## Development

- Use Python 3.11 or newer.
- Install development dependencies with `python -m pip install -e '.[dev]'`.
- Run `ruff check .`, `ruff format --check .`, `mypy src`, and
  `pytest --cov=planseal --cov-report=term-missing` before committing.
- Add or update tests before changing security-sensitive behavior.

## Safety boundaries

- Never log or persist raw plan JSON, environment variables, credentials,
  Terraform state, provider values, or absolute workspace paths.
- Never invoke a shell. Pass subprocess arguments as an explicit list.
- Keep execution opt-in through `--execute`; preview must remain the default.
- Fail closed on malformed evidence, invalid signatures, expired certificates,
  dirty source trees, digest mismatches, replay, and unknown actions.
- Do not weaken the one-certificate/one-execution invariant.

## Documentation

- Keep all repository content in English.
- Update the relevant file under `docs/` when changing a public contract.
- Do not claim support for security properties that tests do not demonstrate.
