# Release Cycle

End-to-end walkthrough of how a change ships in this repo — from a merged PR on `main` all the way to a tagged release, deployed services, published wheel, and Discord announcement.

This doc is the **overview**. The component-specific docs go deeper:

- [`pypi.md`](./pypi.md) — CLI publishing setup and troubleshooting
- [`platform.md`](./platform.md) — platform release workflow details

## Two release lines, separate namespaces

The repo ships two independent artifact lines from the same monorepo. They use disjoint tag namespaces so a CLI release never triggers a platform release (or vice versa).

| Artifact | Tag pattern | Trigger | Workflow | Artifact destination |
|---|---|---|---|---|
| **CLI** (`connexity-cli`) | `cli-vX.Y.Z` | Merge of release-please PR on `main` | [`release-please.yml`](../../.github/workflows/release-please.yml) → [`publish-pypi.yml`](../../.github/workflows/publish-pypi.yml) | [PyPI](https://pypi.org/project/connexity-cli/) |
| **Platform** (backend + frontend) | `vX.Y.Z` (from `v1.0.0`) | Manual `workflow_dispatch` | [`release-platform.yml`](../../.github/workflows/release-platform.yml) | GitHub Release + Docker images (already-deployed) |

> The legacy `v0.1.0` tag is a pre-namespace-split CLI release. Do not reuse it, and skip it when looking at "the latest `v*` tag".

The platform deploys on every push to `main` via [`deploy-backend.yml`](../../.github/workflows/deploy-backend.yml) and [`deploy-frontend.yml`](../../.github/workflows/deploy-frontend.yml). Platform tags are **informational** — they label a coherent batch of shipped work, they do not gate deployment.

The CLI does not deploy continuously; it ships only when a `cli-v*` tag is pushed.

---

## CLI release cycle

### 1. Develop with Conventional Commits

Anything touching `backend/cli/` or the root `pyproject.toml` is picked up by release-please. Commit messages drive the version bump and changelog grouping:

```
feat(cli): add compare command       # → minor bump, "Features" section
fix(cli): handle SSE timeout          # → patch bump, "Bug Fixes"
perf(cli): reduce polling overhead    # → patch bump, "Performance"
docs(cli): clarify auth flow          # → no bump, "Documentation"
chore(cli): ...                       # → ignored
feat(cli)!: drop python 3.10           # → major bump (note the `!`)
```

Commits that do not touch `backend/cli/` are ignored by release-please regardless of message style.

### 2. release-please opens a Release PR

On every push to `main`, [`release-please.yml`](../../.github/workflows/release-please.yml) runs. If there are unreleased CLI commits, it opens (or updates) a single Release PR titled like `chore(cli): release 0.3.0`. The PR contains:

- the version bump in `pyproject.toml` and `backend/cli/_version.py`
- a new section appended to [`backend/cli/CHANGELOG.md`](../../backend/cli/CHANGELOG.md)
- the manifest update in `.release-please-manifest.json`

Review it like any other PR. If you want to hold a release, just don't merge the PR yet — release-please keeps it up to date with each new commit until you do.

### 3. Merge the Release PR

Merging the Release PR triggers release-please to:

1. push a `cli-vX.Y.Z` tag pointing at the merge commit
2. create a matching GitHub Release with the changelog section as the body

### 4. Tag triggers `publish-pypi.yml`

[`publish-pypi.yml`](../../.github/workflows/publish-pypi.yml) listens for `cli-v*` tags and runs three jobs:

1. **build-and-validate** — `hatch build`, install the wheel in a clean venv, verify `connexity-cli --help` works, and assert that heavy backend deps (`fastapi`, `sqlmodel`, `litellm`, `alembic`, `psycopg`) did **not** leak into the wheel. This is a hard gate.
2. **publish** — upload to PyPI via Trusted Publisher (OIDC, no secrets). Uses the `pypi` GitHub environment.
3. **post-publish-smoke-test** — wait 30s for PyPI to propagate, then `pip install connexity-cli==<version>` and run `--help` against the published wheel.

If any of these fail, the tag and GitHub Release still exist, but PyPI was not updated. See [`pypi.md`](./pypi.md#troubleshooting) for fixing each failure mode.

### 5. Verify

```bash
pip install connexity-cli==<version>
connexity-cli --version
gh release view cli-v<version>
```

### Manual override (if release-please is blocked)

```bash
# In pyproject.toml: bump version, then:
git add pyproject.toml backend/cli/_version.py backend/cli/CHANGELOG.md
git commit -m "chore(cli): release X.Y.Z"
git tag cli-vX.Y.Z
git push && git push --tags
```

The `publish-pypi.yml` workflow does not care how the tag was created.

---

## Platform release cycle

### 0. Deploy already happened

Every merge to `main` runs the build-and-push Docker workflow ([`publish-docker-ghcr.yml`](../../.github/workflows/publish-docker-ghcr.yml)) on the release event, and the deploy workflows ([`deploy-backend.yml`](../../.github/workflows/deploy-backend.yml) / [`deploy-frontend.yml`](../../.github/workflows/deploy-frontend.yml)) SSH into the host and `docker compose up -d` the new image. By the time you cut a platform tag, the code is already live.

The tag exists to label "this batch shipped" — for support, ops, and the [GitHub Releases](https://github.com/Connexity-AI/connexity/releases) page.

### 1. Label the PRs that are about to be in the release

The release notes are auto-generated from PR labels via [`.github/release.yml`](../../.github/release.yml). Categories:

| Label on PR | Section in release notes |
|---|---|
| `breaking-change` | ⚠️ Breaking Changes |
| `feature`, `enhancement` | 🚀 Features |
| `bug`, `fix` | 🐛 Bug Fixes |
| `documentation`, `docs` | 📚 Documentation |
| `chore`, `refactor`, `test`, `ci` | 🧰 Maintenance |
| (no recognised label) | Other Changes |
| `ignore-for-release`, `dependencies` | excluded entirely |

Dependabot and `github-actions` author PRs are excluded by default.

If you forgot to label a PR, label it before cutting the release — the workflow reads the current label state at run time.

### 2. Trigger the workflow

Go to [Actions → Release Platform](https://github.com/Connexity-AI/connexity/actions/workflows/release-platform.yml) and click **Run workflow**:

- **Bump type**: `patch` / `minor` / `major`. The workflow finds the latest `vX.Y.Z` tag (excluding `cli-v*` and the legacy `v0.x`), increments based on the bump, and refuses to overwrite an existing tag.
- **Pre-release** (optional): marks the GitHub Release as a pre-release.

The workflow refuses to run on any branch other than `main`. If you need to release from a non-`main` commit (hotfix from a tag), use the manual override at the bottom of this section.

### 3. What the workflow does

1. computes `vX.Y.Z` from the latest platform tag (first release bootstraps at `v1.0.0` regardless of bump input)
2. creates and pushes the tag
3. opens a GitHub Release titled `vX.Y.Z` with `--generate-notes`, sourced from PRs between the previous platform tag and `HEAD`

### 4. Docker images get re-tagged

[`publish-docker-ghcr.yml`](../../.github/workflows/publish-docker-ghcr.yml) runs on `release: published`. It rebuilds and pushes both `<repo>-backend` and `<repo>-frontend` images to GHCR tagged with the release tag, plus `latest`. This gives ops a stable image ref per release for rollbacks.

### Manual override (hotfix from non-main commit)

```bash
git tag -a vX.Y.Z -m "Platform release vX.Y.Z"
git push origin vX.Y.Z
gh release create vX.Y.Z --generate-notes --target <commit-sha> --title vX.Y.Z
```

This bypasses the `main`-only check. Use sparingly — the auto-generated notes will still compare against the previous platform tag, so out-of-order tags can produce confusing diffs.

---

## Announcement

After either release type, post to Discord `#announcements`. This is a manual step — there is no auto-announce.

The fastest path is the `/announce-release` skill ([`.claude/skills/announce-release/SKILL.md`](../../.claude/skills/announce-release/SKILL.md)), which:

1. fetches the latest release with `gh release list`
2. detects CLI vs platform from the tag prefix
3. drafts an announcement in the project's voice (rules + worked examples in the skill)
4. waits for your sign-off
5. posts via the `CONNEXITY_DISCORD_RELEASE_WEBHOOK` webhook (resolved from shell env, falling back to repo-root `.env`)

If you're posting manually, the structure to match is:

### CLI release

```
🚀 connexity-cli vX.Y.Z is out!

<one-sentence summary>

✨ <highlight 1>
🐛 <highlight 2>
⚡ <highlight 3>

Upgrade: `uv tool upgrade connexity-cli`
Full notes: https://github.com/Connexity-AI/connexity/releases/tag/cli-vX.Y.Z
```

### Platform release

```
🚀 Connexity vX.Y.Z is rolling out!

<one-sentence summary>

✨ <highlight 1>
⚡ <highlight 2>
🛠 <highlight 3>

Rolling out across staging → prod over the next few hours.
Full notes: https://github.com/Connexity-AI/connexity/releases/tag/vX.Y.Z
```

### Voice rules (short version)

- "We", not "I". Short sentences. No marketing verbs.
- No hedge words (`should`, `might`, `hopefully`, "kind of", "we think") — delete them.
- Don't leak internal terminology. Frame everything as user impact.
- Length matches substance: ~3 lines for a patch, ~8 for a minor, ~12 for a major.
- Match the headline emoji to the release: 🐛 for fix-only, 🎉 for milestones (1.0, 2.0), 🚀 default.
- One emoji per bullet. Never two in a row. Never emoji-only bullets.
- Always link the GitHub Release URL.
- Always state the user action (`uv tool upgrade ...`, or "rolling out over the next few hours").

The full guide and worked examples live in [`SKILL.md`](../../.claude/skills/announce-release/SKILL.md#voice-guide).

### Skip the announcement when…

- docs-only release (`docs:` commits only)
- internal CI/tooling only (`chore(ci):`, `chore(deps):`)
- a re-tag with no real changes

Use judgement. A silent release is fine if there's nothing for users to act on.

---

## Quick reference

```
┌─────────────────────────────────────────────────────────────────┐
│  CLI                                                            │
│                                                                 │
│  feat(cli): … on main                                           │
│    → release-please opens Release PR                            │
│    → merge PR                                                   │
│    → tag cli-vX.Y.Z + GitHub Release                            │
│    → publish-pypi.yml: build → validate → PyPI → smoke test     │
│    → /announce-release                                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  Platform                                                       │
│                                                                 │
│  every merge to main                                            │
│    → deploy-backend.yml + deploy-frontend.yml deploy live       │
│                                                                 │
│  when ready to label a batch:                                   │
│    → Actions → Release Platform → Run workflow (patch/minor/    │
│       major)                                                    │
│    → tag vX.Y.Z + GitHub Release (auto-notes from PR labels)    │
│    → publish-docker-ghcr.yml re-tags images on GHCR             │
│    → /announce-release                                          │
└─────────────────────────────────────────────────────────────────┘
```

## See also

- [`pypi.md`](./pypi.md) — PyPI Trusted Publisher setup, troubleshooting wheel/validation/smoke-test failures
- [`platform.md`](./platform.md) — full detail on the platform release workflow, label conventions, and manual overrides
- [`.claude/skills/announce-release/SKILL.md`](../../.claude/skills/announce-release/SKILL.md) — Discord announcement skill (voice rules, worked examples, webhook setup)
- [`.github/release.yml`](../../.github/release.yml) — release-notes category config
- [`release-please-config.json`](../../release-please-config.json) — release-please config for the CLI package
