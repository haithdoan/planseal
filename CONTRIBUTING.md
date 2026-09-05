# Contributing

Thank you for helping make infrastructure approval safer and easier to audit.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Verification

```bash
ruff check .
ruff format --check .
mypy src
pytest --cov=planseal --cov-report=term-missing
python -m build
```

Tests must never execute a real Terraform or OpenTofu apply. Mock the executor
boundary and use synthetic names and values in fixtures.

## Pull requests

- Keep changes focused and explain the threat or use case they address.
- Add tests for every changed security invariant.
- Update public documentation when a CLI or wire contract changes.
- Use Conventional Commits, for example `fix: reject expired certificates`.
- Do not include plans, state, credentials, internal URLs, customer names,
  private repository names, or environment identifiers.
