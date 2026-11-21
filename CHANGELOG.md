# Changelog

All notable changes are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions use [SemVer](https://semver.org/).

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
