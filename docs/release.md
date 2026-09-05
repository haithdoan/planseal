# Release Process

PlanSeal uses release PRs instead of automatic version bumps on every merge.
This keeps the public version history calm while still preserving a professional
changelog, tag, and artifact trail.

## Version policy before 1.0

PlanSeal is pre-1.0 software. Use small, honest versions:

- Patch releases (`0.1.1`, `0.1.2`) for bug fixes, documentation fixes,
  packaging fixes, and small internal hardening.
- Minor releases (`0.2.0`, `0.3.0`) for user-visible commands, file format
  additions, new verification policies, or meaningful workflow changes.
- Major releases (`1.0.0`) only after the CLI contract, evidence format, and
  certificate semantics are stable enough to support with confidence.

Breaking changes before 1.0 should still be marked clearly in the changelog.
Do not rush major versions for frequent personal iteration.

## Commit policy

Use Conventional Commits:

- `fix:` produces a patch release.
- `feat:` produces a minor release.
- `feat!:` or a `BREAKING CHANGE:` footer marks a breaking release.
- `docs:`, `test:`, `refactor:`, and `chore:` are included in history but do not
  force a version bump unless they carry a breaking-change marker.

## Release flow

1. Merge normal work to `main` with Conventional Commit messages.
2. The Release workflow opens or updates a release PR.
3. Review the release PR. It updates `CHANGELOG.md`, `pyproject.toml`,
   `src/planseal/__init__.py`, and `.release-please-manifest.json`.
4. Merge the release PR when you actually want to publish.
5. The workflow creates the GitHub Release, builds the wheel and source
   distribution, generates `SHA256SUMS`, and uploads the artifacts.

The release workflow also runs the same quality gates as CI before attaching
artifacts to a GitHub Release.

For the first baseline release, create `v0.1.0` from the commit that adds this
release workflow to `main`. The same workflow will build and attach the release
artifacts when the GitHub Release is published. The Release Please bootstrap SHA
points at the initial project commit only so future release PRs do not turn the
first `feat:` commit into an unnecessary `0.2.0`.

## PyPI publishing

PyPI publishing is intentionally opt-in. Configure PyPI Trusted Publishing for
this repository, then set the repository variable `PUBLISH_PYPI` to `true`.

Until that variable exists, releases still produce verified GitHub artifacts but
do not publish to PyPI.

## Owner checklist for public metadata

Repository settings are owner-managed and are not changed by the release
workflow. Before announcing a release, verify:

- the description remains precise and does not overstate the alpha security
  claim;
- the topics include `terraform`, `opentofu`, `infrastructure-as-code`,
  `devsecops`, `supply-chain-security`, `approval-workflow`, `ai-agents`, and
  `cli`;
- private vulnerability reporting remains enabled; and
- the release artifacts, checksums, provenance attestation, and PyPI project
  all identify the same version.
