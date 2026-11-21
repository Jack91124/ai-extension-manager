## What changed

<!-- One paragraph for a user-visible change. -->

## Why

<!-- The problem this solves. Link the issue if there is one. -->

## How it was verified

- [ ] `python evals/run_tests.py` passes (paste the RESULT line)
- [ ] New or changed behaviour has a scenario test
- [ ] `python demo/run_demo.py` still ends with the expected conflict exit code
- [ ] Docs / CHANGELOG updated

Python and OS tested:

```
```

## Safety checklist

- [ ] No new runtime dependency
- [ ] A destructive path still defaults to refusing, and supports `--dry-run`
- [ ] No tool path or interface was invented; verification level updated if needed
- [ ] No secret, real credential or personal path is included in tests or docs
