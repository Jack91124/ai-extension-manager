# Roadmap

The goal is narrow and measurable: **make "sync my agent skills across tools" safe enough that you
stop hand-copying directories** — then grow from there.

## Now (v1.0) — shipped

- [x] Central library + six adapters + honest verification levels
- [x] Two-way sync with hash-based A/B/C/D/E conflict detection
- [x] Backups, restore, compare, verify, dry runs, resumable journals
- [x] Security scanning, secret refusal, mirror-rewrite refusal
- [x] `aem doctor` / `aem status` / JSON contracts
- [x] 22 scenario tests + reproducible demo

## Days 1–30 — make it trustworthy for strangers

- [x] CI on Ubuntu, macOS and Windows × Python 3.9 / 3.12 (tests + `pip install .` + `aem doctor`) — six jobs green on v1.0.1
- [ ] Publish v1.0.0 and v1.0.1 (done: GitHub + Gitee tags); still to do: `npx skills`-compatible layout and skills.sh badge
- [ ] `aem doctor` detects library edits that bypass the registry (payload hash drift)
- [ ] `aem sync --json` stable schema documented with a version field
- [ ] One real end-to-end run recorded on each of the six tools (or documented as blocked)
- [ ] Collect the first 10 issues and fix the top 3 friction points

**Metric:** 25+ stars, 5+ external issues, CI green on all three operating systems.

## Days 31–60 — reduce the sharp edges

- [ ] Adapter SDK: a tool adapter is a JSON/Markdown file, not a patch to `aem_core.py`
- [ ] Content-addressed payload store (deduplicate identical skill versions)
- [ ] Incremental scan (mtime + hash cache) for libraries with 100+ resources
- [ ] `aem diff` visual summary + `--on-conflict merge` with a three-way merge of text files
- [ ] Team mode: export/import a signed library bundle without credentials
- [ ] Schema migration from v1 with a dry-run report

**Metric:** 100+ stars, first contributor PR merged, median issue response < 7 days.

## Days 61–90 — the execution layer

- [ ] DSH Plugin P0: Dashboard, Agent Synchronization, Conflict Center read paths
- [ ] Plugin execution over a local HTTP contract (the 12 operations in
      `references/dsh-plugin-spec.md`), with the CLI as the single implementation
- [ ] Plugin itself installable with `dsh plugin --profile desktop add <pkg>`
- [ ] Optional: VS Code extension surface for the same contract

**Metric:** demo video published, 300+ stars, Plugin preview usable by 10 testers.

## Later / explicitly not now

- Plugin auto-install by driving each vendor CLI (fragile; vendors change flags)
- Cloud sync / accounts — the library stays local-first
- Marketplace or ranking of skills — out of scope for a sync tool
- A second implementation language — the Python CLI is the only source of truth

## Decision log

- **CLI first, Skill second.** The Skill is a natural-language wrapper; the CLI holds the behaviour.
  A GUI without a correct engine would only hide bugs.
- **Hash-first conflict detection.** Modification time cannot distinguish "copied with a new mtime"
  from "edited"; recorded hashes can.
- **No silent overwrite, ever.** A sync tool that loses a local edit is worse than no sync tool.
- **Plugins are delegated.** Copying a Claude plugin into Codex creates a broken install; returning
  the vendor command is honest.
- **DSH Plugin is P2.** The GUI is valuable but it multiplies the surface; the engine must be stable
  first.
