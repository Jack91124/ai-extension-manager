# CLI reference

`aem` is a thin dispatcher over seven task modules; every command also runs as
`python scripts/aem.py <command>` without installing the package.

## Conventions

| Item | Meaning |
|---|---|
| Library | `AEM_HOME` or `~/.ai-extension-manager` |
| Agent ids | `dsh`, `codex`, `claude`, `gemini`, `cursor`, `copilot` |
| Scope | `user` (default, per-machine) or `workspace` (per project) |
| Modes | `copy` (default, safe) or `link` (directory junction/symlink) |
| Exit codes | `0` success · `1` error or failed check · `2` conflict or difference |
| Machine output | every command accepts `--json` |

Global options: `--home PATH`, `--workspace PATH`, `--json`. They may appear before or after a
subcommand (`aem backups --json` works).

## Library and diagnostics

### `aem init`

Creates the library layout: `library/{skills,plugins,mcp,rules,other}`, `metadata/` (registry,
agents, sync history), `backups/`, `staging/`, `conflicts/`, `logs/`. Idempotent.

```bash
aem init [--json]
```

### `aem doctor`

Ten checks, each `ok` / `warn` / `fail`, with a `fix` hint when actionable: Python version, library
writability, registry readability, schema version, payload directories, lock age, detected tools,
disk space, snapshot size, unresolved conflicts.

```bash
aem doctor [--fix] [--json]
```

`--fix` creates a missing library and removes a lock older than one hour. Exit `1` only when a check
is `fail`.

### `aem status`

One row per recorded resource × agent target, with the verification result:

```bash
aem status [--agent ID] [--scope user|workspace] [--strict] [--json]
```

Statuses: `in-sync`, `changed` (target drifted), `missing`, `corrupted`, `unavailable`,
`manual` (plugin installed outside `aem`), `unknown-agent`. `--strict` exits `1` if any row is not
`in-sync`/`unavailable`/`manual`.

### `aem version`

Prints `aem <version> (python <version>)`.

## Discovery

### `aem scan` (alias `agents`)

Detects the six tools: CLI path and version, home directory, skill directories (user and workspace),
skill counts, plugin system, MCP/rules support, verification level and docs link. Read-only: it never
creates the library.

```bash
aem scan [--agent ID] [--require ID] [--workspace PATH] [--json]
```

`--require` exits `1` unless that tool is installed (useful in scripts).

### `aem detect` / `inspect`

Classifies a path, a URL or an installed tool's resources.

```bash
aem detect --path ./my-skill [--safety] [--check-hash] [--depth N]
aem detect --url https://github.com/owner/repo
aem detect --agent claude --kinds skills,plugins
aem detect --all-agents --json
```

A GitHub/GitLab/Bitbucket/Codeberg URL is classified as a repository and returns the exact import
command to run next; it does not download anything by itself.

## Import

```bash
aem import --source ./local/skill
aem import --source https://github.com/owner/repo --ref main --kinds skills
aem import --source ./rules.json --type rules
aem import --source ./mcp.json --type mcp --server github

# a repository that bundles several skills: choose one, or take them all
aem import --source https://github.com/owner/repo --pick skills/pdf
aem import --source https://github.com/owner/repo --all
```

| Option | Effect |
|---|---|
| `--type auto|skill|plugin|mcp|rules` | force a resource type |
| `--kinds skills,plugins,mcp,rules` | what to take from a repository |
| `--server NAME` | import one MCP server from a config |
| `--pick PATH` | import exactly this resource (path relative to the source) |
| `--all` | import every resource found in the source (default refuses when ambiguous) |
| `--ref` / `--depth` | Git branch/tag and clone depth |
| `--on-conflict skip|keep-library|keep-source|new-version` | behaviour when the resource exists |
| `--force` | import despite SKILL.md validation failure |
| `--allow-risk` | import despite high-risk findings |
| `--allow-secrets` | import despite secrets (dangerous) |
| `--allow-mirror` | allow git `insteadOf` rewrites to a third-party mirror |
| `--dry-run` | classify and scan only; write nothing |

## Sync

```bash
# pull changes from tools into the library
aem sync --direction import --agent claude --agent codex
# push the library to tools
aem sync --direction distribute --agent claude --resource my-skill
# safe mix: import target-side changes, then distribute library changes
aem sync --direction both
# preview
aem sync --direction distribute --all --dry-run
```

| Option | Effect |
|---|---|
| `--direction import|distribute|both` | direction (default `both`) |
| `--agent ID` (repeatable) / `--all-agents` | targets |
| `--resource NAME` (repeatable) / `--all` | resources |
| `--scope user|workspace` | where the target lives |
| `--mode copy|link` | copy (default) or junction/symlink |
| `--on-conflict` | `skip` (default) · `library`/`overwrite` · `target`/`keep-source`/`new-version` |
| `--dry-run` | plan only, no journal |
| `--force` | overwrite state B/C targets (dangerous) |
| `--resume` | continue an interrupted run from its journal |
| `--keep-journal` | keep the journal after success |

Plugins are not copied: the result carries the vendor command to run (and any version drift). MCP
entries are merged into the tool's JSON config; credential values are placeholders.

## Compare and verify

```bash
aem compare --left resource:my-skill --right agent:claude:my-skill --diff
aem compare --left resource:my-skill@2026.11.20-101500 --right resource:my-skill
aem compare --left ./copy-a --right ./copy-b
aem verify --all [--strict]
aem verify --resource my-skill --agent codex
aem verify --all --include-unmanaged
```

Operands: `resource:<name|id>[@version]`, `agent:<agent>:<resource>`, or a path. `compare` exits `2`
when the operands differ. `verify` statuses: `ok`, `drifted`, `missing`, `corrupted`, `manual`,
`unavailable`; `--include-unmanaged` also lists skills a tool has but the library does not.

## Backups and restore

```bash
aem backup --resource my-skill            # snapshot the library payload
aem backups                               # list snapshots
aem restore --resource my-skill --version <label>
aem restore --backup-id <id> --to library
aem restore --backup-id <id> --to agent --agent claude
aem prune --keep 10
```

`restore` takes a fresh snapshot before changing anything, so a restore is itself reversible.

## JSON contracts

Every task command returns one JSON object with at least:

```json
{
  "ok": true,
  "generated_at": "2026-11-21T16:16:33Z",
  "home": "C:\\Users\\you\\.ai-extension-manager",
  "results": [],
  "summary": {}
}
```

`scan` returns `agents[]`; `detect` returns `items[]`; `verify` returns `checks[]`; `status` returns
`rows[]` and `summary`; `import`/`sync` return `results[]`, `conflicts` and `errors`. A conflict
result carries `state` (`A`–`E`, `untracked`) and a `reason`.

## Environment variables

| Variable | Purpose |
|---|---|
| `AEM_HOME` | central library root |
| `AEM_AGENT_HOME_<ID>` | override a tool home (e.g. `AEM_AGENT_HOME_CLAUDE`) — used by tests and the demo |
| `DSH_HOME`, `CODEX_HOME`, `CLAUDE_CONFIG_DIR`, `GEMINI_HOME`, `CURSOR_HOME`, `COPILOT_HOME` | vendor-native home overrides, honoured by adapters |
| `PYTHONUTF8=1` | recommended on Windows for non-ASCII resource names |

## Exit code recipes

```bash
aem verify --all --strict || echo "drift detected"
aem sync --direction both --dry-run; case $? in 0) echo clean;; 2) echo conflict;; *) echo error;; esac
```
