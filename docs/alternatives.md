# Choosing an agent-skills manager

The AI-agent skill ecosystem got crowded fast. Most tools in this space solve one of two problems:
**finding/installing** skills from the internet, or **managing the copies** already on your disk.
aem is firmly in the second camp, and this page says honestly where it fits — including when you
should pick something else.

*Snapshot: November 2026. Tool descriptions and features change; follow the links for the current state.*

## Two families of tools

| Family | Examples | What it is good at | What it usually does not do |
|---|---|---|---|
| Installers / registries | [vercel-labs/skills](https://github.com/vercel-labs/skills) (`npx skills add`), [MoizIbnYousaf/ai-agent-skills](https://github.com/MoizIbnYousaf/ai-agent-skills), [enulus/OpenPackage](https://github.com/enulus/OpenPackage) | one command installs a skill from GitHub into one or many agents; discovery and packaging | keeping track of what changed where after the install |
| Manager apps / CLIs | [xingkongliang/skills-manager](https://github.com/xingkongliang/skills-manager), [jiweiyeah/Skills-Manager](https://github.com/jiweiyeah/Skills-Manager), [luongnv89/asm](https://github.com/luongnv89/asm), **aem** | a central copy, then copy/link it to every agent you use; scan, sync, remove | conflict semantics differ wildly between implementations |

## What aem deliberately does differently

1. **It remembers three hashes per copy**, not one: the library hash, the hash at the last sync, and
   the target's current hash. A two-way change is a *conflict* (exit code 2, nothing written), not a
   last-writer-wins race. Most "sync" tools compare modification times — see
   [why mtime is the wrong default](why-sync-overwrites.md).
2. **It refuses to guess.** Eight conflict states (A–E plus untracked/modified/deleted) each have a
   fixed resolution, and `--on-conflict` must be explicit. Every write is preceded by a per-target
   backup you can restore with `aem restore`.
3. **It verifies instead of assuming.** `aem verify --all` re-hashes installed copies against the
   library; `aem report` renders the result as one HTML page. A copy that drifted is *reported*, never
   silently repaired.
4. **It is honest about support.** The six adapters carry a verification level
   (verified locally / official docs / partial / unverified) — see the
   [support matrix](https://jack91124.github.io/ai-extension-manager/#support). If a tool is absent,
   a plugin mechanism is unverified, or a write is manual, the CLI says so instead of pretending.
5. **It is a plain Python CLI with zero runtime dependencies.** No daemon, no database, no telemetry;
   it works over SSH, in CI, and inside a sandbox. JSON output everywhere.

## What aem does *not* do

- **No GUI yet.** The DSH plugin dashboard is a [specification](../references/dsh-plugin-spec.md), not
  a product. If you want a desktop window, the manager apps above are a better fit today.
- **Six tools, not fifty.** Claude Code, Codex, Gemini CLI, Cursor, VS Code Copilot and DSH are
  supported with per-tool directories verified against docs or a local install. Adding more is a
  registry entry, but unverified adapters are marked as such.
- **No marketplace / browsing.** aem imports what you point it at; it does not discover skills for you.
- **No automatic plugin installation.** Tool-specific plugins go through each tool's own install
  command; aem tracks them, it does not vendor them.
- **Young project.** v1.0.x, single maintainer, 31 scenario tests. Expect sharp edges.

## A short decision guide

- *"I just want `npx skills add owner/repo` to install a skill."* → use the
  [`skills` CLI](https://github.com/vercel-labs/skills).
- *"I want a desktop window that shows everything I have in every tool."* → one of the manager apps.
- *"I edit my skills in several tools, and I am tired of one copy silently winning."* → aem's
  hash-based state machine is built for exactly that.
- *"I need this in CI / on a server / in a script."* → aem is headless by design.
- *"I want one command to sync to DSH, Codex and Claude Code, and a report I can trust."* → aem.

## Sources

- Paths and formats per tool: [where each tool keeps its skills](https://jack91124.github.io/ai-extension-manager/where.html)
  (generated from the same registry the CLI uses).
- Conflict states: [references/conflict-resolution.md](../references/conflict-resolution.md).
- Feature comparison against naive sync scripts: [Why overwrite-on-mtime is wrong](why-sync-overwrites.md).
