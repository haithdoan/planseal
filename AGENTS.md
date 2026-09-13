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

## Natural-language auto-work triggers

When the owner says `auto-work: <goal>`, `hd-work: <goal>`, `background
work: <goal>`, `overnight work: <goal>`, or otherwise asks for autonomous
local work on this repo, route it through the separate `hd-work-os`
project's `hd-work` CLI rather than improvising an ad hoc flow:

```bash
HD_WORK_OS_PROJECT="${HD_WORK_OS_PROJECT:-../hd-work-os}"
uv run --project "$HD_WORK_OS_PROJECT" hd-work \
  --db "$HD_WORK_OS_PROJECT/.hd-work-os/state.db" \
  ask "<goal>" --repo planseal --path <scope>
uv run --project "$HD_WORK_OS_PROJECT" hd-work \
  --db "$HD_WORK_OS_PROJECT/.hd-work-os/state.db" work
```

`../hd-work-os` is the default sibling checkout path; set `HD_WORK_OS_PROJECT`
only if this repo's checkout does not sit next to `hd-work-os/`.

Use `hd-work resume <work_item_id>` to continue an item a provider adapter
paused (`PAUSED`) for owner review, `hd-work status` / `hd-work inbox` to
report progress. Any R2/R3/R4, destructive, or external-write action still
stops for owner approval per the safety boundaries below — `hd-work work`
never bypasses them, never invokes a real Terraform/OpenTofu apply, and
never runs `git push` on its own. Never say "Level 3" to the owner; it is
internal terminology. Full contract: `hd-work-os/docs/usage/hd-work.md`.

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
