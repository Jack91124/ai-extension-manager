# Resource types

A resource is anything a tool loads to extend its agent behaviour. The manager
recognises five top-level types. The distinction matters because **only skills
are portable**; the other types are tool-specific or need format-aware handling.

| Type | One-line definition | Portable? | Library folder |
|---|---|---|---|
| `skill` | Agent Skills folder: `SKILL.md` + optional scripts/references/assets | yes, across all six tools | `library/skills/` |
| `plugin` | A tool's plugin package installed through that tool's plugin mechanism | **no** (per-tool packaging) | `library/plugins/` |
| `mcp` | One MCP server definition (command/URL + env), merged into a tool config | definition is portable, config format is not | `library/mcp/` |
| `rules` | Instructions/rules text (AGENTS.md, CLAUDE.md, GEMINI.md, .mdc, instructions.md) | text is portable, activation differs | `library/rules/` |
| `other` | Software, themes, hooks, unknown archives | no | `library/other/` |

## 1. Skill (primary type)

Follows the Agent Skills open standard (agentskills.io), which all six tools in
phase 1 support in some form.

### Required layout

```text
my-skill/                 <- directory name must equal frontmatter name
  SKILL.md                <- YAML frontmatter + instructions (required)
  scripts/                <- optional executable helpers
  references/             <- optional docs loaded on demand
  assets/                 <- optional templates/fonts/images
```

### SKILL.md frontmatter

Required: `name` (lowercase, digits, hyphens, max 64, must match folder),
`description` (what + when, max 1024 chars).

Optional across tools: `license`, `compatibility`, `allowed-tools`, `metadata`.
VS Code Copilot additionally understands `argument-hint`, `user-invocable`,
`disable-model-invocation` and `context: fork`. These optional fields are preserved
verbatim by the manager; tools that ignore them ignore them.

```markdown
---
name: demo-notes
description: Summarize meeting notes into decisions and action items. Use when the user pastes meeting notes.
license: MIT
---

# Demo Notes
...
```

Validation performed on import (`validate_skill_dir`): SKILL.md present, starts with
frontmatter, name kebab-case and matching the folder, description present and
under the limit, body non-empty. Warnings (not blockers): folder/name mismatch,
angle brackets in description.

### Portability notes

- Directory layout and frontmatter are shared; optional fields are not.
- Paths inside SKILL.md should use forward slashes and be relative to SKILL.md.
- References to tool-specific tools/commands must be conditional; the manager
  does not rewrite skill instructions.
- Never store a skill containing plaintext credentials (scanner refuses it).

## 2. Plugin

A plugin is a package plus an installer contract owned by one tool. Copying a
Claude plugin into Codex's skills folder does nothing and can break the tool.

| Tool | Packaging signal | Installation mechanism |
|---|---|---|
| DSH | `package.json` containing a `dsh` object (`dsh.bundle.patch`, `dsh.client`) | `dsh plugin --profile <name> add <npm-package>` |
| Claude Code | `.claude-plugin/plugin.json` (plus optional `marketplace.json`) | `claude plugin install <plugin>@<marketplace>` |
| OpenAI Codex | marketplace entries + plugin cache; `[plugins."<name>@<marketplace>"]` in config.toml | Codex app marketplace UI / CLI |
| Gemini CLI | `gemini-extension.json` | `gemini extensions install <url-or-path>` |
| Cursor | `.cursor-plugin/plugin.json` | marketplace UI (CLI path unverified) |
| VS Code Copilot | VS Code extension `package.json` contributions or agent plugin package | Customization Marketplace / `code --install-extension` |

Cross-tool packages do exist: a repository can ship `.claude-plugin/` **and**
`.cursor-plugin/` **and** `.plugin/` manifests side by side (verified in the
Vercel plugin cache on the authoring machine). The importer records which tool
manifests are present in `supported_agents` and distribution is allowed only to those
tools.

**Classification rule**: if a directory has both `SKILL.md` and plugin manifests, it
is imported as a skill (skills are the safer, portable subset). The scanner
records the ambiguity in `issues`.

## 3. MCP server

MCP servers are configured, not installed. The library stores one redacted
server definition per resource:

```json
{
  "name": "demo-fetch",
  "config": {
    "command": "npx",
    "args": ["-y", "@demo/fetch-mcp"],
    "env": {"DEMO_API_KEY": "${DEMO_API_KEY}"}
  }
}
```

- On import: the server object is extracted from `mcpServers` (or `mcp_servers` /
  `servers`), secret-looking values are replaced with `${ENV_NAME}` placeholders,
  and the placeholder list is recorded in `record.mcp.placeholders`.
- On distribution: the placeholder is merged into the target JSON config. The
  user must define the environment variable in the tool's environment.
- Never put a literal token into a config, a report, a log or the library.

| Tool | MCP config (verified where noted) |
|---|---|
| Claude Code | `~/.claude.json` -> `mcpServers` (user), `.mcp.json` (project) |
| OpenAI Codex | `~/.codex/config.toml` -> `[mcp_servers.<name>]` (read + manual write) |
| Gemini CLI | `~/.gemini/settings.json` -> `mcpServers` |
| Cursor | `~/.cursor/mcp.json` (user), `.cursor/mcp.json` (project) |
| VS Code Copilot | `~/.copilot/mcp-config.json` (user), `.mcp.json` (workspace) |
| DSH | no standalone MCP config found; MCP arrives through plugins |

## 4. Rules / instructions

Free-form Markdown guidance, with tool-specific activation formats.

| Tool | Format / location |
|---|---|
| DSH | `~/.dsh/AGENTS.md`, `~/.agents/AGENTS.md`, project `AGENTS.md` |
| Codex | `~/.codex/AGENTS.md`, project `AGENTS.md` |
| Claude Code | `~/.claude/CLAUDE.md`, project `CLAUDE.md` |
| Gemini CLI | `~/.gemini/GEMINI.md`, project `GEMINI.md` |
| Cursor | `~/.cursor/rules/*.mdc`, project `.cursor/rules/*.mdc`, `AGENTS.md` |
| VS Code Copilot | `~/.copilot/copilot-instructions.md`, `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md`, `AGENTS.md` |

Conversion policy: the manager does **not** rewrite rule semantics. It places a
faithful copy where the target expects it, preserving the original in the
library. Shared instruction files are append-only manual operations; dedicated
rule folders get a new managed file. Frontmatter differences between formats
(`applyTo` vs `globs` vs plain Markdown) are reported, not silently converted.

## 5. Payload layout and record schema

| Type | Payload | Special record fields |
|---|---|---|
| skill | directory copy | `validation` (name/description checks) |
| plugin | plugin directory | `supported_agents`, `package`, `plugin.evidence` |
| mcp | `payload/server.json` | `mcp.server`, `mcp.config` (redacted), `mcp.placeholders` |
| rules | `payload/content.md` | `content.sha256`, frontmatter summary |
| other | directory/file | note explaining why it is archived only |

Registry record (metadata/registry.json -> resources.<id>):

```json
{
  "id": "skill/demo-notes",
  "type": "skill",
  "name": "demo-notes",
  "slug": "demo-notes",
  "version": "2026.11.21-135410",
  "hash": "<sha256 of sorted rel:sha256 pairs>",
  "manifest": {"SKILL.md": {"sha256": "...", "size": 512}},
  "files": 1,
  "bytes": 512,
  "source": {"url": null, "platform": "local", "kind": "local-path", "path": "..."},
  "created_at": "2026-11-21T13:54:10Z",
  "updated_at": "2026-11-21T13:54:10Z",
  "supported_agents": [],
  "targets": {
    "codex": {"agent": "codex", "scope": "user", "path": "...", "mode": "copy",
              "source_hash": "...", "target_hash": "...", "version": "...",
              "synced_at": "...", "last_action": "install"}
  },
  "sync_mode": "copy",
  "status": "active",
  "dependencies": [],
  "safety": {"risk": "low", "counts": {"high": 0, "medium": 0, "low": 0}},
  "versions": [{"version": "...", "hash": "...", "label": "20261121T135410", "note": "..."}],
  "notes": []
}
```

Hashing: per-file SHA-256 over content; resource hash = SHA-256 of the sorted
`relative-path=sha256` lines. VCS metadata and system junk are excluded. The same
function is used for library payloads, targets, backups and versions, which is
what makes conflict detection deterministic.

## 6. Classification signals (implementation)

| Signal | Result |
|---|---|
| `<dir>/SKILL.md` | skill (validate frontmatter) |
| `.claude-plugin/plugin.json`, `.cursor-plugin/plugin.json`, `gemini-extension.json`, `package.json#dsh`, `contributes.chatSkills` | plugin |
| JSON/TOML containing `mcpServers` / `[mcp_servers]` | mcp |
| `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `copilot-instructions.md`, `*.instructions.md`, `*.mdc` | rules |
| directory of the above | rules |
| anything else | other (never distributed) |

When a directory is only a container (repo root), the scanner descends up to the
configured depth and reports each resource it finds; it does not guess a type
from the repository name.
