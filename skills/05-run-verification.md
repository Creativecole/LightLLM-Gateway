# Skill: Run Verification

Use this skill after every modification.

## Goal

Verify that the repository is lint-clean, tests pass, and the app remains importable.

## Required Command

Run:

```bash
scripts/check.sh
```

## Expected Checks

The script must run:

- `ruff check .`
- `pytest`
- App import check.

## If Verification Fails

1. Read the first actionable failure.
2. Fix the root cause.
3. Re-run `scripts/check.sh`.
4. Repeat until checks pass or a real external blocker is identified.

## Reporting

When done, report:

- The command run.
- Whether it passed.
- Any remaining blocker.
