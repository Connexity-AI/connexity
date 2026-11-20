# Release Cycle

End-to-end walkthrough of how a change ships in this repo — from a merged PR on `main` all the way to a tagged release, deployed services and Discord announcement.

This doc is the **overview**. [`platform.md`](./platform.md) goes deeper on the platform release workflow.

## The release line

| Artifact | Tag pattern | Trigger | Workflow | Artifact destination |
|---|---|---|---|---|
| **Platform** (backend + frontend) | `vX.Y.Z` (from `v1.0.0`) | Manual `workflow_dispatch` | [`release-platform.yml`](../../.github/workflows/release-platform.yml) | GitHub Release + Docker images (already-deployed) |

> The `v0.1.0` and `cli-v*` tags are from a command line tool that is no longer part of the repo. Do not reuse them, and skip them when looking at "the latest `v*` tag".

The platform deploys on every merge to `main` through Cloud Build triggers on Google Cloud Run (see [`deployment.md`](../deployment.md)). Platform tags are **informational** — they label a coherent batch of shipped work, they do not gate deployment.

---

## Platform release cycle

### 0. Deploy already happened

Every merge to `main` that touches `backend/`, `frontend/` or `mcp_server/` is built by Cloud Build and deployed to its Cloud Run service (see [`deployment.md`](../deployment.md)). By the time you cut a platform tag, the code is already live.

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

After a release, post to Discord `#announcements`. This is a manual step — there is no auto-announce.

The fastest path is the `/announce-release` skill ([`.claude/skills/announce-release/SKILL.md`](../../.claude/skills/announce-release/SKILL.md)), which:

1. fetches the latest release with `gh release list`
2. drafts an announcement in the project's voice (rules + worked examples in the skill)
3. waits for your sign-off
4. posts via the `CONNEXITY_DISCORD_RELEASE_WEBHOOK` webhook (resolved from shell env, falling back to repo-root `.env`)

If you're posting manually, the structure to match is:

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
│  Platform                                                       │
│                                                                 │
│  every merge to main                                            │
│    → Cloud Build triggers deploy to Cloud Run                   │
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

- [`platform.md`](./platform.md) — full detail on the platform release workflow, label conventions, and manual overrides
- [`.claude/skills/announce-release/SKILL.md`](../../.claude/skills/announce-release/SKILL.md) — Discord announcement skill (voice rules, worked examples, webhook setup)
- [`.github/release.yml`](../../.github/release.yml) — release-notes category config
