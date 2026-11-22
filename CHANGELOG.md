# Changelog

All notable changes are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions use [SemVer](https://semver.org/).

## [Unreleased]

### Added

- Animated 10-second demo (`docs/demo.gif`, 109 KB) rendered from the real `demo/run_demo.py`
  transcript via `docs/make_demo_gif.py`; both READMEs now show it instead of the static hero image.

## [1.0.3] - 2026-11-22

### Added

- One-line install without cloning: `python -m pip install --user "git+https://github.com/Jack91124/ai-extension-manager.git@v1.0.3"`
  (or `pipx install`), plus a prebuilt wheel attached to the v1.0.3 release.
- End-to-end verification of `npx skills add Jack91124/ai-extension-manager`: the CLI installs the whole
  skill into `.agents/skills/ai-extension-manager` and symlinks it for every detected agent.

### Changed

- The repository homepage now points at the [skills.sh listing](https://www.skills.sh/jack91124/ai-extension-manager),
  so discovery and install share one entry point.
- README quick start leads with the no-clone install path; cloning stays documented for contributors.

## [1.0.2] - 2026-11-22

### Added

- `npx skills add Jack91124/ai-extension-manager` install path: the repository root is a valid
  Agent Skill and is now listed on skills.sh; README documents the CLI install next to `pip install`.
- Launch kit (`docs/launch.md`) with English/Chinese positioning, social copy and a channel checklist,
  plus a real-transcript hero image (`docs/hero.png`, reproducible via `docs/make_hero.py`).
- Two regression scenarios (`evals/run_tests.py`, 24 total): out-of-band library edits followed by
  a two-sided change, and `compare` with missing/unknown operands.

### Fixed

- Synchronisation could treat a state-C situation as state-B when the library payload had been
  edited outside the import pipeline (stale record hash), risking an overwrite in
  `--direction both`. Target state checks, post-write verification and target records now use the
  current payload tree hash; the record is refreshed when that hash changes.
- `compare_resources.py` raised `TypeError: string indices must be integers` when one side was
  missing; missing operands (including `library:` / `<agent>:` typos) now exit `1` with a clear
  `operand not found on disk` error instead of crashing or reporting a fake difference.
- `demo/run_demo.py` used a doubled `library/library` path; the sandbox home is now `home/`.
- One-step syncs printed `(1 steps)`; pluralisation is correct.

## [1.0.1] - 2026-11-22

### Fixed

- Python 3.9 compatibility: `aem.py` used PEP 604 unions at import time without deferred annotations.
- CI: pin the Ubuntu runner to 22.04 so Python 3.9 remains available; the 3.9 Windows/macOS jobs now pass too.

## [1.0.0] - 2026-11-21

First public release: a working CLI + Agent Skill. The DSH Plugin dashboard is specified, not built.

### Added

- `aem` command line: `init`, `doctor`, `status`, `scan`, `detect`, `import`/`add`, `sync`,
  `compare`/`diff`, `verify`, `backup`/`backups`/`restore`/`prune`, `version`.
- Central library layout (`~/.ai-extension-manager` by default, `AEM_HOME` override) with
  `library/`, `metadata/`, `backups/`, `staging/`, `conflicts/` and `logs/`.
- Six adapters (Claude Code, OpenAI Codex, DSH, Gemini CLI, Cursor, VS Code Copilot) with honest
  verification levels and per-tool skill/rule/MCP/plugin capability declarations.
- Two-way sync with content-addressed conflict detection: states A, B, C, D, E and untracked.
  Default conflict behaviour is to write nothing and exit `2`.
- Copy and link modes, backup before overwrite, dry runs, resumable journals, and batch sync.
- Import from local paths and HTTPS Git repositories, with cleaning of `.git` metadata.
- Security scanner for dangerous shell patterns and secrets, MCP credential placeholders,
  refusal of git mirror rewrites.
- `doctor` diagnostics with `--fix` for the library and stale locks.
- Mitigation of library-level races via an exclusive lock file.
- Self-contained demo (`demo/run_demo.py`) and 22 scenario tests (`evals/run_tests.py`).
- Agent Skill entry point (`SKILL.md`) with references for architecture, resources, adapters,
  sync, conflicts, security, installation methods and the planned DSH Plugin.
- Complete Simplified Chinese README (`README.zh-CN.md`), a language switch on both READMEs,
  and a Chinese quick-reference section in `SKILL.md`.

### Known limitations

- DSH Plugin GUI/execution layer is not implemented (`references/dsh-plugin-spec.md`).
- Plugin installation returns the native command instead of executing it.
- Codex MCP writes are manual (TOML is not rewritten automatically).
- Gemini CLI and Cursor adapters are documented but not runtime-tested.
- No schema migration yet: `SCHEMA_VERSION` mismatch is reported by `doctor`.
