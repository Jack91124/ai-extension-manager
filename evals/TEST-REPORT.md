# AI Extension Manager - Scenario Test Report

- generated: 2026-11-22T02:49:15Z
- result: **22/22 passed**
- duration: 25.69s

| # | scenario | result | seconds | evidence |
|---|---|---|---|---|
| 1 | test_01_classify_github_skill | PASS | 0.56 | skill detected in repo; github URL classified |
| 2 | test_02_classify_github_plugin | PASS | 0.28 | dsh plugin manifest recognised |
| 3 | test_03_import_skill | PASS | 0.33 | imported with complete metadata (2 files) |
| 4 | test_04_import_from_claude | PASS | 0.49 | claude skill imported and target recorded |
| 5 | test_05_distribute_to_codex | PASS | 0.93 | distributed and verified on codex |
| 6 | test_06_reverse_import_modified | PASS | 1.38 | reverse import updated the library and stayed in sync |
| 7 | test_07_compare_versions | PASS | 1.13 | two versions compared with a unified diff |
| 8 | test_08_conflict_detection | PASS | 2.7 | state C detected, dry-run exits 2, explicit resolutions work |
| 9 | test_09_restore_old_version | PASS | 1.15 | old version restored and hash verified |
| 10 | test_10_missing_tool | PASS | 1.95 | absent tool reported and never written to |
| 11 | test_11_blocked_target | PASS | 0.69 | blocked path produced an actionable error instead of a crash |
| 12 | test_12_incompatible_plugin | PASS | 1.03 | cross-tool plugin distribution refused with explanation |
| 13 | test_13_batch_sync | PASS | 1.09 | three tools synced and verified in one command |
| 14 | test_14_checksum_failure | PASS | 1.13 | missing and modified files detected by checksum verification |
| 15 | test_15_interrupted_and_repeat | PASS | 2.32 | repeat run is idempotent; journal resumes; dry runs leave no journal |
| 16 | test_16_unsafe_skill | PASS | 0.7 | high-risk script blocked until --allow-risk |
| 17 | test_17_secret_handling | PASS | 1.03 | skill credential refused; MCP credential replaced with an env placeholder |
| 18 | test_18_invalid_skill | PASS | 0.63 | invalid SKILL.md rejected unless --force is explicit |
| 19 | test_19_git_mirror_rewrite | PASS | 0.4 | third-party git mirror refused before any clone |
| 20 | test_20_cli_doctor | PASS | 2.24 | doctor reports actionable warnings, init fixes them, machine is healthy |
| 21 | test_21_cli_status | PASS | 1.77 | status summarises each target and --strict turns drift into a failure |
| 22 | test_22_cli_aliases | PASS | 1.35 | aliases dispatch correctly, unknown commands exit 2 |
