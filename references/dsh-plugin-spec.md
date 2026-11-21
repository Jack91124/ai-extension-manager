# DSH Plugin development specification - AI Extension Manager Dashboard

> **Status: specification only. Not implemented.** This document exists so the
> dashboard can be built later without changing the Skill's contract. Nothing in
> this file is available at runtime today; the Skill must not call these tools
> or routes until they exist in a shipped plugin.

## 1. Goal and scope

The plugin is the graphical management panel and local execution layer for the
system described in `architecture.md`. It consumes and produces the exact same
data (central library, registry, conflict states, agent registry) that the
bundled Python scripts already use, so the two backends are interchangeable.

In scope: five pages, local scanning, import/distribute/sync execution, conflict
centre, settings, operation log, diff viewer, seven backend operations exposed as
DSH tools. Out of scope: cloud sync, multi-user/team server, marketplace hosting,
model calls.

## 2. DSH plugin form factor (verified against DSH 0.2.0-rc.2)

A DSH plugin is an npm package mounted with
`dsh plugin --profile <name> add <package>`. The reference implementation on
this machine (`@michengai/dsh-skills-manager`) shows the required shape:

```text
ai-extension-manager-dashboard/
  package.json          name, dsh.bundle.patch, dsh.client.inject, exports, peerDeps
  cordis.patch.yml      loader patch entries that mount server + client plugins
  lib/index.js          server-side cordis plugin (ESM): tools, routes, services
  lib/client.js         web client plugin: pages/slots, React components
  lib/core.js           shared file-system / hashing / sync engine (port from aem_core.py)
  lib/types.d.ts
```

```json
{
  "name": "@your-scope/dsh-ai-extension-manager",
  "version": "0.1.0",
  "type": "module",
  "main": "lib/index.js",
  "exports": {".": "./lib/index.js", "./client": "./lib/client.js"},
  "dsh": {
    "bundle": {"patch": "./cordis.patch.yml"},
    "client": {
      "inject": ["@deepseek-ai/dsh-client-ui-slots",
                 "@deepseek-ai/dsh-client-locale",
                 "@deepseek-ai/dsh-client-ui-primitives"],
      "platform": "web"
    }
  },
  "peerDependencies": {
    "@deepseek-ai/cordis": ">=4.0.1 <5.0.0",
    "@deepseek-ai/dsh-host-webserver": ">=0.2.0-rc.1 <0.3.0-0",
    "@deepseek-ai/dsh-session": ">=0.2.0-rc.1 <0.3.0-0",
    "@deepseek-ai/dsh-skill": ">=0.2.0-rc.1 <0.3.0-0",
    "@deepseek-ai/dsh-tools": ">=0.2.0-rc.1 <0.3.0-0",
    "@deepseek-ai/dsh-web-app": ">=0.2.0-rc.1 <0.3.0-0",
    "react": "^18.2.0", "react-dom": "^18.2.0"
  }
}
```

Rules learned from the reference plugin: pin peer ranges to the host DSH release
line; ship `lib/` prebuilt (no build step at install time); declare every host
package you import in peerDependencies; register UI through slots rather than
patching the shell; keep server and client entry points separate.

## 3. Pages

### Page 1 - Dashboard

Purpose: one screen that answers "is my AI toolchain healthy?".

| Section | Content | Data source |
|---|---|---|
| KPI cards | resources total, skills, plugins, MCP, rules, conflicts open | registry |
| Tool status | 6 cards with installed/config-only/absent, CLI version, skill counts | `list_agents` |
| Recent activity | last 20 events (import/install/update/conflict/restore) | sync-history |
| Conflicts | open conflicts with resource + tool + state | conflicts/ |
| Health banner | stale journal, failed last run, backup age, library size | metadata/logs |

Actions: `Scan all tools`, `Open conflicts`, `View log`, `Refresh`.
States: loading skeleton; empty state explaining how to import the first skill;
error card with the failing operation id and a retry button.

### Page 2 - Resource Library

Purpose: inspect and manage everything in the central library.

- Table columns: name, type badge, version, hash (short), source (link),
  installed-in (agent chips), status, updated_at, size.
- Filters: type (skill/plugin/mcp/rules/other), status, tool, search by name or
  source, "has conflict" toggle.
- Detail drawer: metadata, manifest file tree, safety findings, version history
  with restore/compare buttons, target list with per-tool verify status,
  "open payload folder" (opens the OS file manager via host route).
- Actions: import (file picker / URL), inspect, compare versions, distribute,
  back up, delete-from-library (double confirmation, keeps backup).

### Page 3 - Agent Synchronization

Six independent cards (DSH, Codex, Claude Code, Gemini CLI, Cursor, VS Code
Copilot). Each card shows status, version, resolved skill path, skill count,
last sync, open conflicts, and buttons:

| Button | Operation | Progress |
|---|---|---|
| Scan | `scan_agent` | per-directory progress bar |
| Import from this tool | `sync_resource(import, agent)` | streamed step list |
| Distribute to this tool | `sync_resource(distribute, agent)` | streamed step list |
| Two-way sync | `sync_resource(both, agent)` | import then distribute phases |
| View diff | `compare_resource` | diff modal |
| View log | filtered operation log | drawer |

Page toolbar: `Scan all`, `Batch import`, `Batch distribute`, `Two-way sync all`,
`Sync all compatible resources`. Every batch shows a preview (what will change,
what will conflict, what will be skipped) before executing.

Absent tools: card is dimmed, buttons disabled with the tooltip "not installed -
no verified resource directory"; never create their directories.

### Page 4 - Conflict Center

- Conflict list grouped by resource: tool, state (A-F), detected time, library
  version vs target hash, quick diff.
- Detail: side-by-side or inline unified diff per file, binary marker, "3-way
  not available" note.
- Resolutions: keep library, keep target, manual merge (opens a file editor with
  save-to-library), save as new version. Each shows exactly what will be
  written, then requires confirmation. Resolution writes a history entry with
  both hashes.
- Backup panel: list backups for the resource and restore any of them.
- Bulk resolve is allowed only for identical-state conflicts and always previews.

### Page 5 - Settings

| Group | Fields |
|---|---|
| Library | root path (validated, must be writable), layout info, open folder, reindex |
| Agents | per-tool home override + user/workspace skill roots, verify button, "re-detect" |
| Sync | default mode (copy/link), default conflict policy (always ask by default), batch concurrency (1-4), auto-backup retention |
| Scanning | auto-scan on startup (off default), scan interval (off by default), include workspace scope, max depth |
| Security | risk threshold for auto-skip, require confirmation for plugin installs (locked on), secret policy (locked to redact), allowed plugin marketplaces |
| Appearance | language zh/en, theme inherited from host, density |

Settings persist to `<library>/metadata/settings.json` (same file the scripts read)
with schema versioning and validation; invalid paths are rejected, never
silently created.

## 4. Operation contract (must be identical to the Skill's contract)

The plugin registers these DSH tools. Inputs/outputs are the envelope from
`architecture.md` section 3; mutations require an idempotency key.

| Tool | Input | Output |
|---|---|---|
| `aem_list_agents` | `{scope?, workspace?}` | agents[] with status/paths/caps |
| `aem_scan_agent` | `{agent, scope?, kinds?}` | candidates[] with evidence/validation/safety |
| `aem_list_resources` | `{type?, query?, status?}` | records[] |
| `aem_inspect_resource` | `{id} or {path}` | classification + manifest + safety |
| `aem_import_resource` | `{source, type?, onConflict?, allowRisk?}` | imported record or conflict |
| `aem_install_resource` | `{id, agent, mode?}` | target state + hashes or manual command |
| `aem_sync_resource` | `{direction, agents[], resources[]?}` | steps[] + journal id |
| `aem_compare_resource` | `{left, right, diff?}` | versions + file diffs |
| `aem_resolve_conflict` | `{conflictId, resolution}` | resolved states + history id |
| `aem_backup_resource` | `{id, agent?}` | backup id |
| `aem_restore_resource` | `{backupId or id+version, to}` | restored hash |
| `aem_verify_sync` | `{id?, agent?, all?}` | per-target statuses |

Behaviour requirements:

- every operation returns the same status vocabulary as the scripts;
- conflicts are returned as data, never thrown as a generic error;
- long operations expose progress (`scan` 0-100, `plan`, `write` i/n, `verify`) and are
  cancellable; cancellation leaves a resumable journal;
- repeated calls with the same idempotency key return the stored result;
- file writes are staged + atomic rename, registry writes are atomic, and a
  lock serialises concurrent operations.

## 5. Backend HTTP routes (local only)

| Method | Route | Purpose |
|---|---|---|
| GET | `/aem/api/state` | dashboard snapshot (agents, resources, conflicts, last events) |
| GET | `/aem/api/agents` | agent registry + detection |
| GET | `/aem/api/resources` | paged/filtered records |
| GET | `/aem/api/resources/:id` | record + manifest + versions |
| POST | `/aem/api/import` | import |
| POST | `/aem/api/sync` | sync (returns operation id) |
| GET | `/aem/api/operations/:id` | progress/result |
| POST | `/aem/api/conflicts/:id/resolve` | resolve |
| GET | `/aem/api/compare` | diff |
| GET | `/aem/api/logs` | filtered events |
| POST | `/aem/api/backups` | backup |
| POST | `/aem/api/backups/:id/restore` | restore |

Constraints: bind to the host's local server only; origin checks; no arbitrary
file browser route (only paths inside the library/agents roots and a "reveal in
file manager" action); request body size limits; never return file contents that
match the secret scanner unless the user explicitly opens that file.

## 6. Data model

Reuse exactly (do not fork): `registry.json` resource records,
`agents.json` tool definitions, `sync-history.json` events, conflict JSON files,
backup manifests. Additions:

```json
// metadata/settings.json
{
  "schema": 1,
  "libraryRoot": "...",
  "agents": {"codex": {"homeOverride": null, "skillsOverride": null}},
  "sync": {"mode": "copy", "onConflict": "skip", "concurrency": 2},
  "scan": {"onStartup": false, "intervalSeconds": 0, "includeWorkspace": false},
  "security": {"riskThreshold": "medium", "requireConfirmation": true},
  "ui": {"language": "zh", "density": "comfortable"}
}
```

Operation journal (in memory + file): id, type, startedAt, steps[{key,label,state,
message}], cancellable flag, result envelope.

## 7. UI/UX requirements

- Chinese (default) and English strings, all text via locale files; no hardcoded
  copy in components.
- Every destructive or overwriting action: preview -> confirm -> result toast.
- Progress: determinate for known step counts, indeterminate for scanning, with
  a cancel button that actually stops before the next file.
- Errors: human message + operation id + "copy diagnostic" button; never a raw
  stack trace in the UI.
- Empty states explain the next action (e.g. "no skills yet - scan a tool").
- Keyboard: search focus, arrow navigation in tables, Esc closes drawers.
- Accessibility: labels on icon buttons, focus rings, contrast per host theme.
- Density: tables virtualised above 500 rows.
- Never display a secret; masked values show only a 6-char prefix.

## 8. Security requirements

1. Server-side validation of every path against allowlisted roots.
2. No shell execution from the UI except the explicitly previewed plugin install
   command, which is shown verbatim and requires a separate confirmation.
3. Secrets redacted at the service boundary (same scanner as the scripts).
4. Audit every mutation to sync-history + operations.jsonl with hashes.
5. CSP-safe client code; no remote code loading; no telemetry by default.
6. The plugin must work offline; only import/download needs network.
7. Reading outside the library and verified agent roots is forbidden.

## 9. Performance targets

| Operation | Target |
|---|---|
| Dashboard load (1k resources) | < 300 ms |
| Scan one tool with 50 skills | < 2 s |
| Distribute one skill | < 300 ms + I/O |
| Diff one skill (< 100 files) | < 500 ms |
| Full verify (6 tools, 200 targets) | < 5 s |
| Memory footprint | < 150 MB |

Cache manifests by (path,size,mtime,hash) to avoid re-hashing unchanged files,
invalidate on registry change.

## 10. Implementation phases

| Phase | Deliverable | Exit criteria |
|---|---|---|
| P0 | port `aem_core.py` to `lib/core` (hashing, state machine, install, verify) | unit tests mirror the Python suite |
| P1 | server tools + routes, no UI | every operation callable and covered by API tests |
| P2 | Dashboard + Settings pages | state loads, settings round-trip |
| P3 | Resource Library + Agent Synchronization | import/distribute/sync from UI, progress works |
| P4 | Conflict Center + diff viewer | resolve all four ways with history |
| P5 | i18n, accessibility, polish, packaging | install via `dsh plugin ... add` on a clean profile |

## 11. Test plan

- Port the 19 scenario tests from `evals/run_tests.py` to the JS core; they are the
  behavioural contract (classification, import, both directions, conflicts,
  restore, absent tool, blocked path, incompatible plugin, batch, checksum,
  idempotency, risky skill, secrets, invalid SKILL.md).
- API tests: auth/origin, path traversal, oversized body, concurrent sync lock,
  cancellation/resume, idempotency key.
- UI tests: pages render with fixtures, conflict resolution flow, progress, i18n.
- Manual acceptance on a machine with all six tools installed.

## 12. Acceptance criteria (dashboard)

1. Dashboard shows correct totals and six tool statuses without a manual refresh
   after a sync.
2. Library page lists all resources, filters by type, opens source and version.
3. Each tool card performs scan/import/distribute/two-way/diff/log end to end.
4. Batch operations preview their plan and never silently overwrite.
5. Conflict Center resolves each state and records both hashes.
6. Settings changes take effect without restarting DSH, and invalid paths are
   refused.
7. All mutating operations appear in the operation log with results.
8. No operation exposes a secret; scanner blocks risky imports without explicit
   confirmation.

## 13. Explicit non-goals and open questions

- No cloud/team sync; conflicts are per machine.
- No automatic text merge; manual merge opens files.
- No running arbitrary plugin installers without a confirmation dialog.
- Open: how to represent a plugin install in progress (the tool CLI is a child
  process), and whether to support Windows junctions across volumes in link mode.

When this plugin ships, the Skill should call its tools first and fall back to
the Python scripts only if the plugin is unavailable. Until then, the scripts are
the single implementation.
