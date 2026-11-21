# Architecture

## 1. Why two layers

The system is deliberately split into a **decision layer** and an **execution
layer**. Mixing them is what makes most "AI tool managers" unreliable: a chat
model cannot be trusted to know a machine's real directories, and a GUI cannot
judge whether a third-party script is safe.

```text
User request (natural language)
        |
        v
+---------------------------+        plan / confirm        +----------------------------+
| Skill: decision layer     | --------------------------> | Plugin: execution layer   |
| classify, inspect, plan,  |                             | UI, scan, copy, link,     |
| review risk, choose tool, | <-------------------------- | diff, install, log        |
| verify, report            |      verified results       +----------------------------+
+---------------------------+                                          |
        | fallback when no plugin                                      v
        +--------------------> bundled Python CLI ------------> central library + agents
```

| Concern | Skill | DSH Plugin | Bundled scripts |
|---|---|---|---|
| Understand intent | yes | no | no |
| Classify GitHub repo / resource | yes | no | deterministic helpers |
| Security review + user confirmation | yes | shows UI only | pattern scanner |
| Know real tool paths | reads registry, never guesses | scans + serves | detects + persists |
| File copy / link / hash | plans | executes | executes (phase 1) |
| Conflict decision | proposes + asks | presents options | detects, refuses to guess |
| GUI, progress, logs, diffs | no | yes | text/JSON output |
| Result verification | interprets | reports | computes hashes |

Phase 1 (this deliverable) implements Skill + scripts. The Plugin is a
specification only (see `dsh-plugin-spec.md`). The Skill must never call a plugin
operation that does not exist at runtime; it checks for availability first.

## 2. Components

```text
~/.ai-extension-manager/                 (AEM_HOME, configurable)
  library/
    skills/<slug>/payload/               portable Agent Skills
    plugins/<slug>/payload/              tool-specific plugin package
    mcp/<slug>/payload/server.json       redacted MCP server definition
    rules/<slug>/payload/content.md      instructions / rules text
    other/<slug>/payload/                unclassified, archived only
  metadata/
    registry.json                        one record per resource
    agents.json                          per-tool paths + capability flags
    sync-history.json                    append-only operation events
  backups/<utc>-<type>-<slug>-<agent>/   payload + manifest.json
  staging/                               clone/import work + conflict staging + journals
  conflicts/                             unresolved conflict evidence
  logs/operations.jsonl                  machine-readable audit trail
```

Each library resource directory contains:

```text
<type>/<slug>/
  payload/                  current content (what is distributed)
  resource.json             copy of the registry record
  versions/<label>/payload/ immutable version snapshots for restore/compare
  versions/<label>/version.json
```

## 3. Operation contract

The contract below is the interface the Skill uses. **Phase 1 maps every
operation to a bundled script; the Plugin must implement the same operations
before it can be used as a backend.** Every operation returns the envelope:

```json
{
  "ok": true,
  "operation": "sync_resource",
  "generated_at": "2026-11-21T13:00:00Z",
  "data": {},
  "conflicts": [],
  "errors": [],
  "warnings": []
}
```

Exit codes used by the CLI (Plugin must map them to the same semantics):
0 success, 1 failure/invalid, 2 conflict or unconfirmed risk.

| Operation | Input | Output | Implemented by |
|---|---|---|---|
| `list_agents` | scope, workspace | tool status, paths, versions, capabilities | `scan_agents.py` |
| `scan_agent` | agent id, scope, kinds | resource candidates with evidence | `detect_resources.py --agent` |
| `list_resources` | type filter, query | registry records | registry.json (read) |
| `inspect_resource` | id/path | classification, validation, safety, manifest | `detect_resources.py --path --safety` |
| `import_resource` | source, type, conflict policy | imported record or conflict | `import_resource.py` |
| `install_resource` | resource id, agent, mode | installed target + hashes | `sync_resources.py --direction distribute` |
| `export_resource` | resource id, destination | copied payload | not yet a first-class command (use payload path) |
| `sync_resource` | direction, agents, resources | per-step actions | `sync_resources.py` |
| `compare_resource` | left, right operands | versions, manifests, unified diffs | `compare_resources.py` |
| `resolve_conflict` | conflict id, resolution | updated record/target | explicit `--on-conflict` flags |
| `backup_resource` | id, agent | backup id + manifest | `backup_restore.py backup` |
| `restore_resource` | backup id or version | restored payload + hash | `backup_restore.py restore` |
| `verify_sync` | resource/agent/all | per-target status | `verify_sync.py` |

`export_resource` and a one-shot `resolve_conflict` command are designed but not
exposed as dedicated CLIs; they are composed from the operations above. The
Plugin specification requires first-class implementations.

### Request/response rules for the future Plugin

- Every mutating call carries an idempotency key; repeating the same call with
  the same key must return the previous result instead of writing twice.
- Long operations stream progress events (`scan`, `plan`, `write`, `verify`) and finish with the
  envelope; cancellation must leave a journal that `sync_resource` can resume.
- The Plugin must return the same conflict states (A-F) and the same status
  strings; no new vocabulary.
- Errors are coded: `not-found`, `unverified-agent`, `incompatible`, `conflict`,
  `permission-denied`, `blocked-path`, `invalid-resource`, `unsafe`, `secret-detected`,
  `write-failed`, `hash-mismatch`.
- The Plugin must never report success before re-hashing the written target.

## 4. Data flow

### Import (tool -> library)

```text
scan agent skill dirs -> candidate dirs -> validate SKILL.md -> safety scan
  -> hash payload -> compare with registry (name/hash)
  -> new: stage -> library/<type>/<slug>/payload -> record + history
  -> same hash: skip
  -> different hash: conflict policy (skip default) -> conflicts/ or new version
```

### Distribute (library -> tool)

```text
record -> capability gate (skill/plugin/mcp/rules) -> resolve target path
  -> compare recorded state (A-F) -> if conflict: stop + evidence
  -> backup target -> copy/link -> re-hash -> record target -> verify
```

### Two-way

Import first so target-only changes become library versions, then distribute so
library-only changes reach targets. A single `--direction both` run is equivalent
to import then distribute and is safe to repeat.

## 5. Extension points

**Add an AI tool**: add an entry to `metadata/agents.json` (or the defaults in
`scripts/aem_core.py`) with home env/default, skill directories (user and
workspace), plugin system/manifests/install command, MCP config paths and rule
paths, plus a `verification` level and `docs` URL. The engine needs no code change
for skills; plugins/MCP/rules work as soon as the declared paths exist.

**Add a resource type**: add the kind directory under `library/`, a classifier in
`classify_path()`, a payload normaliser in `import_resource.py`, an installer in
`install_payload()`, a verifier branch and a compatibility rule. Do not special
case types inside the sync loop.

## 6. Non-goals (phase 1)

- No GUI, no background watcher, no auto-update daemon.
- No execution of third-party installers; plugin install is a reviewed plan.
- No automatic text merge of conflicting files.
- No cross-tool plugin copying.
- No credential storage; secrets are placeholders only.
