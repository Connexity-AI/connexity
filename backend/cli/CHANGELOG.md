# Changelog

## [1.0.0](https://github.com/Connexity-AI/connexity/compare/cli-v0.2.0...cli-v1.0.0) (2026-10-06)


### ⚠ BREAKING CHANGES

* POST /environments/{id}/deploy and the deployment endpoints are removed, along with eval_gate_eval_config_id and current_version_* on environments.
* runtime kind "connexity", RunConfig.agent_simulator and RunConfig.tool_mode are removed. Stored configs using them no longer validate.
* the /prompt-editor API, POST /test-cases/ai, agent guidelines endpoints and the matching CLI commands are removed.

### refactor

* remove product-driven deploys ([826c704](https://github.com/Connexity-AI/connexity/commit/826c704191f9b2167a4efc7de42a97be34729b87))
* remove the in-house agent simulator and Connexity runtime ([10d4579](https://github.com/Connexity-AI/connexity/commit/10d457988848e1ae10eb8ab9ad13373b6e051691))


### Features

* add OpenAPI specification and enhance agent version management ([920753f](https://github.com/Connexity-AI/connexity/commit/920753f9ad6d5287b434d5bb24ca44e909fdfeb9))
* **cli:** add evaluation-engine commands ([cf073c6](https://github.com/Connexity-AI/connexity/commit/cf073c6f14540e4f9105e4e8ecdcb9c2923d3e21))
* **eval:** pluggable evaluation engine framework (Connexity / Retell / Custom URL) ([1802af7](https://github.com/Connexity-AI/connexity/commit/1802af78c7dfc2cab0b0d7e9676662d213c1f54a))
* remove the in-product AI assistant and prompt editor ([c9b48dd](https://github.com/Connexity-AI/connexity/commit/c9b48dd86b8ddfe5ff73848593346604a8e9f921))

## [0.2.0](https://github.com/Connexity-AI/connexity/compare/cli-v0.1.1...cli-v0.2.0) (2026-05-06)


### Features

* **cli:** surface CS-127 thresholds, add deployment lifecycle, fix README accuracy ([#111](https://github.com/Connexity-AI/connexity/issues/111)) ([009fc25](https://github.com/Connexity-AI/connexity/commit/009fc25268718bf597f3bbbc2795b57bf0d3eab2))


### Bug Fixes

* **release:** move version source to backend/cli/_version.py ([#115](https://github.com/Connexity-AI/connexity/issues/115)) ([a351ecd](https://github.com/Connexity-AI/connexity/commit/a351ecd4c56b789af564f3118ba7e4b80c94f361))

## 0.1.1 (2026-05-06)

### Bug Fixes

- Add missing PyPI metadata for searchability (keywords, `Environment :: Console`, `Operating System :: OS Independent` classifiers).

## 0.1.0 (2026-05-05)

Initial release of `connexity-cli`. Sets up versioning, packaging, and the
release-please pipeline. Future entries will be generated from CLI commits
under `backend/cli/` going forward.
