# AI Extension Manager - Scenario Test Report

- generated: 2026-11-25T17:03:59Z
- result: **29/29 passed**
- duration: 41.17s

| # | scenario | result | seconds | evidence |
|---|---|---|---|---|
| 1 | test_01_classify_github_skill | PASS | 0.6 | skill detected in repo; github URL classified |
| 2 | test_02_classify_github_plugin | PASS | 0.34 | dsh plugin manifest recognised |
| 3 | test_03_import_skill | PASS | 0.45 | imported with complete metadata (2 files) |
| 4 | test_04_import_from_claude | PASS | 0.6 | claude skill imported and target recorded |
| 5 | test_05_distribute_to_codex | PASS | 1.02 | distributed and verified on codex |
| 6 | test_06_reverse_import_modified | PASS | 1.44 | reverse import updated the library and stayed in sync |
| 7 | test_07_compare_versions | PASS | 1.1 | two versions compared with a unified diff |
| 8 | test_08_conflict_detection | PASS | 2.84 | state C detected, dry-run exits 2, explicit resolutions work |
| 9 | test_09_restore_old_version | PASS | 1.2 | old version restored and hash verified |
| 10 | test_10_missing_tool | PASS | 2.14 | absent tool reported and never written to |
| 11 | test_11_blocked_target | PASS | 0.69 | blocked path produced an actionable error instead of a crash |
| 12 | test_12_incompatible_plugin | PASS | 1.06 | cross-tool plugin distribution refused with explanation |
| 13 | test_13_batch_sync | PASS | 1.22 | three tools synced and verified in one command |
| 14 | test_14_checksum_failure | PASS | 1.13 | missing and modified files detected by checksum verification |
| 15 | test_15_interrupted_and_repeat | PASS | 2.26 | repeat run is idempotent; journal resumes; dry runs leave no journal |
| 16 | test_16_unsafe_skill | PASS | 0.67 | high-risk script blocked until --allow-risk |
| 17 | test_17_secret_handling | PASS | 1.17 | skill credential refused; MCP credential replaced with an env placeholder |
| 18 | test_18_invalid_skill | PASS | 0.7 | invalid SKILL.md rejected unless --force is explicit |
| 19 | test_19_git_mirror_rewrite | PASS | 0.45 | third-party git mirror refused before any clone |
| 20 | test_20_cli_doctor | PASS | 2.51 | doctor reports actionable warnings, init fixes them, machine is healthy |
| 21 | test_21_cli_status | PASS | 1.57 | status summarises each target and --strict turns drift into a failure |
| 22 | test_22_cli_aliases | PASS | 1.16 | aliases dispatch correctly, unknown commands exit 2 |
| 23 | test_23_direct_library_edit | PASS | 2.0 | out-of-band library edits refresh the hash; later both-side edits conflict as state C |
| 24 | test_24_compare_missing_operand | PASS | 1.39 | compare reports changed files, and unknown operands fail cleanly instead of crashing |
| 25 | test_25_cli_adopt_and_distribute | PASS | 1.19 | aem adopt pulls from a tool; aem distribute pushes to a tool |
| 26 | test_26_cli_report | PASS | 3.12 | report renders resources, targets, drift and tool status into one HTML file |
| 27 | test_27_cli_import_pick | PASS | 1.45 | ambiguous bundle exits 2 with candidates; --pick imports one; --all imports every match |
| 28 | test_28_cli_dirs | PASS | 4.2 | aem dirs resolves skills/MCP/rules paths per tool with scope, filters and unknown-agent errors |
| 29 | test_29_init_unwritable_root | PASS | 0.27 | unwritable root produced a clean actionable error |
