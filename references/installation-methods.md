# Installation methods

This reference answers one question per tool and resource type: **what exactly
happens on disk, what command is required, and how to undo it.**

## 1. Acquiring the source

| Source | Command | Notes |
|---|---|---|
| local path | `import_resource.py --source ./dir` | no network, fastest, used by tests |
| GitHub/GitLab/Bitbucket/Codeberg URL | `import_resource.py --source https://...` | shallow clone (`--depth 1`) into `staging/`, `.git` removed before hashing |
| specific branch/tag | add `--ref <name>` | pin when reproducibility matters |
| archive/zip | not implemented | unzip manually, then import the directory |

Guard rails: only `https://` URLs are cloned; host must be in the allowlist; the
clone target is inside the staging directory (no path traversal); no repository
script is executed during import. Before cloning, git `url.*.insteadOf` rules are
audited; a rule that redirects an official host to a mirror blocks the import
(`git-rewrite-detected`) until `--allow-mirror` is given. A `--dry-run` of a URL
source still clones into `staging/` (then cleans up), because classification needs
the files.

## 2. Skills (the only fully portable type)

### Install into a tool

```text
<tool skill root>/<skill-name>/SKILL.md
```

The engine copies the library payload (default) or links it (`--mode link`).
Per-tool user roots:

| Tool | User skill root | Workspace root |
|---|---|---|
| DSH | `~/.dsh/skills` (primary), `~/.agents/skills` | `<ws>/.dsh/skills`, `<ws>/.agents/skills` |
| Codex | `~/.codex/skills`, `~/.agents/skills` | `<ws>/.agents/skills` |
| Claude Code | `~/.claude/skills` | `<ws>/.claude/skills` |
| Gemini CLI | `~/.gemini/skills`, `~/.agents/skills` | `<ws>/.gemini/skills`, `<ws>/.agents/skills` |
| Cursor | `~/.cursor/skills` | `<ws>/.cursor/skills` |
| VS Code Copilot | `~/.copilot/skills` | `<ws>/.github/skills` |

After installing: start a new session/chat (or reload the tool) so the skill is
discovered. Verify with `verify_sync.py` and by asking the tool to list its skills.

### Uninstall a skill

1. Back it up: `backup_restore.py backup --resource <name> --agent <agent>`.
2. Remove the target directory manually (or let the future Plugin do it).
3. Optionally remove the library resource (keep the backup).

The engine deliberately has no "delete from tool" command in phase 1.

## 3. Plugins (per-tool mechanism, never file-copy)

| Tool | Install | Uninstall | Restart |
|---|---|---|---|
| DSH | `dsh plugin --profile <profile> add <npm-package>` | `dsh plugin --profile <profile> remove <package>` (pnpm-backed) | restart the app/profile |
| Claude Code | `claude plugin install <name>@<marketplace>` (add marketplace first) | `claude plugin disable` / `uninstall` | new session |
| OpenAI Codex | Codex app marketplace; config.toml `[marketplaces.*]` / `[plugins."..."]` | remove the plugin entry + cache | restart the app |
| Gemini CLI | `gemini extensions install <github-url\|local-path>` | `gemini extensions uninstall <name>` | restart CLI |
| Cursor | marketplace UI (CLI unverified) | marketplace UI | restart editor |
| VS Code Copilot | Customization Marketplace, or `code --install-extension <vsix>` | Extensions view | reload window |

`sync_resources.py` returns these commands as a `manual` action with the package
name already substituted. It does not run them by default.

Pre-install checks for a plugin: manifest present, declared hooks/commands, what
it adds to the host (tools, commands, MCP servers), and whether it requires a
marketplace that the user trusts.

## 4. MCP servers

MCP is a config merge, not a copy.

```json
// Claude Code ~/.claude.json (user) or <ws>/.mcp.json (project)
{"mcpServers": {"demo-fetch": {"command": "npx", "args": ["-y", "@demo/fetch-mcp"],
  "env": {"DEMO_API_KEY": "${DEMO_API_KEY}"}}}}
```

| Tool | Writable by the engine | File |
|---|---|---|
| Claude Code | yes | `~/.claude.json`, `<ws>/.mcp.json` |
| Gemini CLI | yes | `~/.gemini/settings.json` |
| Cursor | yes | `~/.cursor/mcp.json`, `<ws>/.cursor/mcp.json` |
| VS Code Copilot | yes | `~/.copilot/mcp-config.json`, `<ws>/.mcp.json` |
| OpenAI Codex | no (manual) | `~/.codex/config.toml` `[mcp_servers.*]` |
| DSH | unverified | delivered through plugins |

The target config is backed up, re-read, merged and written atomically. An
existing server with different values is a conflict. After writing, the user
must export the referenced environment variables; tool restart may be required.

## 5. Rules / instructions

| Target | Engine action |
|---|---|
| dedicated folder (`.cursor/rules`, `.github/instructions`) | write a new managed file, never touch siblings |
| missing shared file (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `copilot-instructions.md`) | create it with a provenance header |
| existing shared file | no write; return the managed block for the user to append |

Uninstall: remove the managed file, or the marked block in a shared file.

## 6. Global vs workspace installs

- Default `--scope user`: visible to every project for that tool.
- `--scope workspace --workspace <path>`: writes into the project's own directory
  (`.claude/skills`, `.github/skills`, ...). Prefer this for team-shared resources
  that should be committed to version control.
- Workspace installs still use the central library as the source; do not edit
  the target copy, edit the library and re-distribute.

## 7. Operating-system notes

| Concern | Windows | macOS/Linux |
|---|---|---|
| copy | `shutil.copytree` | same |
| link | directory junction (`mklink /J`), symlink fallback | symlink (verified by code, not tested on this host) |
| permissions | ACL/blocked-file errors surface as "write failed" | permission errors surface the same way |
| paths in manifests | forward slashes internally | same |
| line endings | preserved byte-for-byte by hashing | same |

Never run the tools as administrator/root just to make a write succeed; choose a
writable library or target location instead.

## 8. Verification after install

```bash
python scripts/verify_sync.py --resource <name> --agent <agent> --json
python scripts/compare_resources.py --left resource:<name> --right agent:<agent>:<name>
```

Expected: `ok` with matching hashes. A new session in the target tool is the only
true end-to-end verification that the tool loads the resource; say so explicitly
when you cannot run the tool.
