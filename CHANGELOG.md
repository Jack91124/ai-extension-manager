# Changelog

All notable changes are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions use [SemVer](https://semver.org/).

## [Unreleased]

## [1.0.19] - 2026-11-26

### Added

- URL imports now fail with an actionable hint when `git clone` cannot reach the host:
  check `git config --global --get-regexp '^url\.'` for mirror rewrites, or download the
  repository and import the local path (`aem import --source <folder>`). Added scenario
  test 34 as a regression (34/34 passing).
- Bilingual README troubleshooting section for clone failures and git URL rewrites.

### Changed

- Quick-start pins, test badge and user-facing docs advanced to `v1.0.19` / 34 scenario tests.

## [1.0.18] - 2026-11-26

### Added

- `aem doctor` now warns when a git `url.<base>.insteadOf` rule redirects an official host
  (e.g. `github.com`) to a third-party mirror — the same supply-chain risk that
  `import_resource.py` already refuses at import time. New `git-mirror` check with an
  actionable fix hint. Added scenario test 33 as a regression (33/33 passing).

### Changed

- Quick-start pins, test badge and user-facing docs advanced to `v1.0.18` / 33 scenario tests.

## [1.0.17] - 2026-11-26

### Added

- Stable, versioned JSON result contract `aem.result/v1`: every `--json` command now
  emits `schema` and `tool_version` envelope fields via the common `emit_json()` funnel.
  Documented in `references/json-contract.md`. Added scenario test 32 as a regression.

### Changed

- Quick-start pins, test badge and user-facing docs advanced to `v1.0.17` / 32 scenario tests.

## [1.0.16] - 2026-11-26

### Added

- `aem doctor` now detects library payloads edited directly on disk, bypassing the registry:
  the `payloads` check reports a `warn` with the affected resource names and points to the
  refresh path. Added scenario test 31 as a regression (31/31 passing).

### Changed

- Quick-start pins, test badge and user-facing docs advanced to `v1.0.16` / 31 scenario tests.

## [1.0.15] - 2026-11-26

### Fixed

- `aem doctor` no longer reports a regular file placed at the central library root as
  "writable"; it now fails the library check with an actionable `not a directory` message.
  Added scenario test 30 as a regression (30/30 passing).
- Quick-start pins and test badge advanced to `v1.0.15`.

## [1.0.14] - 2026-11-26

### Fixed

- `aem init` now catches OSError when the central library root is not writable (locked-down home,
  sandboxed host) and returns an actionable JSON/human error suggesting `--home` / `AEM_HOME`,
  instead of dumping a raw Python traceback. Added scenario test 29 as a regression.
- Refreshed the awesome-list candidates in the launch kit: removed a dead list and an unmaintained
  one, added five verified-active, contribution-friendly lists (checked 2026-11-26).
- Quick-start install pins advanced to `v1.0.14`; scenario test badge updated to 29 passing.

## [1.0.13] - 2026-11-26

### Fixed

- SKILL.md now states explicitly that every `scripts/...` example is relative to the skill's own
  directory, not the user's project, and tells the agent how to resolve it (framework context, or
  locate `SKILL.md` then use an absolute path). This closes a real gap for the "install once, drive
  with one sentence" workflow when the skill lives in an agent skills folder, not a checkout.
- Quick-start install pins advanced to `v1.0.13` in both READMEs and the launch kit.

## [1.0.12] - 2026-11-25

### Fixed

- Quick-start install commands in both READMEs and the launch kit still pinned `v1.0.4`, so a
  visitor following the README installed a version seven releases behind and missed `aem dirs`, the
  multi-resource import guard and the macOS CI fixes. They now pin `v1.0.12`.
- Scenario-test badge corrected from 27 to 28 in both READMEs.

## [1.0.11] - 2026-11-25

### Added

- `docs/alternatives.md`: an honest comparison of installer CLIs, desktop managers and aem, with a
  decision guide for when aem is the wrong choice.

### Fixed

- README status sections now state 28 scenario tests instead of 26.

## [1.0.10] - 2026-11-22

### Added

- `aem dirs` (alias `aem paths`) prints the resolved personal and project skill folders, MCP
  config files and rules files for all six tools, with scope and existence, straight from the same
  agent registry `aem scan` and the public paths page use.

## [1.0.9] - 2026-11-22

### Fixed

- The multi-resource import test compares candidate paths as a set, so CI is stable on
  case-insensitive macOS filesystems where directory listing order differs.

## [1.0.8] - 2026-11-22

### Added

- `aem import --pick PATH` imports exactly one resource from a source that bundles several
  skills, and `aem import --all` imports every match.

### Fixed

- `aem import` no longer sweeps up every skill in a repository by accident: when a folder or
  GitHub repository contains more than one resource it now lists the candidates and exits with
  code 2 until you choose `--pick` or `--all`.

## [1.0.7] - 2026-11-22

### Added

- `docs/where.html` — a generated page listing the exact personal/project skills directories, MCP config
  files, rules files and plugin mechanism for all six tools, with a verification level per row.
- `docs/make_where.py` — renders that page and `docs/llms.txt` straight from the agent registry in
  `scripts/aem_core.py`, so the public table cannot drift from what `aem scan` reads.
- `docs/llms.txt` — machine-readable summary (install, path table, key pages) for AI crawlers.

### Changed

- README (English and Chinese) gained a "where each tool keeps its skills" table and links to the new page.
- Landing pages link to the new page from the nav, the support table and the footer; sitemap includes it.

## [1.0.6] - 2026-11-22

### Changed

- Rewrote the skill description around what people actually search for (one library, two-way sync, install
  a skill from GitHub, copy skills between tools, drifted copies, conflicts) instead of listing features.

### Documentation

- `docs/launch/posts.md`: copy-paste launch copy — X thread, Reddit post, Show HN, Chinese community post,
  awesome-list PR template, image assets and posting order. Nothing in it is posted automatically.

## [1.0.5] - 2026-11-22

### Added

- `aem report`: renders the whole library into one self-contained HTML file — resources by type,
  every tracked target with its live state (in-sync / drifted / missing), detected tools, and the
  recent activity log. No network calls; `--json` returns the same data for scripting.
  Screenshot: `docs/report.png`. Scenario test 26 covers it (26 tests total).

### Documentation

- GitHub Pages landing site: <https://jack91124.github.io/ai-extension-manager/> (English) and
  `/zh.html` (中文) with a comparison table, `sitemap.xml` and `robots.txt`; linked from both READMEs.
- `docs/launch.md`: zero-audience cold-start plan (day 1–14), awesome-list PR targets, and the
  repo social-preview step.

### Fixed

- Quick-start install lines in both READMEs pinned `v1.0.3` while the latest release was `v1.0.4`;
  they now pin `v1.0.4`.

## [1.0.4] - 2026-11-22

### Added

- `aem adopt` and `aem distribute`: one-word shortcuts for the two sync directions
  (`aem adopt --agent claude` = `aem sync --direction import --agent claude`).
- Scenario test 25 covers both shortcuts end to end (25 tests total).
- CI and latest-release badges in both READMEs; CI is green on main.

### Documentation

- Animated 10-second demo (`docs/demo.gif`, 109 KB) rendered from the real `demo/run_demo.py`
  transcript via `docs/make_demo_gif.py`; both READMEs now show it instead of the static hero image.
- 1200x630 social card (`docs/og.png`, rendered by `docs/make_og.py`).
- Long-form article `docs/why-sync-overwrites.md` (English + 中文摘要) linked from both READMEs.

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
