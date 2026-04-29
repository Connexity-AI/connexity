<p align="center">
  <a href="https://connexity.ai">
    <img src="./assets/logo.png" alt="Connexity" width="200" />
  </a>
</p>

<div align="center">
   <div>
      <h3>
         <a href="https://connexity.ai">
            <strong>Website</strong>
         </a> ·
         <a href="https://github.com/Connexity-AI/connexity-evals">
            <strong>GitHub</strong>
         </a> ·
         <a href="./docs">
            <strong>Docs</strong>
         </a> ·
         <a href="https://discord.gg/Gj47DqWq">
            <strong>Discord</strong>
         </a>
      </h3>
   </div>

   <div>
      <a href="./docs"><strong>Documentation</strong></a> ·
      <a href="https://github.com/Connexity-AI/connexity-evals/issues"><strong>Report Bug</strong></a> ·
      <a href="https://github.com/Connexity-AI/connexity-evals/discussions"><strong>Feature Request</strong></a> ·
      <a href="https://github.com/Connexity-AI/connexity-evals/commits/main"><strong>Changelog</strong></a>
   </div>
   <br/>
   <span>Connexity uses <a href="https://github.com/Connexity-AI/connexity-evals/discussions"><strong>GitHub Discussions</strong></a> and <a href="https://discord.gg/Gj47DqWq"><strong>Discord</strong></a> for support and feature requests.</span>
   <br/>
   <br/>
</div>

<p align="center">
   <a href="./LICENSE">
      <img src="https://img.shields.io/badge/License-MIT-orange.svg" alt="MIT License">
   </a>
   <a href="https://discord.gg/Gj47DqWq" target="_blank">
      <img src="https://img.shields.io/badge/Discord-Join%20us-5865F2?logo=discord&logoColor=white" alt="Join us on Discord">
   </a>
   <a href="https://connexity.ai" target="_blank">
      <img src="https://img.shields.io/badge/Made%20with%20%E2%9D%A4%20by-Connexity-orange" alt="Made with love by Connexity">
   </a>
</p>

Connexity is an **open-source evaluation and observability platform for voice AI agents**. It closes the loop between development and production: build or connect an agent, refine prompts with an AI co-pilot, generate realistic test cases from the agent's own configuration and real conversations, run evaluations locally or in CI, inspect production calls, and promote better versions with confidence — all from one place.

## 🌀 Core Features

Connexity is built around a single closed loop for developing voice AI agents — **connect or build → edit → test → evaluate → observe → iterate**.

- **Agent versioning** — work freely on a draft of your agent's prompt, tools, and configuration. When you're happy with the changes, capture them as an immutable version with an optional changelog. Past versions are kept so you can compare runs, roll back, or branch off them.

- **AI-assisted prompt editor** — collaborate with an AI agent that knows your current prompt, tools, and past evaluation results to draft, critique, and rewrite prompts faster than you would by hand.

- **Test case generation** — Connexity reads the agent's own system prompt, tool definitions, and production conversations to generate diverse multi-turn test cases. Each generated case ships with a persona, an opening message, expected outcomes for the judge, and the tool calls the agent is expected to make. You can also use AI to draft or refine individual test cases from natural-language instructions.

- **Agent evaluation** — run multi-turn simulations against your agent, scored by an LLM-as-judge with custom metrics, full transcripts, tool-call traces, and per-turn cost / token accounting.

- **Production observability** — connect real-world call sources, review production conversations alongside evaluation results, and turn missed edge cases into regression tests before they happen again.

- **CLI for CI/CD** — automate evaluation in GitHub Actions and other pipelines: every PR can run a regression suite against your agent and fail the build on quality, cost, or latency regressions.

- **Agent deployment workflow** — manage environments for connected agents today, with push-to-platform deployment on the roadmap so the same artifact you evaluated is the one that goes live.

Together these pieces form a **closed development loop**: connect or build → edit → test → evaluate → observe, then start over with real-world data.

## 🛠 Deploy Connexity

Run Connexity on your own infrastructure. Use Docker for a full self-hosted stack, or run the app locally while keeping the database in Docker for development.

### Local development

**Option A** runs the app on your machine with the database and migrations wired through Make; **Option B** runs the full stack in Docker Compose. Pick one workflow below.

```bash
# Get a copy of the latest Connexity repository
git clone https://github.com/Connexity-AI/connexity-evals.git
cd connexity-evals

# Copy environment variables
cp .env.example .env
cp frontend/apps/web/.env.example frontend/apps/web/.env

# Install dependencies (Python + frontend)
make install

# Start database
make db

# Run migrations
make db-upgrade

# Start backend (in one terminal)
make dev

# Start frontend (in another terminal)
make dashboard
```

### Option B — Everything in Docker

```bash
# 1. Copy environment variables
cp .env.example .env
cp frontend/apps/web/.env.example frontend/apps/web/.env

# 2. Start all services (frontend, backend, database, database browser)
make docker-up
```

Then open the dashboard at [http://localhost:3000](http://localhost:3000).

### VM

Run Connexity on a single Virtual Machine using the same Docker Compose stack. Suitable for small teams and internal deployments — clone the repo on your VM, set production secrets in `.env`, and run `make docker-up`. The repository also includes Docker build and deploy workflows for teams that want to publish their own images. See the [`docs/`](./docs) folder for hardening and configuration tips.

## 🪢 Integrations

Connexity is designed to live alongside the voice AI platforms you already use. Retell support is available in beta, and more first-class adapters are in active development.

### Voice platforms

| Platform        | Status         | Description                                                                                                                  |
| --------------- | -------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **Retell**      | *Beta*         | Connect your Retell workspace, browse agents, link environments, and sync production calls into Connexity.                   |
| **Vapi**        | *Planned*      | Import agents from your Vapi workspace into Connexity, version and evaluate them, then push updates back to Vapi.            |
| **ElevenLabs**  | *Planned*      | Two-way sync with ElevenLabs Conversational AI agents, including prompt, tools, and configuration.                           |

> **Want one of these sooner?** Vote in [GitHub Discussions](https://github.com/Connexity-AI/connexity-evals/discussions) or join us on [Discord](https://discord.gg/Gj47DqWq).

### Bring your own agent

You don't need to be on one of the integrated platforms to use Connexity. There are two ways to plug your agent in:

- **Platform-side simulation** — define your agent directly in Connexity (system prompt, tools, model, provider, temperature) and Connexity will simulate it end-to-end alongside the user simulator using its built-in agent runner. No separate hosting required.
- **External URL** — point Connexity at any agent that speaks the [Agent HTTP contract](./docs/agent-contract.md) — an OpenAI-compatible chat messages payload over a single `POST /agent/respond` endpoint. Framework-agnostic; see [`examples/integrations/`](./examples/integrations) for runnable Python and LangChain starters.

### CLI *(in development)*

A standalone CLI package is in active development to make it easy to drive evaluations from CI (e.g. GitHub Actions). For now, the CLI ships inside the backend and can be invoked via `make cli ARGS="..."`.

## 🚀 Quickstart

The end-to-end developer loop in Connexity looks like this:

> **Run the platform → Connect or build an agent → Generate test cases → Run an evaluation → Inspect results and production calls.**

### 1️⃣ Run the platform

The fastest way is the all-in-one Docker stack:

```bash
git clone https://github.com/Connexity-AI/connexity-evals.git
cd connexity-evals

cp .env.example .env
cp frontend/apps/web/.env.example frontend/apps/web/.env

make docker-up
```

| Service   | URL                                                            |
| --------- | -------------------------------------------------------------- |
| Dashboard | [http://localhost:3000](http://localhost:3000)                 |
| API docs  | [http://localhost:8000/docs](http://localhost:8000/docs)       |
| Database browser | [http://localhost:8083](http://localhost:8083)          |

Sign in with the seeded superuser (configured in `.env`):

| Field    | Value               |
| -------- | ------------------- |
| Email    | `admin@example.com` |
| Password | `password`          |

> Prefer running the app natively with the DB in Docker? Use `make install && make db && make db-upgrade && make dev` and `make dashboard` in another terminal. See `make help` for all targets.

### 2️⃣ Bring an agent into Connexity

Pick one:

- **Connect Retell** *(beta)* — connect your Retell workspace, choose the agent/environment you want to observe, and bring production calls into Connexity.
- **Import from Vapi or ElevenLabs** *(planned)* — connect your account and pull an existing agent, including its prompt, tools, and configuration.
- **Build from scratch with the AI prompt editor** — start a new agent and let the AI co-pilot help you draft the system prompt, tools, and persona.
- **Point at any HTTP endpoint** — register an existing agent that implements the [Agent HTTP contract](./docs/agent-contract.md). See [`examples/integrations/`](./examples/integrations) for runnable Python and LangChain starters.

Edits are kept as a draft on the agent. When you're ready, capture the draft as a new version (with an optional changelog) — that version is what evaluations and deployments are pinned to.

### 3️⃣ Generate test cases

From the dashboard, generate a batch of test cases for your agent. Connexity reads the agent's system prompt and tool definitions and produces diverse multi-turn scenarios — happy paths, edge cases, and adversarial / red-team cases — each with a persona, an opening message, expected outcomes, and the tool calls the agent is expected to make.

You can also ask AI to create or refine individual test cases from natural-language instructions, including turning real production transcripts into repeatable regression tests.

### 4️⃣ Run an evaluation

Run the test cases against your agent. Connexity simulates the user side, lets your agent execute its own tool loop, and records full transcripts, tool calls, token usage, latency, and cost.

For automation in CI, use the CLI *(in development)* — for example, in a GitHub Action that runs the regression suite on every PR and fails the build on quality regressions.

### 5️⃣ Inspect results and production calls

In the dashboard you can:

- Compare runs across agent versions and prompts
- Drill into per-turn transcripts, tool calls, and judge verdicts
- Track cost and latency trends
- Review synced Retell calls and convert real-world misses into new tests
- Promote a version for deployment workflows *(push back to source platforms coming soon)*

## 🌟 Star Us

If Connexity is useful to you, please star the repo on GitHub — it helps a lot.

<a href="https://github.com/Connexity-AI/connexity-evals">
   <img src="https://img.shields.io/github/stars/Connexity-AI/connexity-evals?style=social" alt="Star Connexity on GitHub">
</a>

## 💬 Support

Finding an answer to your question:

- The [`docs/`](./docs) folder is the best place to start.
- [GitHub Discussions](https://github.com/Connexity-AI/connexity-evals/discussions) — ask questions, share what you're building, and request features.
- [Discord](https://discord.gg/Gj47DqWq) — chat with the team and other users in real time.

Support channels:

- **Ask any question in our [GitHub Discussions](https://github.com/Connexity-AI/connexity-evals/discussions).** Please include as much detail as possible (code snippets, screenshots, logs) so we can help quickly.
- [Request a feature](https://github.com/Connexity-AI/connexity-evals/discussions) on GitHub Discussions.
- [Report a bug](https://github.com/Connexity-AI/connexity-evals/issues) on GitHub Issues.
- For time-sensitive or private queries, email [dmitry@spacestep.ca](mailto:dmitry@spacestep.ca).

## 🤝 Contributing

Your contributions are welcome!

- Vote on ideas in [GitHub Discussions](https://github.com/Connexity-AI/connexity-evals/discussions).
- Raise and comment on [Issues](https://github.com/Connexity-AI/connexity-evals/issues).
- Open a PR — see [CONTRIBUTING.md](./CONTRIBUTING.md) for how to set up a development environment and what we expect in pull requests.

## 🥇 License

This repository is [MIT licensed](./LICENSE).
