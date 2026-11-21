# AI Extension Manager - Scenario Test Report

- generated: 2026-11-21T16:19:50Z
- result: **22/22 passed**
- duration: 40.37s

| # | scenario | result | seconds | evidence |
|---|---|---|---|---|
| 1 | test_01_classify_github_skill | PASS | 0.73 | skill detected in repo; github URL classified |
| 2 | test_02_classify_github_plugin | PASS | 0.4 | dsh plugin manifest recognised |
| 3 | test_03_import_skill | PASS | 0.47 | imported with complete metadata (2 files) |
| 4 | test_04_import_from_claude | PASS | 0.76 | claude skill imported and target recorded |
| 5 | test_05_distribute_to_codex | PASS | 1.55 | distributed and verified on codex |
| 6 | test_06_reverse_import_modified | PASS | 1.99 | reverse import updated the library and stayed in sync |
| 7 | test_07_compare_versions | PASS | 1.47 | two versions compared with a unified diff |
| 8 | test_08_conflict_detection | PASS | 3.77 | state C detected, dry-run exits 2, explicit resolutions work |
| 9 | test_09_restore_old_version | PASS | 1.52 | old version restored and hash verified |
| 10 | test_10_missing_tool | PASS | 2.99 | absent tool reported and never written to |
| 11 | test_11_blocked_target | PASS | 1.19 | blocked path produced an actionable error instead of a crash |
| 12 | test_12_incompatible_plugin | PASS | 1.85 | cross-tool plugin distribution refused with explanation |
| 13 | test_13_batch_sync | PASS | 1.67 | three tools synced and verified in one command |
| 14 | test_14_checksum_failure | PASS | 1.6 | missing and modified files detected by checksum verification |
| 15 | test_15_interrupted_and_repeat | PASS | 3.75 | repeat run is idempotent; journal resumes; dry runs leave no journal |
| 16 | test_16_unsafe_skill | PASS | 1.4 | high-risk script blocked until --allow-risk |
| 17 | test_17_secret_handling | PASS | 2.01 | skill credential refused; MCP credential replaced with an env placeholder |
| 18 | test_18_invalid_skill | PASS | 1.22 | invalid SKILL.md rejected unless --force is explicit |
| 19 | test_19_git_mirror_rewrite | PASS | 0.8 | third-party git mirror refused before any clone |
| 20 | test_20_cli_doctor | PASS | 4.07 | doctor reports actionable warnings, init fixes them, machine is healthy |
| 21 | test_21_cli_status | PASS | 2.43 | status summarises each target and --strict turns drift into a failure |
| 22 | test_22_cli_aliases | PASS | 1.95 | aliases dispatch correctly, unknown commands exit 2 |
