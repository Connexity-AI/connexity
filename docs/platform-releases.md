# Platform Releases

This document covers how to cut a versioned release of the Connexity platform (backend + frontend), independent of the [`connexity-cli` PyPI release flow](./pypi-publishing.md).

## Why platform releases exist

The platform deploys continuously on push-to-`main` (see `deploy-backend.yml` / `deploy-frontend.yml`), so platform tags are not required for code to ship — they are *informational*:

- mark "what shipped together" for change-log purposes
- give support and ops a stable label to refer to ("the bug appeared in `v1.4.0`")
- generate a clean, browseable list of releases on [GitHub Releases](https://github.com/Connexity-AI/connexity/releases)

Cut one whenever you have a coherent batch of changes you want to label.

## Tag namespace

| Tag pattern | Meaning |
|---|---|
| `vX.Y.Z` | Platform release (this doc) |
| `cli-vX.Y.Z` | CLI package release on PyPI (see [`pypi-publishing.md`](./pypi-publishing.md)) |
| `v0.1.0` (no prefix) | Historical CLI release pre-dating the namespace split. Do not reuse. |

Platform releases start at **`v1.0.0`** to avoid colliding with the `v0.1.0` historical tag.

## How to cut a release

Trigger the **Release Platform** workflow manually:

1. Go to [Actions → Release Platform](https://github.com/Connexity-AI/connexity/actions/workflows/release-platform.yml).
2. Click **Run workflow**.
3. Pick the bump type:
   - `patch` — bug fixes only (`v1.2.3` → `v1.2.4`)
   - `minor` — new features, backward-compatible (`v1.2.3` → `v1.3.0`)
   - `major` — breaking changes (`v1.2.3` → `v2.0.0`)
4. Optionally tick **Mark as pre-release**.
5. Click **Run workflow**.

Within ~30 seconds the workflow:

1. Computes the next `vX.Y.Z` based on the latest existing platform tag.
2. Creates and pushes the tag.
3. Opens a GitHub Release titled `vX.Y.Z` with auto-generated notes — formatted by [`.github/release.yml`](../.github/release.yml) into Features / Bug Fixes / Documentation / Maintenance / Other Changes sections, sourced from PR labels and titles since the previous platform tag.

The tag and release are visible at https://github.com/Connexity-AI/connexity/releases.

## Conventions for clean release notes

Auto-generated notes group PRs by the labels in [`.github/release.yml`](../.github/release.yml). To keep notes useful:

- **Label your PRs** — `feature`, `bug`, `documentation`, `chore`, etc. PRs without a recognised label fall under "Other Changes".
- **Use clear PR titles** — they're the bullet text in the release notes.
- **Add `breaking-change`** to any PR that requires consumers to update.
- **Add `ignore-for-release`** to PRs you'd rather hide (auto-merged dependency bumps, internal refactors that don't affect users).

## What the release does NOT do

- Does not deploy. Deployment continues to happen on every merge to `main` via the existing deploy workflows.
- Does not modify `pyproject.toml` or any version file. The platform has no installable artifact, so no in-source version field needs bumping.
- Does not write a `CHANGELOG.md` file. GitHub Releases is the source of truth — keeping a duplicate file in the repo would just rot.
- Does not affect CLI releases. CLI publishing uses release-please + a separate `cli-v*` tag namespace.

## Manual override

If you need to cut a release by hand (e.g., from a tag on a non-main commit for a hotfix):

```bash
git tag -a v1.2.4 -m "Platform release v1.2.4"
git push origin v1.2.4
gh release create v1.2.4 --generate-notes --target <commit-sha> --title v1.2.4
```

The `release-platform.yml` workflow refuses to run from any branch other than `main` to prevent accidental release tags off feature branches — manual overrides bypass this check, so use sparingly.
