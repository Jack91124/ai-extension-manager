# Synchronization engine

## 1. Model

The library is the shared source of truth, but it is **not** an authority that
may overwrite tools. Every target copy has a recorded state:

```json
"targets": {
  "codex": {
    "agent": "codex", "scope": "user",
    "path": "C:/Users/me/.codex/skills/demo",
    "mode": "copy",
    "source_hash": "<library hash at last sync>",
    "target_hash": "<hash written to the target>",
    "version": "2026.11.21-120000",
    "synced_at": "2026-11-21T12:00:00Z",
    "last_action": "install"
  }
}
```

Two hashes are enough to separate "the library moved" from "the target moved"
without trusting modification times. Mtimes are recorded only as advisory
metadata; they never decide an overwrite.

## 2. Conflict state machine

```text
                library_hash == recorded source?     actual == recorded target?
                         yes                no          yes        no
in-sync                    x                 -            -          -
A (library only)           -                 x            x          -
B (target only)            x                 -            -          x
C (both)                   -                 x            -          x
D (target deleted)         state exists in record but path is missing
E (never existed)          no record and path missing
untracked                  path exists, no record, hashes differ
```

Rules:

- `in-sync`: skip. No write, no backup.
- `A`: distribute may update after a target backup.
- `B`: distribute refuses (exit 2) and points at the import direction.
- `C`: both directions refuse. A conflict record is written under
  `conflicts/` and the user must choose.
- `D`: distribute restores the target from the library (backup not needed).
- `E`: never create a tool directory for an absent tool; report
  `unavailable`.
- `untracked`: a copy exists that the library never saw. Import-or-adopt;
  never overwrite silently.

Implementation: `compute_target_state()` in `scripts/aem_core.py`; tested by scenarios
8, 14 and 15.

## 3. Directions

### Import (tool -> library)

For each detected tool and each skill directory:

1. enumerate child directories containing `SKILL.md`;
2. validate the skill (name, description, frontmatter, body);
3. record the target as `adopt-on-import` if identical, else decide by state;
4. state B -> new library version (snapshot the previous payload first);
5. state A -> skip ("library is ahead; distribute instead");
6. state C / untracked -> conflict record, no writes;
7. new -> stage, scan safety, commit, write registry + history.

### Distribute (library -> tool)

1. compatibility gate (`skill` is portable; `plugin` must match the tool's packaging;
   `mcp` needs a JSON config; `rules` needs a rules location);
2. resolve the real target path from `agents.json`;
3. compute state (above);
4. conflict -> write evidence, return `conflict`;
5. otherwise backup target, write to a staging sibling, atomically replace,
   re-hash, record the target, log the event;
6. verify in the same call (hash mismatch is a failure, not a success).

### Both

Import then distribute. Rationale: target-only changes become library versions;
library-only changes then reach the targets without two conflict passes.

## 4. Modes

| Mode | Behaviour | Verified |
|---|---|---|
| `copy` | independent copy; default; portable | Windows, all six tool path types |
| `link` | junction/symlink to `library/<type>/<slug>/payload` | Windows junction verified (Copilot target); macOS/Linux symlink and per-tool behaviour unverified |

Link mode requires the library to be on the same volume, otherwise the tool may
not follow it. Verification resolves the link and compares the resolved target;
a link pointing elsewhere is reported as `corrupted`.

## 5. Idempotency and interruption

- Content-addressed manifests make repeating a run a no-op: identical payloads
  produce `skip` and no backup (test 15 asserts the backup count is unchanged).
- Mutations are staged then atomically replaced (`os.replace`) so a crash cannot leave
  a half-written skill directory.
- `staging/journal-<direction>.json` records completed step keys
  (`"<direction>:<agent>:<path>"`). A rerun with `--resume` skips completed steps.
  Dry runs never mark steps as done.
- A lock file (`metadata/.library.lock`) serialises import/sync/backup processes;
  stale locks older than 5 minutes are broken.
- The registry is written atomically (temp file + fsync + replace).

## 6. Safety rails

| Situation | Engine behaviour |
|---|---|
| Target equals library | skip, no writes |
| Target differs, untracked | conflict, no writes |
| Both changed | conflict, no writes |
| Agent absent | unavailable, never mkdir |
| Parent path is a file | clean "write failed" error, no traceback |
| Payload hash after write differs | error + restore hint, never "success" |
| Library payload missing | error, no distribution |
| Plugin targeted at a different tool | blocked with per-tool packaging reason |
| Shared instruction file exists | manual managed-block instruction |
| MCP entry exists with different values | conflict unless explicitly overwritten |

## 7. CLI summary

```bash
# import everything visible in every installed tool
python scripts/sync_resources.py --direction import --json

# distribute one resource to three tools
python scripts/sync_resources.py --direction distribute \
  --agent dsh --agent codex --agent claude --resource demo-notes --json

# all resources to all compatible tools (dry run first)
python scripts/sync_resources.py --direction distribute --all --dry-run --json

# two-way for one tool with link mode
python scripts/sync_resources.py --direction both --agent cursor --mode copy --json

# resume an interrupted run
python scripts/sync_resources.py --direction distribute --all --resume --json
```

Exit codes: 0 all good, 2 conflicts (nothing overwritten), 1 errors/rejections.

## 8. Performance characteristics

Hashing dominates. The engine reads every file once per comparison; a skill with
100 files of 1 MB is about 100 MB of I/O per side. For normal skills (tens of
KBs) a full-machine scan is well under a second. The registry stores the
manifest so repeated syncs do not re-hash unchanged library payloads beyond the
target comparison.
