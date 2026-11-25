# JSON result contract (`aem.result/v1`)

Every CLI script in `scripts/` that accepts `--json` emits a single JSON object
on stdout. `aem_core.emit_json()` is the single output funnel, so the contract
below applies to **all** commands — `scan_agents.py`, `detect_resources.py`,
`import_resource.py`, `sync_resources.py`, `compare_resources.py`,
`verify_sync.py`, `backup_restore.py`, and every `aem ... --json` subcommand.

## Envelope fields (always present, added automatically)

| Field | Type | Meaning |
|---|---|---|
| `schema` | string | Result envelope version. Currently `aem.result/v1`. Incremented only when a field is renamed, removed, or changes type. |
| `tool_version` | string | Semantic version of the tool that produced the result (e.g. `1.0.17`). Distinct from `schema`: the tool may add optional fields without a schema bump. |

A caller that supplies either field explicitly wins (the injection never
overwrites an existing value). All pre-existing command-specific top-level
fields — `ok`, `generated_at`, `results`, `summary`, `agents`, `checks`, `diffs`,
`backups`, `conflicts`, `errors`, `warnings`, `home`, `direction`, and others —
keep their names and types. This is a strictly additive change; existing
consumers keep working.

## Command-specific payloads

The envelope fields are merged into each command's existing result object:

- `scan_agents.py` → `{ok, generated_at, home, workspace, agents[], summary}`
- `detect_resources.py` → `{ok, mode, generated_at, candidates[], summary, summary_text}`
- `import_resource.py` → `{ok, source, results[], summary, conflicts, errors}`
- `sync_resources.py` → `{ok, direction, results[], summary, conflicts, errors, manual}`
- `compare_resources.py` → `{ok, left, right, differences[], diffs[], errors[]}`
- `verify_sync.py` → `{ok, checks[], summary, unmanaged[], problems[], unmanaged_count}`
- `backup_restore.py` → `{ok, backups[]/backup/..., count/...}`

Consumers should read what they need by key and never assume the object has
*only* the listed keys. New optional keys may be added in any tool release.

## Exit codes (unchanged)

0 success · 1 failure/invalid input · 2 conflict or unconfirmed risk.

Conflict cases return machine-readable data (`action: "conflict"` /
`"would-conflict"`, and a `conflicts` count on `sync`), never a generic error.
They exit 2 on the CLI; the JSON is still valid and complete.

## Plugin backend contract

The future DSH Plugin wraps these same results in the richer envelope defined
in `architecture.md` section 3 (`operation`, `data`, `conflicts[]`,
`errors[]`, `warnings[]`). It must preserve `schema` and `tool_version` from
the CLI result inside `data` so a client can detect an outdated backend.
No new status vocabulary is permitted (see `architecture.md` section 3).

## Compatibility policy

- Adding an optional field → no `schema` bump; bump `tool_version`.
- Renaming/removing a field, or changing a field's type → bump `schema`
  (`aem.result/v2`, ...) and keep the v1 emitter available for one release.
- Tests: `evals/run_tests.py::test_32_json_contract_fields` asserts the
  envelope on five representative commands and the no-clobber behaviour.
