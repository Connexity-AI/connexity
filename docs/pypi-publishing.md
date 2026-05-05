# PyPI Publishing Setup

This document covers the one-time setup required to enable automated publishing of the `connexity-cli` package to PyPI.

## Overview

The publishing pipeline uses two GitHub Actions workflows:

1. **Release Please** (`.github/workflows/release-please.yml`) — Watches merges to `main` that touch `backend/cli/` or the root `pyproject.toml`. Automatically opens and maintains a Release PR with changelog and version bumps. When merged, creates a git tag and GitHub Release.

2. **Publish to PyPI** (`.github/workflows/publish-pypi.yml`) — Triggered by `cli-v*` tags (component-prefixed so they don't collide with the platform's plain `v*` tags). Builds the wheel, validates it, publishes to PyPI via Trusted Publisher (OIDC), and runs a post-publish smoke test.

> **Tag namespaces in this repo**
> - `cli-vX.Y.Z` — CLI package release (this doc)
> - `vX.Y.Z` — platform release, see [`platform-releases.md`](./platform-releases.md)
> - `v0.1.0` (no prefix) — historical CLI release predating the namespace split; do not reuse.

## One-Time Setup: PyPI Trusted Publisher

Trusted Publishers use OpenID Connect (OIDC) so the GitHub Actions workflow can publish to PyPI without storing API tokens as secrets.

### Steps

1. Go to [pypi.org](https://pypi.org) and log in (or create an account).

2. **For a new package** (first-ever publish):
   - Go to https://pypi.org/manage/account/publishing/
   - Under "Add a new pending publisher", fill in:
     - **PyPI project name**: `connexity-cli`
     - **Owner**: `Connexity-AI`
     - **Repository**: `connexity`
     - **Workflow name**: `publish-pypi.yml`
     - **Environment name**: `pypi`
   - Click "Add"

3. **For an existing package** (already uploaded at least once):
   - Go to https://pypi.org/manage/project/connexity-cli/settings/publishing/
   - Under "Add a new publisher", fill in the same fields as above
   - Click "Add"

### GitHub Environment Setup

The publish workflow references a GitHub environment called `pypi`. Create it:

1. Go to https://github.com/Connexity-AI/connexity/settings/environments
2. Click "New environment"
3. Name it `pypi`
4. Optionally add deployment protection rules (e.g., required reviewers)
5. Save

No secrets need to be added to this environment — OIDC handles authentication.

## How Releases Work

### Day-to-Day Development

Use [Conventional Commits](https://www.conventionalcommits.org/) for changes to the CLI:

```
feat(cli): add compare command
fix(cli): handle timeout in SSE streaming
docs(cli): update usage examples
perf(cli): reduce polling interval overhead
```

Commits that don't match these patterns (or don't touch `backend/cli/`) are ignored by Release Please.

### Release Flow

```
1. Merge PRs to main
   └── (Release Please detects changes to backend/cli/)
2. Release Please creates/updates a "Release PR"
   └── Contains: version bump in pyproject.toml, backend/cli/CHANGELOG.md updates
3. Developer reviews and merges the Release PR
   └── Release Please creates git tag (cli-v0.2.0) and GitHub Release
4. Tag push triggers publish-pypi.yml
   └── Build → Pre-publish validation → Publish → Post-publish smoke test
5. pip install connexity-cli gets the new version
```

### Where the changelog lives

- **In the repo:** [`backend/cli/CHANGELOG.md`](../backend/cli/CHANGELOG.md) — release-please writes to it on every Release PR.
- **On GitHub:** the [Releases page](https://github.com/Connexity-AI/connexity/releases?q=cli-v) auto-mirrors each Release PR's CHANGELOG entry.
- **On PyPI:** PyPI does not natively render per-release changelogs. The `[project.urls]` section in `pyproject.toml` exposes `Changelog` and `Releases` links in the project's PyPI sidebar — clicking them sends users to the locations above.

### Manual Override

If you need to publish outside the Release Please flow:

```bash
# Bump version in pyproject.toml manually, then:
git add pyproject.toml
git commit -m "chore: release 0.3.0"
git tag cli-v0.3.0
git push && git push --tags
```

## Verifying a Release

After a publish completes:

```bash
# Check the version on PyPI
pip install connexity-cli==<version>
connexity-cli --version

# Check the GitHub Release
gh release view cli-v<version>
```

## Troubleshooting

### "Trusted publisher not configured"

The OIDC publisher on pypi.org hasn't been set up, or the workflow name / environment name doesn't match. Double-check the values in the PyPI publisher config match exactly: workflow `publish-pypi.yml`, environment `pypi`.

### Pre-publish validation fails

The built wheel includes dependencies it shouldn't (FastAPI, SQLModel, etc.). Check that the top-level `pyproject.toml` only lists CLI dependencies and that `[tool.hatch.build.targets.wheel]` only includes `backend/cli`.

### Post-publish smoke test fails

PyPI propagation can take up to a minute. The workflow waits 30 seconds by default. If this is consistently failing, increase the sleep duration in the workflow.
