---
name: announce-release
description: Draft and post a Connexity release announcement to Discord after cutting a CLI or platform release. Use this skill whenever the user types `/announce-release`, or asks to "announce the release", "post the release to Discord", "draft a release announcement", "tell Discord about the new version", "share the new release", or anything that sounds like wanting to publicise a freshly cut release of `connexity-cli` or the platform. Trigger even when the user just says something casual like "ok the release is out, let's tell people" — that's the intended use case. Do not trigger for non-release announcements (blog posts, hiring, generic Discord messages).
---

# announce-release

Drafts a Discord announcement for a Connexity release and posts it to `#announcements` after the developer signs off.

This skill exists because writing release posts is a small, repetitive task that's easy to do badly (too marketing, too dry, missing the link, wrong emoji). It pulls the release notes, drafts in our voice, and waits for an explicit "ship it" before posting. The human stays in the loop for the parts that matter — tone, framing, what actually deserves a highlight.

## Repo context

The Connexity monorepo (`Connexity-AI/connexity`) ships two release artifacts under different tag namespaces. The skill must detect which type it's dealing with from the tag prefix.

| Type | Tag pattern | Source of notes | Upgrade path |
|---|---|---|---|
| **CLI** | `cli-vX.Y.Z` | GitHub Release body + `backend/cli/CHANGELOG.md` | `uv tool upgrade connexity-cli` |
| **Platform** | `vX.Y.Z` (from `v1.0.0` onward) | GitHub Release body (auto-generated) | Rolling deploy / link to product |

The legacy `v0.1.0` tag is an old CLI release — ignore it. If you encounter it as a candidate, skip it and ask for clarification rather than treating it as a platform release.

## Workflow

Follow this in order. Don't skip the confirmation step at the end — there's no automatic posting, ever.

### 1. Find the target release

```bash
gh release list --limit 10
```

Default to the most recent release. If the user named a specific tag, use that. If two or more recent releases look like plausible candidates (e.g. a CLI and a platform release both cut the same day), list them and ask which one.

Detect type from the tag prefix:
- starts with `cli-v` → CLI release
- starts with `v` (and is not `v0.1.0`) → platform release
- anything else → ask the user

### 2. Decide whether it's worth announcing at all

Not every release deserves an announcement. Skip and tell the user if the release is:
- docs-only (`docs:` commits only)
- internal CI/tooling (`chore(ci):`, `chore(deps):` only)
- a re-tag with no real changes

In those cases, say something like "this looks like a docs-only release, probably not worth a Discord post — want me to draft one anyway?" Let the user override.

### 3. Fetch the notes

```bash
gh release view <tag> --json tagName,body,publishedAt,url,name
```

For CLI releases, also pull the matching section from the changelog (everything between the `## [X.Y.Z]` heading and the next `## [` heading):

```bash
sed -n "/## \[X\.Y\.Z\]/,/## \[/p" backend/cli/CHANGELOG.md | sed '$d'
```

If the release body is sparse and you need more context to write meaningful highlights, look at commits since the previous tag of the same type:

```bash
gh api repos/Connexity-AI/connexity/compare/<prev-tag>...<this-tag> --jq '.commits[].commit.message'
```

You're reading these to understand what's in the release, not to enumerate them. Pick the highlights.

### 4. Draft the announcement

Apply the [voice guide](#voice-guide) and the [structures](#structure) below. Use the [worked examples](#examples) as your primary tone anchor — read all three before drafting.

Show the draft to the user inside a fenced code block (so they can see it as it'll appear in Discord, give or take Discord's markdown rendering). Don't post yet.

### 5. Review loop

Wait for the user's response. Match on intent, not exact wording:

| User says (or similar) | Do |
|---|---|
| "ship it", "lgtm", "post it", "send it", "go" | Post it |
| "make it shorter", "drop the second bullet", "no emoji on the headline", any specific edit | Apply the edit, show the new draft, wait again |
| "rewrite", "start over", "try again" | Regenerate from scratch with the same notes |
| "cancel", "nvm", "not yet" | Stop without posting, leave it for later |

When applying edits like "make it shorter", preserve the things the user didn't ask to change (emojis, structure, the link). Only strip emojis if they explicitly say so.

If the user's response is ambiguous (e.g. they reply with just a comment, no clear instruction), ask: "did you want me to apply that as an edit, or post as-is?"

### 6. Post

Required: `CONNEXITY_DISCORD_RELEASE_WEBHOOK`.

Optional override: `CONNEXITY_DISCORD_RELEASE_WEBHOOK_DRY_RUN`. If set, post there instead — this is the staff/test channel and is the right thing to use when iterating on the skill itself or doing a practice run.

Resolution order for each variable: shell environment first, then the repo-root `.env` file. The shell wins if both are set. The `.env` fallback exists so developers who keep secrets in the per-repo `.env` (which is the convention for this repo) don't need to also export them globally.

```bash
# Read VAR from $REPO_ROOT/.env if not set in the environment.
# Strips matching surrounding single or double quotes; takes the last
# matching line if duplicates exist; ignores commented lines.
load_from_env_file() {
  local var_name=$1
  local repo_root
  repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || return
  local env_file="$repo_root/.env"
  [ -f "$env_file" ] || return
  grep -E "^[[:space:]]*${var_name}=" "$env_file" \
    | tail -n1 \
    | sed -E "s/^[[:space:]]*${var_name}=//" \
    | sed -E 's/^"(.*)"$/\1/' \
    | sed -E "s/^'(.*)'$/\1/"
}

WEBHOOK_PROD="${CONNEXITY_DISCORD_RELEASE_WEBHOOK:-$(load_from_env_file CONNEXITY_DISCORD_RELEASE_WEBHOOK)}"
WEBHOOK_DRY_RUN="${CONNEXITY_DISCORD_RELEASE_WEBHOOK_DRY_RUN:-$(load_from_env_file CONNEXITY_DISCORD_RELEASE_WEBHOOK_DRY_RUN)}"
WEBHOOK="${WEBHOOK_DRY_RUN:-$WEBHOOK_PROD}"

curl -s -X POST "$WEBHOOK" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg c "$DRAFT" '{content: $c}')"
```

Use `jq -n --arg` for the JSON body — never string-interpolate the draft into a JSON literal, or backticks/quotes/newlines in the draft will break the request.

After posting, report success and (if Discord returned a message URL via the `?wait=true` trick or response headers) the link to the message. If the webhook returned a non-2xx, surface the error verbatim.

When you tell the user where the webhook came from, distinguish "from your shell environment" vs "from `.env`" — useful when they're surprised about which channel it posted to.

### 7. Webhook missing — walk the user through setup

If `CONNEXITY_DISCORD_RELEASE_WEBHOOK` resolves to empty in **both** the shell environment and the repo-root `.env`, don't just bail. Walk them through it:

> The webhook isn't configured (not in the shell environment and not in the repo-root `.env`), so I can't post yet. Here's how to set it up:
>
> 1. Open Discord, go to the `#announcements` channel.
> 2. Click the gear icon (Edit Channel) → **Integrations** → **Webhooks** → **New Webhook**.
> 3. Name it something like "Release Bot", optionally set an avatar, click **Copy Webhook URL**.
> 4. Pick **one** of these:
>    - **Repo `.env` (recommended for this repo)** — add this line to `<repo-root>/.env`:
>      ```
>      CONNEXITY_DISCORD_RELEASE_WEBHOOK=<paste URL here>
>      ```
>      No quotes needed unless the URL contains shell metacharacters; `.env` is gitignored so the secret stays local.
>    - **Shell export** — add to `~/.zshrc` (or `~/.envrc` if you use direnv):
>      ```
>      export CONNEXITY_DISCORD_RELEASE_WEBHOOK='<paste URL here>'
>      ```
>      then `source ~/.zshrc` (or `direnv allow`).
> 5. Re-run `/announce-release`.
>
> While you're there, consider also setting `CONNEXITY_DISCORD_RELEASE_WEBHOOK_DRY_RUN` for a private staff channel — handy for testing.

Show the draft you'd have posted anyway, so the work isn't wasted. They can copy-paste it manually if they're in a hurry.

---

## Voice guide

Read this before drafting. The [worked examples](#examples) are the ground truth — these rules are descriptive of what makes those examples work, not a substitute.

**Tone:** open-source maintainer talking to users. Confident, not boastful. Pipecat's release posts are the reference (warm, first-person plural, emoji-anchored). Not Langfuse's bot voice.

**Voice rules:**
- "We", not "I". Connexity is a team.
- Short sentences. Cut marketing verbs ("unleash", "supercharge", "empower").
- **No hedge words.** Specifically: `should`, `might`, `hopefully`, `kind of`, `sort of`, `we think`, `we believe`, `pretty much`. These soften claims that don't need softening — if a fix makes setup less confusing, write "Makes setup less confusing", not "Should make setup less confusing". The only valid use of "should" is when describing how something will behave for the reader (e.g. "you should see the new dashboard within an hour"). When you find yourself reaching for a hedge, just delete it and re-read — the sentence is almost always stronger.
- **Don't leak internal terminology, even when it doesn't sound internal.** Words like "ship-blockers", "core functionality", "polish", "L1/L2/L3", or any project-codename-derived term may read as plain English to you but mean nothing to users. Test by asking: "would a user reading the changelog know what this means without context?" If no, rewrite using concrete user-visible terms. (Real example: "covers ship-blockers and polish" should become "catches both regressions and rough-edge issues" or just be cut.)
- Always link the GitHub release URL at the end.
- Always tell the reader the action they can take (`uv tool upgrade ...`, "check it out at ...", or "rolling out over the next few hours").
- Length matches substance: 3 lines for a patch, ~8 for a minor with highlights, ~12 for a major. Never pad.
- A `fix(cli):` headline release gets 🐛, not 🚀. Match the headline emoji to what the release is actually about.

**Emoji palette** (one per highlight max, never two in a row, never emoji-only bullets):

| Emoji | Use for |
|---|---|
| 🚀 | Release headline / new version landing |
| ✨ | New features |
| 🐛 | Bug fixes |
| 🛠 | Tooling, infra, internal-but-user-visible |
| 📚 | Docs |
| ⚡ | Performance |
| 💔 | Breaking changes (always also call out in words, not just emoji) |
| 🎉 | Milestone releases (1.0, 2.0) |
| ❤️ | Contributor thanks at the end |

**Avoid:**
- Listing every commit. Pick highlights, link covers the rest.
- Internal language ("merged the eval-domain refactor"). Translate to user impact.
- Apologising, mentioning blockers, anything self-critical.
- Two emojis in a row.

## Structure

**CLI release:**

```
🚀 connexity-cli vX.Y.Z is out!

<one-sentence what this release is about>

<3-5 emoji-anchored highlight bullets — only if minor or major>

Upgrade: `uv tool upgrade connexity-cli`
Full notes: <github release URL>
```

**Platform release:** same shape, but replace the `Upgrade:` line with either:
- "Rolling out across staging → prod over the next few hours." (default)
- "Live now at `<deployed URL>`." (if the user provides one)

For patch releases, drop the highlights section entirely. Three lines is fine.

## Examples

These are the load-bearing part of this skill. Match their feel.

### Example 1 — patch release (CLI)

Tag: `cli-v1.4.3`
Notes: a single bug fix for a crash when `connexity eval run` was called without a `--config` flag.

Draft:

```
🐛 connexity-cli v1.4.3 is out!

Quick fix: `connexity eval run` no longer crashes when called without `--config` — it now picks up `connexity.yml` from the current directory like it always should have.

Upgrade: `uv tool upgrade connexity-cli`
Full notes: https://github.com/Connexity-AI/connexity/releases/tag/cli-v1.4.3
```

Notes on why: 🐛 not 🚀 because it's a fix release — leading with the rocket would oversell. Three lines plus links. No bullet section because there's nothing to bullet.

### Example 2 — minor release with highlights (platform)

Tag: `v1.6.0`
Notes: new dashboard for eval runs, Postgres → 16 upgrade in the deploy pipeline, faster trace ingestion.

Draft:

```
🚀 Connexity v1.6.0 is rolling out!

We've shipped a new home for eval runs and made trace ingestion meaningfully faster. Highlights:

✨ A new **Eval Runs** dashboard with filterable history, side-by-side run comparison, and export to CSV
⚡ Trace ingestion is ~3× faster on large batches — same volume, lower latency before traces show up
🛠 Internal: Postgres bumped to 16 across staging and prod (no migration needed on your end)

Rolling out across staging → prod over the next few hours.
Full notes: https://github.com/Connexity-AI/connexity/releases/tag/v1.6.0
```

Notes on why: 3 highlights, one emoji each, no two emojis adjacent. The Postgres bump is internal but mentioned because it's the kind of thing operators want to know — note how it's framed as "no migration needed on your end" rather than "we did a migration." User-facing framing.

### Example 3 — major release with breaking changes (CLI)

Tag: `cli-v2.0.0`
Notes: config format moved from `.toml` to `.yml`, removed deprecated `connexity legacy-export` command, new `connexity init` interactive setup.

Draft:

```
🎉 connexity-cli v2.0.0 is out!

A clean break we've been planning for a while. The config format is now YAML, the legacy export command is gone, and there's a proper interactive `connexity init` to get you set up.

💔 **Breaking:** config files moved from `connexity.toml` to `connexity.yml`. Run `connexity migrate-config` to convert in place.
💔 **Breaking:** `connexity legacy-export` has been removed. Use `connexity export` (which has been the preferred form since v1.3).
✨ New `connexity init` walks you through first-time setup interactively
📚 Docs reorganised around the new config format

Upgrade: `uv tool upgrade connexity-cli`
Full notes: https://github.com/Connexity-AI/connexity/releases/tag/cli-v2.0.0
```

Notes on why: 🎉 for the milestone (not 🚀 — major versions earn the party). Both breaking changes are called out in words, not just 💔. Each breaking bullet tells the user exactly what to do. The migrate-config command is the most important sentence in the post — surfaced explicitly, not buried.

---

## Extending this skill

**Adding a new emoji to the palette:** edit the table in [Voice guide](#voice-guide) and ideally add an example use in the [Examples](#examples) section so the model has a reference.

**Tone adjustments:** the examples carry more weight than the rules. If you want the voice to shift, edit an example to reflect the new voice and the model will follow.

**A new release artifact (e.g. an SDK):** add a row to the table at the top, add a structure under [Structure](#structure), and ideally add an example.

## Out of scope (intentional)

This is a Claude-Code-only flow. It assumes a developer is in front of a terminal, drafting and reviewing. There's no CI variant — running this same flow unattended (e.g. as a GitHub Action that fires on release publish) would be a separate surface using the Anthropic API with prompt caching on the system prompt. Build that separately if/when it's wanted; don't bolt it onto this skill.

The skill also doesn't post to anywhere other than Discord. Cross-posting to Twitter/LinkedIn/elsewhere is a different problem (different voice, different structure, different review cycle) and should be its own skill.
