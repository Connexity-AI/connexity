# Changelog

## [0.2.0](https://github.com/Connexity-AI/connexity/compare/cli-v0.1.0...cli-v0.2.0) (2026-05-06)


### Features

* Add deleted_at field to TestCasePublicSchema for soft-delete tracking ([6ea052c](https://github.com/Connexity-AI/connexity/commit/6ea052c6bdc06bd3971242433e388bb2f573475d))
* Add runStatus prop to ConversationResultRow and EvalRunDetailContent for improved status handling ([8a26b82](https://github.com/Connexity-AI/connexity/commit/8a26b824ceabbf27e71176e75841152a4fb8f6b2))
* **eval:** add run-level metrics & cases pass thresholds (CS-127) ([fa2988f](https://github.com/Connexity-AI/connexity/commit/fa2988f10a76807cde34042cd0e8e3abec48a72e))
* Format source_mode assignment for improved readability ([b67c97e](https://github.com/Connexity-AI/connexity/commit/b67c97ecbaa3003158096ecd2fe858ade5f7834d))
* Refactor environments list and section components to use new Button component and improve UI ([1d52a9f](https://github.com/Connexity-AI/connexity/commit/1d52a9f4f0ddb715187af6024e15d36e1e4e93f9))
* Refactor environments list and section components to use new Button component and improve UI ([dd65a1c](https://github.com/Connexity-AI/connexity/commit/dd65a1ccc8a097484ad5c59a180c2177f2a95d75))
* Refactor test cases components and improve UI consistency ([d848b72](https://github.com/Connexity-AI/connexity/commit/d848b72631ccca51a4f4b8aaa3d28b570a9a62df))
* Update descriptions in RunCreateSchema and RunCreate type for clarity ([9a45083](https://github.com/Connexity-AI/connexity/commit/9a4508344195a1bafc230ac262e802ada63810b0))


### Bug Fixes

* **cli:** add missing PyPI metadata for searchability ([#107](https://github.com/Connexity-AI/connexity/issues/107)) ([d7b1175](https://github.com/Connexity-AI/connexity/commit/d7b1175c292505d7e0cb4a0fb320edd5584628f3))
* Simplify Accordion component usage in ToolAccordion and ToolAccordionBubble ([f9d7456](https://github.com/Connexity-AI/connexity/commit/f9d7456033cc5f3aeeab844f186d6cb2f6f3e463))

## 0.1.0 (2026-05-05)

Initial release of `connexity-cli`. Sets up versioning, packaging, and the
release-please pipeline. Future entries will be generated from CLI commits
under `backend/cli/` going forward.
