# Project Identity and Distribution

PlanSeal is distributed as an open-source project under the MIT License. The
license allows broad use, modification, redistribution, sublicensing, and
commercial use, as long as downstream copies preserve the required copyright
and license notice.

## Official Channels

Use these channels to verify that a release came from the upstream project:

- Source repository: <https://github.com/haithdoan/planseal>
- Python package: <https://pypi.org/project/planseal/>
- GitHub releases: <https://github.com/haithdoan/planseal/releases>
- Security reports: <https://github.com/haithdoan/planseal/security/advisories/new>

Release artifacts are built by GitHub Actions, checked before publication, and
attached to the matching GitHub Release. PyPI releases are published through
PyPI Trusted Publishing rather than a long-lived API token.

## Attribution

Downstream copies and substantial portions of the project must preserve the
copyright notice and MIT License text, as required by the license.

The canonical copyright notice is:

```text
Copyright (c) 2026 Hai Doan
```

## Fork Branding

Forks and derived projects are welcome under the MIT License. To avoid confusing
users, forks should not present themselves as the official PlanSeal project
unless they are maintained by the upstream maintainer.

Recommended fork behavior:

- keep the original license and copyright notice;
- clearly identify the fork maintainer;
- link back to the upstream project when practical; and
- use a distinct package name if publishing a modified distribution.

## Authenticity Checks

Before installing or reporting issues, confirm that the package or source tree
matches the official channels above. If a package, repository, or release claims
to be PlanSeal but does not match those channels, treat it as an unofficial
downstream distribution.
