# Document Cloud Run deploys and delete the dead deploy workflows

- **Owner:** Dmytro
- **Slice:** none (infrastructure; set up outside the repo, documented here)
- **Design:** No UI change.
- **MCP:** None needed: no feature changes; the MCP server is now deployed (see Changes).

## Goal

The repo says truthfully how code reaches production. Today `docs-internal/releases/`
says GitHub Actions deploy over SSH on every push to `main`. Those workflows wait for
build workflows that no longer exist and have not run in months. Deploys now go
through Cloud Build to Google Cloud Run, set up on 2026-11-12.

## Changes

Already done outside the repo on 2026-11-12, recorded here (Dmytro approved each step):

- The Cloud Build triggers for `connexity-backend` and `connexity-ui` (europe-west1) now
  fire on `main`, each only when its folder changes; they watched an old feature branch.
- The backend reads its database from Secret Manager, pointing at the restored Supabase
  project; the 1.x schema there was wiped and the rebuild's migrations applied
  (`0009_check_runs_and_issues`).
- A new `connexity-mcp` service and trigger (`mcp_server/**`); the backend issues OAuth
  tokens for it.
- The backend's keys moved from plain environment variables to Secret Manager; the
  frontend's unused key variables were removed.

In the repo:

- **New `docs-internal/deployment.md`:** services, triggers, secrets, the database, and
  what to know (migrations on start, `/healthz` reserved by Cloud Run).
- **Deleted `.github/workflows/deploy-backend.yml` and `deploy-frontend.yml`** (Dmytro
  approved deleting them).
- **`docs-internal/releases/cycle.md` and `platform.md`** point to Cloud Run instead of
  the deleted workflows; `docs-internal/README.md` lists the new doc.

## Decisions

- Google Cloud Run, connected to the repository, in `europe-west1` next to the Supabase
  database in Paris (Dmytro: "Can we just connect repo to Google Cloud Run?"; "Approve,
  keep europe").
- The database is the existing Supabase project, wiped of 1.x data (Dmytro: "Yes, wipe
  it").

## Done when

- `make check` passes.
- No doc in `docs-internal/` refers to the deleted workflows.
- `deployment.md` names no secret value.

## Out of scope

- The `railway.toml` files and `docs-internal/railway-template.md`; whether Railway stays
  an option is a separate decision.
- `publish-docker-ghcr.yml` and the release workflows, which still serve releases.
- A staging environment.

## Risks

- Every merge to `main` that touches a service is live within minutes, with no staging.
- `JWT_SECRET_KEY` also derives the OAuth signing key; rotating it logs everyone out and
  invalidates MCP tokens. The doc says so.

## Outcome

### Deviations from the plan

- The plan was written after Dmytro approved the work in conversation ("Yes, do both"),
  not before; the cloud steps it records were each approved as they ran.

### Check results

| Step | Result |
|---|---|
| `make check` | see the pull request's CI (docs and workflow deletions only) |

Checked against the live services on 2026-11-12:

| Request | Expected | Got |
|---|---|---|
| `GET` backend `/` | 200 | 200 |
| `GET` frontend `/` | redirect to sign-in | 307 |
| `POST` MCP `/mcp` without a token | 401 | 401 |
| MCP `/.well-known/oauth-protected-resource` | names the backend as authorization server | yes |
| Backend `/.well-known/jwks.json` after the key moved to Secret Manager | the same Ed25519 key | yes |
| Supabase `alembic_version` | `0009_check_runs_and_issues` | yes, 29 tables |

### Not done

- No staging environment.
- The backend does not yet keep an instance running for continuous call sync; that
  ships with the sync feature.
- `railway.toml` files and the Railway template doc are untouched.
