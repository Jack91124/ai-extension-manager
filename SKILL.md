---
name: ai-extension-manager
description: >-
  Sync AI agent skills, rules and MCP configs across Claude Code, Codex, Gemini CLI, Cursor, VS Code Copilot
  and DSH from one local library, with hash-based conflict detection, backups and security review. Use when
  the user wants to install a skill or plugin from GitHub, keep skills in sync between AI tools, import what
  a tool already has, compare or repair drifted copies, resolve a two-way sync conflict, or back up / restore
  AI resources. Triggers: "把这个 GitHub 技能装到 Claude Code 和 Codex", "把六个工具新增的 Skill 导入中央库",
  "同步/备份/恢复 AI 扩展". Do not use it for editing application code that merely mentions MCP or skills.
license: MIT
compatibility: Python 3.9+ (standard library only), git for remote repositories, Windows/macOS/Linux. Optional DSH Plugin is NOT included; scripts are the execution layer until that plugin exists.
allowed-tools: Read Write Edit Bash Glob Grep
metadata:
  display_name: AI Extension Manager
  display_name_zh: AI 扩展资源管理助手
  version: 1.0.4
  category: developer-tools
  phase: v1.0 (CLI + Agent Skill; DSH Plugin specified, not built)
---

# AI Extension Manager

One central library, six AI tools, two-way synchronization. This skill is the
**decision layer**: it classifies a resource, checks compatibility and safety,
plans the change, executes it through the bundled Python tools (or the DSH
Plugin once one exists), verifies the result and reports it.

The bundled scripts are the only execution layer that exists today. There is no
graphical DSH Plugin yet. Never claim that a plugin UI, a plugin tool, or a
native API of another AI tool is available unless the environment scan proves it.

## Install and run

The stable entry point is `aem`; the seven Python scripts remain the implementation.

```bash
python -m pip install .        # from a source checkout; installs the `aem` command
aem init                       # create ~/.ai-extension-manager
aem doctor                     # check Python, paths, registry, locks and tools
aem status                     # resource x agent sync state
```

Without installing, every command also works as `python scripts/aem.py <command>`.

| Command | Purpose |
|---|---|
| `aem scan` | detect the six tools and their skill directories |
| `aem detect --path P` | classify P as skill / plugin / MCP / rules |
| `aem import --source P` | import into the central library |
| `aem sync --direction distribute --agent claude --agent codex --resource NAME` | distribute |
| `aem adopt` / `aem distribute` | one-word shortcuts for the two sync directions |
| `aem verify --all` | verify installed copies |
| `aem status` | one table of every resource x agent pair |
| `aem doctor` | diagnose setup problems with fixes |

All commands accept `--home`, `--workspace` and `--json`; see `references/cli-reference.md`.

## Non-negotiable rules

1. **Detect before you touch.** Run `scripts/scan_agents.py` first. Never guess a tool's
   directory, version or capability; the registry marks every path as
   local / official / partial / unverified.
2. **No silent overwrite.** Any existing file or resource that differs from the
   incoming content is a conflict. Conflicts require an explicit resolution
   (keep library / keep target / manual merge / save as new version). The scripts
   exit 2 and store evidence instead of overwriting.
3. **Back up before replacing.** The engine snapshots the target and the library
   version before every write. Backups live under `<home>/backups/`.
4. **Review before installing code.** Run the built-in safety scan, read the
   scripts that will ship, and get explicit user confirmation for high/medium
   risk resources or for anything that installs packages, runs shell commands,
   or ships binaries.
5. **Secrets never enter the library.** Credentials found in skills are refused;
   credentials in MCP configs are replaced with `${ENV_VAR}` placeholders and the
   user must export the variable. Never echo a secret into a report.
6. **Honest capability reporting.** If a tool is absent, a plugin mechanism is
   unverified, or a distribution path is not implemented, say so and stop. A
   partial result reported accurately is better than a fake success.

## Establish context (run first, every session)

```bash
python scripts/scan_agents.py --json
python scripts/scan_agents.py --workspace <project> --json   # adds project-scope dirs
```

Both scan commands are read-only: they never create the central library. The first
mutating command creates it. If the default location is not writable (sandboxed
hosts, read-only home), pass `--home <writable-dir>` and tell the user which root you used.

Use the JSON: tool status (installed / config-only / absent), CLI version, skill
directories and their counts, plugin system, MCP and rules capability, plus
`verification` flags. Record the central library root: it defaults to
`$AEM_HOME` or `~/.ai-extension-manager`. Pass `--home` when the user wants another location.

If the request names a specific tool that is `absent`, say so immediately and offer
one of: install the resource somewhere present, prepare a portable copy, or stop.
Do not create directories inside a tool that is not installed.

## Pick the workflow

| User intent | Workflow | Primary commands |
|---|---|---|
| "install this GitHub skill / plugin" | A. Install from source | `detect_resources.py --url` then `import_resource.py` |
| "what's new in my AI tools?" | B. Scan and import | `sync_resources.py --direction import` |
| "sync this skill to Codex and Claude" | C. Distribute | `sync_resources.py --direction distribute --agent ...` |
| "make all tools match the library" | D. Two-way sync | `sync_resources.py --direction both` |
| "these copies disagree" | E. Conflict review | `compare_resources.py` + manual decision |
| "is the install still correct?" | F. Verify / repair | `verify_sync.py` then re-distribute |
| "roll back / restore" | G. Backups | `backup_restore.py` |
| "install this plugin for me" | H. Plugin planning | plugin action is a plan + command, see below |
| "what do I have?" | I. Inventory report | `detect_resources.py --all-agents` + registry |

Detailed contracts live in `references/`; read only what the task needs:

- `architecture.md` - layers, Skill/Plugin boundary, operation contract
- `resource-types.md` - classification signals, record schema, payload layout
- `agent-compatibility.md` - verified paths and capabilities per tool
- `synchronization-engine.md` - state machine, modes, journal, idempotency
- `conflict-resolution.md` - detection math and resolution procedures
- `security-policy.md` - scanner rules, confirmation gates, secret handling
- `installation-methods.md` - per-tool install/uninstall mechanics
- `dsh-plugin-spec.md` - specification for the future dashboard plugin

## Workflow A - install from a GitHub URL or local path

1. Classify the source **before** downloading when possible:
   `python scripts/detect_resources.py --url <url> --json`
   The result says whether the URL is a repository, which host it is, and the
   exact import command. Recognised types: `skill`, `plugin`, `mcp`, `rules`.
2. Before any remote import, the tool audits git `url.*.insteadOf` rewrites. A rule
   that sends github.com clones to a third-party mirror is refused with
   `git-rewrite-detected` (exit 1): show the rule and ask; only pass `--allow-mirror`
   if the user trusts that mirror. A URL dry run still clones into `staging/`
   (classification needs the files) and cleans up afterwards; local paths have no
   such side effect.
3. For a remote repo, import with conflict policy and a dry run first:
   `python scripts/import_resource.py --source <url> --dry-run --json`
   Then run without `--dry-run`. The clone is shallow and goes to `staging/`.
4. Read the JSON result. `needs-confirmation` means the security scanner found
   shell piping, recursive deletes, binary payloads or other risky patterns:
   summarize the findings, show the file and line, and ask before re-running
   with `--allow-risk`. `secret-detected` means a credential is embedded; do not
   retry with `--allow-secrets` unless the user explicitly wants that risk.
5. A repository may contain several resources; the importer imports each typed
   candidate. Use `--type skill` / `--type plugin` / `--kinds` to narrow.
6. Distribute only after import succeeded (workflow C).

## Workflow B - scan tools and import their resources

```bash
python scripts/sync_resources.py --direction import --agent claude --agent codex --json
python scripts/sync_resources.py --direction import --json          # all six tools
python scripts/sync_resources.py --direction import --workspace .   # project scope
```
Actions: `imported` (new), `imported-update` (state B, target changed only, a new
library version is created), `skip` (identical or library ahead),
`conflict` (state C, exit 2), `needs-confirmation` / `rejected` (unsafe or invalid).

When `conflict` appears, do not force. Run workflow E.

## Workflow C - distribute library resources

```bash
python scripts/sync_resources.py --direction distribute \
  --agent dsh --agent codex --agent claude --resource <id-or-name> --json
python scripts/sync_resources.py --direction distribute --all --json
```
- `--mode copy` is the default and the only universally safe mode.
- `--mode link` creates a junction/symlink to the library payload. Verify with
  `verify_sync.py` afterwards; the link mode has only been verified on Windows
  junctions, not on every platform/tool combination.
- Skills are portable. Plugins are **not**: the engine refuses cross-tool plugin
  copies and returns a `manual` action with the exact per-tool install command.
  Present that command, explain where it installs, and let the user run it or
  approve running it. Never copy plugin files into another tool's skills folder.
- Before planning a plugin install, inventory what is already installed:
  `python scripts/detect_resources.py --agent <id> --kinds plugins --json`
  lists installed plugins with versions and cache paths (Claude
  `installed_plugins.json`, Codex `config.toml` + cache, DSH profile bundles, Gemini
  extensions, VS Code extensions contributing `chatSkills`). Report version drift
  between tools and never hand-copy a plugin cache directory.
- MCP resources are merged into the target JSON config with secret redaction.
  Codex stores MCP in TOML; automated writes are intentionally not implemented,
  so the result is manual with a config snippet.
- Rules: dedicated rule folders get a new managed file; shared instruction
  files (AGENTS.md / CLAUDE.md / GEMINI.md) are never modified when they already
  exist - the result is `manual` with a managed block to append.

## Workflow D - two-way sync

```bash
python scripts/sync_resources.py --direction both --agent codex --json
```
Import first, then distribute. Both directions are idempotent: identical content
is skipped without writes or backups. Use `--resume` after an interrupted run; the
journal under `staging/journal-*.json` records completed steps.

## Workflow E - conflict review and resolution

1. Explain the state (A/B/C/D/E) using `references/conflict-resolution.md`.
2. Show the difference:
   `python scripts/compare_resources.py --left resource:<name> --right agent:<agent>:<name> --diff`
   For two stored versions use `resource:<name>@<version-label>`.
3. Offer exactly these resolutions:
   - **keep library** - distribute to the target with `--on-conflict library` (backup first).
   - **keep target** - capture the target as a new library version:
     `import_resource.py --source <target-path> --on-conflict keep-source` or
     `sync_resources.py --direction import --on-conflict new-version`.
     On the distribute side `--on-conflict target` means "leave it alone" (`kept-target`).
   - **manual merge** - show both files, let the user edit the library payload,
     then distribute and verify. This skill does not auto-merge text.
   - **save as new version** - import with `--on-conflict new-version`.
4. After resolving, run `verify_sync.py` and report both versions and hashes.
5. Never pick a resolution silently. State C means both sides changed on purpose;
   the user owns that decision.

## Workflow F - verify and repair

```bash
python scripts/verify_sync.py --all --json
python scripts/verify_sync.py --resource <name> --include-unmanaged --json
```
Statuses: `ok`, `drifted` (file list included), `missing`, `corrupted` (bad link),
`umanaged` (present in a tool, absent from the library), `unavailable`.
Repair = re-distribute when the library is authoritative, or import when the
target is authoritative. Both are conflict-guarded, so decide the direction with
the user first.

## Workflow G - backup and restore

```bash
python scripts/backup_restore.py backup --resource <name>
python scripts/backup_restore.py list
python scripts/backup_restore.py restore --backup-id <id> --to library
python scripts/backup_restore.py restore --resource <name> --version <label>
python scripts/backup_restore.py prune --keep 10
```
Global flags (`--home`, `--json`) go **before** the subcommand. Every restore snapshots
the current state first, so restores are undoable.

## Workflow H - plugin distribution (planning only)

Plugins are tool-specific packages. The engine:
1. detects the packaging (e.g. `.claude-plugin/plugin.json`, `package.json#dsh`,
   `gemini-extension.json`, `.cursor-plugin/plugin.json`),
2. refuses cross-tool copies,
3. returns the target tool's real install mechanism and command, e.g.
   `dsh plugin --profile desktop add <npm-package>` or
   `claude plugin install <plugin>@<marketplace>`.

The skill does not execute package installs by default. Show the command, the
marketplace/source, and the restart requirement; ask before running it. A DSH
Plugin for this system is specified in `references/dsh-plugin-spec.md` but is
**not implemented** - do not call or advertise it.

## Safety review checklist (before any install)

- Source: official repo? star/age/owner? does the README match the code?
- Files: what scripts/binaries/hooks ship? any `postinstall` / `setup.py` / `.pth`?
- Commands: piping downloads into a shell, recursive deletes, privilege
  escalation, persistence, credential access, network exfiltration.
- Data: does it read `.ssh`, browser profiles, token stores, env dumps?
- Permissions: does the target tool need a restart? does it read project or user
  scope? does the user want a global or workspace install?
- Reversibility: a backup exists? is uninstall documented?

Report risk as high/medium/low with concrete evidence, then ask.

## Result report (always end with this shape)

```markdown
## Operation report
- Request: <what the user asked>
- Environment: <tool status + versions + library root>
- Classification: <type, source, version/hash, supported tools>
- Security: <risk, findings, secret handling, confirmation given>
- Actions: <imported / installed / skipped / manual / conflict, per tool>
- Verification: <verify status per target, hashes compared>
- Conflicts/backups: <paths>
- Not done / unverified: <honest list>
- Next step: <one concrete action>
```

## Failure playbook

| Symptom | Meaning | Action |
|---|---|---|
| exit 2 on sync/import | conflict (including dry runs), nothing overwritten | workflow E |
| `git-rewrite-detected` | git insteadOf redirects official hosts to a mirror | show the rule; `--allow-mirror` only if trusted |
| PermissionError / access denied on the library root | default `~/.ai-extension-manager` is not writable here | re-run with `--home <writable-dir>`, tell the user the root used |
| `kept-target` | explicit keep-target resolution | run the import direction when the user wants it in the library |
| `unavailable` for a tool | tool absent or no verified dir | stop, offer alternatives |
| `error write failed` | blocked path/permission | report path, do not retry blindly; ask for a writable location |
| `needs-confirmation` | scanner found risk | show findings, ask, then `--allow-risk` |
| `secret-detected` | credential in payload | scrub or refuse; never store it |
| `invalid` skill | SKILL.md fails the open standard | fix name/description or use `--force` only if the user accepts a non-standard skill |
| hash mismatch after write | storage problem | report, restore from backup, do not claim success |

## Environment facts this skill was built against

Verified on the authoring machine: DSH 0.2.0-rc.2, Claude Code 2.1.318,
Codex config-only (no CLI on PATH), VS Code 1.115.0, Gemini CLI and Cursor not
installed. Re-verify with `scan_agents.py` on every new machine; paths and
capabilities are data, not assumptions.

## 中文速查（给中文用户）

完整中文说明见 [README.zh-CN.md](README.zh-CN.md) 与 [references/cli-reference.md](references/cli-reference.md)。

```bash
python -m pip install .              # 安装 aem 命令
python scripts/aem.py <命令>          # 或不安装直接运行
aem init && aem doctor && aem scan    # 建库、体检、探测六个工具
```

| 用户说 | 执行 |
|---|---|
| 把这个 GitHub 上的 Skill 装到 DSH/Codex/Claude | 先 `aem detect --url <url>` 识别类型与风险，再 `aem import --source <url>`，然后 `aem sync --direction distribute --agent ... --resource ...`，最后 `aem verify --all` |
| 把六个工具新增的 Skill 导入中央库 | `aem adopt`（等价于 `aem sync --direction import --all-agents`），冲突时报告并停下，不覆盖 |
| 检查哪些副本漂移/损坏 | `aem verify --all` 或 `aem status --strict` |
| 回滚某个资源 | `aem backups` 找到快照，再 `aem restore --resource <名> --version <标签>` |
| 两边都改过怎么办 | 不自动合并；给出 `aem compare --diff` 证据，让用户选保留中央库、保留目标、手动合并或另存新版本 |

默认不覆盖、先备份、危险操作要确认。DSH Plugin 面板尚未实现，不要声称存在。
