# Contributing to Connexity

Thanks for your interest in contributing! Connexity is built in the open and we welcome issues, ideas, and pull requests of all sizes.

## Ways to contribute

- **Report a bug** — open an [issue](https://github.com/Connexity-AI/connexity/issues) with reproduction steps, expected vs. actual behavior, and your environment (OS, Docker / Node / Python versions).
- **Request a feature** — start a thread in [GitHub Discussions](https://github.com/Connexity-AI/connexity/discussions). Describe the use case before the implementation — it's much easier to align on a solution that way.
- **Improve the docs** — typos, missing pieces, or clearer explanations are always appreciated. PRs against [`docs/`](./docs) and the README are welcome.
- **Send a pull request** — bug fixes, small features, and well-scoped refactors are great first contributions. For larger changes, please open a discussion or issue first so we can agree on the direction.

## Development setup

The fastest way to get a working environment is the local dev mode (DB in Docker, app runs natively):

```bash
git clone https://github.com/Connexity-AI/connexity.git
cd connexity

cp .env.example .env
cp frontend/apps/web/.env.example frontend/apps/web/.env

make install   # installs Python (uv) and frontend (pnpm) dependencies
make db        # starts Postgres + Adminer in Docker
make db-seed   # runs Alembic migrations and seeds a superuser
```

Then run the backend and frontend in two terminals:

```bash
make dev        # FastAPI on http://localhost:8000
make dashboard  # Next.js on http://localhost:3000
```

Run `make help` to see all available targets (lint, format, tests, client codegen, etc.).

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [uv](https://docs.astral.sh/uv/) for Python dependency management
- [Node.js](https://nodejs.org/) and [pnpm](https://pnpm.io/) for the frontend
- GNU Make

## Quality checks

Before opening a PR, please run the relevant checks locally.

### Backend (`backend/`)

```bash
cd backend
uv run ruff check app cli scripts        # lint
uv run ruff format --check app cli scripts  # format check
uv run pyright                            # type check
uv run pytest app/tests -v                # tests
```

### Frontend (`frontend/`)

```bash
cd frontend
pnpm lint                  # ESLint
pnpm turbo check-types     # TypeScript type check
```

### After backend route or model changes

If you changed any FastAPI route, request/response model, or anything else that affects the OpenAPI schema, regenerate the typed frontend client:

```bash
bash scripts/generate-client.sh
```

CI will fail if the generated client is stale. Never edit files in `frontend/apps/web/src/client/` by hand — they are auto-generated.

## Coding conventions

We keep the codebase small and consistent. The full conventions are in [`CLAUDE.md`](./CLAUDE.md), but the highlights are:

- **Python 3.12+**, type hints on every public signature, no `Any` unless interfacing with untyped libraries, `ruff` for lint/format, `pyright` for type checking.
- **Database logic in `crud.py`**, never inline in route handlers.
- **TypeScript strict mode**, functional React components, named exports, Tailwind v4, ShadcnUI.
- **No barrel files**, no default exports for components.
- **Server actions** for form submissions; **Zod** for validation.

## Pull request guidelines

- Keep PRs focused — one logical change per PR makes review faster and revert easier.
- Include a short description of **what** changed and **why**. Link any related issue or discussion.
- Add or update tests when you change behavior.
- Make sure CI is green before requesting review.
- For UI changes, a screenshot or short screen recording in the PR description is very helpful.

## Commit messages

Use clear, imperative commit messages, e.g. `Add support for Vapi agent import` or `Fix off-by-one in test case batcher`. Squash noisy WIP commits before merge.

## Reporting security issues

Please do **not** open public GitHub issues for security vulnerabilities. Email [dmitry@spacestep.ca](mailto:dmitry@spacestep.ca) and we will respond as soon as possible.

## License

By contributing to Connexity, you agree that your contributions will be licensed under the [MIT License](./LICENSE).

---

Questions? Join us on [Discord](https://discord.gg/Gj47DqWq) or start a thread in [GitHub Discussions](https://github.com/Connexity-AI/connexity/discussions). Thanks for helping make Connexity better!
