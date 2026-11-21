# Agent compatibility matrix

Every path and capability below is data, not an assumption. Each entry carries a
verification level:

| Level | Meaning |
|---|---|
| `local` | confirmed by inspecting this machine (directory exists, CLI runs, config parsed) |
| `official` | confirmed in vendor documentation (URL recorded) |
| `partial` | mechanism documented but the exact path/behaviour was not exercised |
| `none` | not installed and not verified; the engine refuses to guess |

Re-run `python scripts/scan_agents.py --json` to refresh. Override paths by editing
`<AEM_HOME>/metadata/agents.json`; no code change is needed.

## Summary (authoring machine, 2026-11-21)

| Tool | Detected | CLI | Skill scope | Plugin system | MCP write | Rules |
|---|---|---|---|---|---|---|
| DSH | installed | dsh 0.2.0-rc.2 | user + workspace | dsh-bundle (npm) | unverified | AGENTS.md |
| Codex | config-only | not on PATH | user + workspace | codex-marketplace | read + manual (TOML) | AGENTS.md |
| Claude Code | installed | 2.1.318 | user + workspace | claude-marketplace | yes (JSON) | CLAUDE.md |
| Gemini CLI | absent | - | user + workspace | gemini-extension | yes (JSON, partial) | GEMINI.md |
| Cursor | absent | - | user + workspace | unverified | yes (JSON, partial) | .mdc + AGENTS.md |
| VS Code Copilot | installed | code 1.115.0 | user + workspace | vscode-agent-plugin | yes (JSON) | instructions + AGENTS.md |

`config-only` means the product's configuration directory exists but its CLI is not on
PATH (for example the Codex desktop app). File operations still work; commands
that would need the CLI are reported as manual.

## DSH (DeepSeek Harness) - local

- Skills: `~/.dsh/skills` and `~/.agents/skills` (both are loaded; confirmed by the
  installed `@michengai/dsh-skills-manager` plugin and the machine's shared-skill setup).
  Project scope: `<ws>/.dsh/skills`, `<ws>/.agents/skills`.
- Plugins: npm packages mounted into a profile. A plugin's `package.json` carries a
  `dsh` object, typically `dsh.bundle.patch` pointing at a `cordis.patch.yml` and/or
  `dsh.client` for a web UI. Install with
  `dsh plugin --profile <profile> add <npm-package>`; the profile lives at
  `~/.dsh/profiles/<profile>/package.json` (`dsh.profile.bundles`).
- MCP: no standalone MCP config file was found. Treat MCP as unverified; it
  normally arrives through an installed plugin.
- Rules: `~/.dsh/AGENTS.md`, `~/.agents/AGENTS.md`, project `AGENTS.md`.
- Restart: reload the profile/app after installing a plugin. Adding a skill is
  discovered at session start.
- Link mode: not verified for DSH; copy is the safe default.

## OpenAI Codex - local (config-only)

- Skills: `~/.codex/skills` is populated on this machine; vendor documentation
  also lists `~/.agents/skills` as the native Codex skill location (confirmed in
  VS Code's Agent Skills page). Both are scanned; `~/.codex/skills` is the primary
  install target.
- Plugins: `~/.codex/config.toml` holds `[marketplaces.<id>]` and
  `[plugins."<name>@<marketplace>"]`; code is cached under
  `~/.codex/plugins/cache/<marketplace>/<plugin>/<version>`. Installation goes
  through the Codex app marketplace / CLI, not the file system.
- MCP: `[mcp_servers.<name>]` sections in config.toml. The manager reads them but
  does not rewrite TOML; distribution returns a manual snippet.
- Rules: `~/.codex/AGENTS.md` and project `AGENTS.md`.
- Note: the Codex CLI was not on PATH here; command-based steps must be presented
  as manual actions.

## Claude Code - local

- Skills: `~/.claude/skills`, project `.claude/skills`.
- Plugins: `~/.claude/plugins/` contains `installed_plugins.json`,
  `known_marketplaces.json`, `marketplaces/<marketplace>` (git clone) and
  `cache/<marketplace>/<plugin>/<version>`. Plugin manifest:
  `.claude-plugin/plugin.json`. CLI: `claude plugin install <plugin>@<marketplace>`,
  `claude plugin marketplace add <repo>`; a plugin directory can also be loaded
  per session with `--plugin-dir`.
- MCP: `~/.claude.json` (`mcpServers`, user scope) and `.mcp.json` (project). CLI:
  `claude mcp add / add-json / get`, `--mcp-config`.
- Rules: `~/.claude/CLAUDE.md` and project `CLAUDE.md`.
- Restart: new session needed after plugin changes; skills are discovered per session.

## Gemini CLI - absent on this machine, official docs

Official docs (geminicli.com/docs/cli/skills, /docs/extensions/reference):

- Skills: user `~/.gemini/skills` or the `~/.agents/skills` alias; workspace
  `.gemini/skills` or `.agents/skills`. The `.agents` alias takes precedence over the
  `.gemini` directory in the same tier.
- Extensions: `gemini extensions install <github-url|local-path>`, manifest
  `gemini-extension.json`, installed copy under `~/.gemini/extensions/<name>`
  (path inferred from docs; the manager creates it only when the tool exists).
  Extensions can bundle commands, hooks, sub-agents, skills, themes and MCP servers.
- MCP: `~/.gemini/settings.json` -> `mcpServers` (confirmed by docs snippets).
- Rules: `~/.gemini/GEMINI.md` and project `GEMINI.md`.
- Restart: extension changes require a CLI restart.

## Cursor - absent on this machine, partial verification

- Skills: `~/.cursor/skills` and `<ws>/.cursor/skills` (from the local skills-manager
  path map; Cursor documentation could not be fetched from this network).
- Plugins: `.cursor-plugin/plugin.json` exists in cross-tool packages, but no
  verified CLI install path. The manager refuses plugin distribution and points
  to the Cursor marketplace UI.
- MCP: `~/.cursor/mcp.json` and `<ws>/.cursor/mcp.json` (confirmed by VS Code's MCP
  reference table).
- Rules: `~/.cursor/rules/*.mdc`, `<ws>/.cursor/rules/*.mdc`, `AGENTS.md`.
- Link mode: unverified.

## VS Code / GitHub Copilot - official + local

Official docs (code.visualstudio.com/docs/agent-customization/agent-skills and
/docs/agents/reference/custom-instructions-reference, /mcp-configuration):

- Skills: project `.github/skills/`, personal `~/.copilot/skills/`. The Local harness
  also reads `.claude/skills` and `.agents/skills`; the Codex harness reads
  `.agents/skills` natively.
- Plugins: VS Code "Agent Plugins" via the Customization Marketplace, or
  extensions (`code --install-extension <vsix>`). Extension skills can be
  contributed with `contributes.chatSkills`.
- MCP: native Copilot files are `~/.copilot/mcp-config.json` (user) and workspace-root
  `.mcp.json`; `.vscode/mcp.json` is the deprecated Local-harness format with a
  `servers` key.
- Rules: `~/.copilot/copilot-instructions.md`, `.github/copilot-instructions.md`,
  `AGENTS.md`, `.github/instructions/**/*.instructions.md`.
- Restart: reload the VS Code window after extension changes; skills are
  discovered when a new chat session starts.

## Installed plugin inventory

`detect_resources.py --agent <id> --kinds plugins --json` lists installed plugins
without touching anything: Claude `installed_plugins.json` (id, scope, version,
install path), Codex `config.toml [plugins]` joined with cache versions, DSH
profile `dsh.profile.bundles` + `node_modules` versions, Gemini extensions, VS Code
extensions that contribute `chatSkills`. Use it before planning a plugin install
and to report version drift between tools (a real machine had Claude 0.50.0 and
Codex 0.48.0 of the same plugin). Never hand-copy a plugin cache.

## Capability semantics

| Capability | Meaning for distribution |
|---|---|
| `skill` | copy/link the skill directory into the first verified user skill dir |
| `plugin` | never copy; return the tool's install command and packaging evidence |
| `mcp` | merge a redacted server entry into a JSON config; TOML is manual |
| `rules` | new managed file in a rule folder, or a manual managed block in a shared file |
| `global` / `workspace` | whether user-level and project-level installs are both supported |
| `autodiscovery` | the tool loads skills without extra registration |
| `symlink` | verified link mode; currently Windows junctions were verified, other platforms unverified |
| `restart_required` | whether the tool must restart after a change |

## Adding a seventh tool

1. Copy an existing entry in `metadata/agents.json`.
2. Fill `home_env/home_default`, `markers`, `skills.user` and `skills.workspace`.
3. Declare plugin and MCP mechanisms honestly (`supported: no / unverified / yes`).
4. Add `verification` and `docs` plus notes describing the evidence.
5. Run `scan_agents.py --agent <id>`; if the skill directory is missing the tool
   is reported absent/config-only, which is correct.
6. Add tests to `evals/run_tests.py` for the new target before shipping.

The compatibility gate is data-driven: `compat_check()` reads the same entry the
scanner uses, so a wrong entry produces a visible refusal rather than a wrong
write.
