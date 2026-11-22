# AI Extension Manager - Scenario Test Report

- generated: 2026-11-22T09:47:38Z
- result: **26/26 passed**
- duration: 23.39s

| # | scenario | result | seconds | evidence |
|---|---|---|---|---|
| 1 | test_01_classify_github_skill | PASS | 0.51 | skill detected in repo; github URL classified |
| 2 | test_02_classify_github_plugin | PASS | 0.21 | dsh plugin manifest recognised |
| 3 | test_03_import_skill | PASS | 0.26 | imported with complete metadata (2 files) |
| 4 | test_04_import_from_claude | PASS | 0.39 | claude skill imported and target recorded |
| 5 | test_05_distribute_to_codex | PASS | 0.74 | distributed and verified on codex |
| 6 | test_06_reverse_import_modified | PASS | 0.98 | reverse import updated the library and stayed in sync |
| 7 | test_07_compare_versions | PASS | 0.71 | two versions compared with a unified diff |
| 8 | test_08_conflict_detection | PASS | 1.87 | state C detected, dry-run exits 2, explicit resolutions work |
| 9 | test_09_restore_old_version | PASS | 0.77 | old version restored and hash verified |
| 10 | test_10_missing_tool | PASS | 1.37 | absent tool reported and never written to |
| 11 | test_11_blocked_target | PASS | 0.46 | blocked path produced an actionable error instead of a crash |
| 12 | test_12_incompatible_plugin | PASS | 0.66 | cross-tool plugin distribution refused with explanation |
| 13 | test_13_batch_sync | PASS | 0.76 | three tools synced and verified in one command |
| 14 | test_14_checksum_failure | PASS | 0.76 | missing and modified files detected by checksum verification |
| 15 | test_15_interrupted_and_repeat | PASS | 1.66 | repeat run is idempotent; journal resumes; dry runs leave no journal |
| 16 | test_16_unsafe_skill | PASS | 0.54 | high-risk script blocked until --allow-risk |
| 17 | test_17_secret_handling | PASS | 0.75 | skill credential refused; MCP credential replaced with an env placeholder |
| 18 | test_18_invalid_skill | PASS | 0.48 | invalid SKILL.md rejected unless --force is explicit |
| 19 | test_19_git_mirror_rewrite | PASS | 0.33 | third-party git mirror refused before any clone |
| 20 | test_20_cli_doctor | PASS | 1.7 | doctor reports actionable warnings, init fixes them, machine is healthy |
| 21 | test_21_cli_status | PASS | 1.14 | status summarises each target and --strict turns drift into a failure |
| 22 | test_22_cli_aliases | PASS | 0.79 | aliases dispatch correctly, unknown commands exit 2 |
| 23 | test_23_direct_library_edit | PASS | 1.34 | out-of-band library edits refresh the hash; later both-side edits conflict as state C |
| 24 | test_24_compare_missing_operand | PASS | 0.92 | compare reports changed files, and unknown operands fail cleanly instead of crashing |
| 25 | test_25_cli_adopt_and_distribute | PASS | 0.77 | aem adopt pulls from a tool; aem distribute pushes to a tool |
| 26 | test_26_cli_report | PASS | 2.07 | report renders resources, targets, drift and tool status into one HTML file |
