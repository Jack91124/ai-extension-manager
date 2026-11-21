# Contributing

Thanks for helping. This project is intentionally small and dependency-free: Python 3.9+, standard
library only.

## Development setup

```bash
git clone https://github.com/OWNER/ai-extension-manager.git
cd ai-extension-manager
python -m pip install -e .
python -m pip install -e . --no-build-isolation   # e.g. Windows, when build isolation fails
aem doctor
python evals/run_tests.py
```

The scenario suite uses disposable fake homes under `evals/_tmp/` and never touches a real tool
configuration. Run one case with `python evals/run_tests.py --only test_08` and keep the sandbox
with `--keep`.

## Ground rules

1. **Never invent a tool path or an interface.** New adapter behaviour must be backed by official
   docs, a verified installation, or an explicit `verification` marker (`local` / `official+local` /
   `partial` / `none`) in `scripts/aem_core.py`.
2. **No new runtime dependencies.** If a feature cannot be done with the standard library, open an
   issue first.
3. **Default is never destructive.** New operations must support `--dry-run`, write conflicts instead
   of overwriting, and back up before replacing.
4. **Add a scenario test.** Every bug fix and feature needs a case in `evals/run_tests.py` asserting
   exit codes and files on disk, not just stdout text.
5. **Keep JSON contracts stable.** Add fields; do not rename or repurpose existing ones without a
   schema bump in `SCHEMA_VERSION`.

## Adding a tool adapter

1. Add an entry to `default_agent_configs()` in `scripts/aem_core.py`: id, CLI names, home env,
   markers, user/workspace skill paths, plugin system, MCP configs, rules paths, docs URL and a
   verification level.
2. Add it to the `AGENTS` ordering and to `references/agent-compatibility.md`.
3. Run `aem scan` and `aem detect --agent <id>` against a real installation and record what you saw.
4. Add a scenario test that misses the tool (no directory) and one that receives a skill.
5. If the tool cannot be installed in CI, say so in the PR and mark the adapter `partial`.

## Pull requests

- Keep commits focused; describe the user-visible change in the PR body.
- Include the output of `python evals/run_tests.py` (all green) and the Python/OS you tested.
- Update `CHANGELOG.md` under "Unreleased".
- By contributing you agree your work is licensed under the MIT license.
