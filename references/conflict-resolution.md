# Conflict resolution

## 1. Principle

A conflict means the system **cannot know** what the user wants. Both sides
changed after the last successful sync; picking a winner by timestamp loses data.
Therefore:

- the default behaviour is to stop and preserve evidence;
- the user chooses one of four resolutions;
- every resolution is reversible (backup + version snapshot);
- no resolution is applied silently.

## 2. Detecting a conflict

```text
record.hash                current library hash
target.source_hash         library hash at last sync
target.target_hash         hash written to the target at last sync
actual_hash                hash of the target right now
```

| library == source_hash | actual == target_hash | meaning | state |
|---|---|---|---|
| yes | yes | in sync (unless actual != library, see note) | in-sync |
| no | yes | library changed only | A |
| yes | no | target changed only | B |
| no | no | both changed | C |

Additional states: `D` (recorded target path missing), `E` (no record, no path),
`untracked` (path exists, no record, different content), `F` (resource exists only in
a target). `compute_target_state()` implements this; scenario test 8 asserts that
state C never overwrites the target.

## 3. Where conflicts are stored

```text
conflicts/
  demo-notes-codex.json            one file per resource+agent (sync conflicts)
  demo-notes-<incoming-hash>/      import conflicts keep the incoming payload
    payload/
    conflict.json
```

Conflict record:

```json
{
  "id": "skill/demo-notes@codex",
  "resource_id": "skill/demo-notes",
  "resource_name": "demo-notes",
  "agent": "codex",
  "state": "C",
  "description": "both the library and the target changed (manual merge needed)",
  "detected_at": "2026-11-21T13:00:00Z",
  "library": {"version": "...", "hash": "...", "path": "..."},
  "target": {"path": "...", "hash": "..."},
  "resolution_options": ["keep-library", "keep-target", "manual-merge", "save-as-new-version"],
  "resolved": false
}
```

The history log (metadata/sync-history.json and logs/operations.jsonl) records
every detection and resolution with hashes, so the decision is auditable.

## 4. The four resolutions

### Keep library (target is stale)

```bash
python scripts/compare_resources.py --left resource:demo-notes --right agent:codex:demo-notes --diff
python scripts/sync_resources.py --direction distribute --agent codex \
  --resource demo-notes --on-conflict library --json
python scripts/verify_sync.py --resource demo-notes --agent codex --json
```

The engine backs up the target first. Use when the library version is the one
the user wants and the target edit was accidental.

### Keep target (target is newer)

```bash
# simplest: import the agent's copy directly
python scripts/import_resource.py --source ~/.codex/skills/demo-notes --on-conflict keep-source
# or resolve it inside the sync engine (target/keep-source/new-version are accepted)
python scripts/sync_resources.py --direction import --agent codex --resource demo-notes \
  --on-conflict new-version --json
```

The previous library payload becomes a version snapshot, the target content
becomes the new library version, and the target is recorded as in sync.

### Manual merge (both are meaningful)

1. Show both copies:
   `compare_resources.py --left resource:<name> --right agent:<agent>:<name> --diff`
2. Let the user edit the library payload at
   `<AEM_HOME>/library/<type>/<slug>/payload/` (or produce a merged file).
3. Distribute with `--on-conflict library` (the engine still backs up the target).
4. Verify.

The manager never auto-merges text; a bad merge is worse than an explicit edit.
For binary files, always pick a side, never merge.

### Save as new version (keep both, branch)

```bash
python scripts/sync_resources.py --direction import --agent codex --resource demo-notes \
  --on-conflict new-version --json
```

The imported content becomes the current version; the previous payload stays
under `versions/` and can be compared or restored (workflow G).

## 4b. Resolution flags on the sync CLI

`sync_resources.py --on-conflict` accepts:

| Value | Direction | Meaning |
|---|---|---|
| `skip` | both | conflict is reported, nothing written (exit 2) |
| `library` / `overwrite` | distribute | target is stale: backup then overwrite (explicit user decision) |
| `target` | distribute | keep the target as-is: returns `kept-target`, no write, no conflict file |
| `target` / `keep-source` / `new-version` | import | target is authoritative: capture it as a new library version |

`--force` is not a conflict resolution; it only bypasses SKILL.md validation.
A dry-run that would conflict also exits 2, so scripts and CI can rely on the
exit code.

## 5. Import-side conflicts

When importing a payload that differs from an existing library resource:

| `--on-conflict` | Effect |
|---|---|
| `skip` (default) | incoming payload staged under `conflicts/<slug>-<hash>/`, exit 2 |
| `keep-library` | incoming discarded, library untouched |
| `keep-source` | current payload snapshotted + backed up, incoming becomes current |
| `new-version` | same as keep-source, recorded as an explicit new version |

Never retry an import with `--force` to "get past" a conflict: force only bypasses
SKILL.md validation, not conflict protection.

## 6. Deletion and absence

| Situation | Handling |
|---|---|
| Target deleted (state D) | distribute restores it from the library (no data loss risk) |
| Library deleted, target remains (state F) | import recreates the resource from the target |
| Tool uninstalled / directory absent (E) | report unavailable; do not recreate the product directory |
| User wants to uninstall | remove the target copy only after backup; the skill layer has no destructive uninstall command, use `backup_restore.py backup` + manual removal, or wait for the Plugin |

## 7. Decision checklist to present to the user

1. What changed on each side, file by file (from `compare_resources.py --diff`).
2. Which side is authoritative for this resource.
3. Whether the other side's change is worth keeping as a version.
4. Whether the tool needs a restart after the resolution.
5. The exact command that will run and what it will overwrite.

Only after those five answers apply a resolution and verify.
