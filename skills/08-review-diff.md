# Skill: Review Diff

Use this skill before final handoff or when asked to review changes.

## Goal

Review the diff for correctness, scope, and maintainability.

## Steps

1. Check `git status --short`.
2. Review changed files.
3. Look for unrelated edits.
4. Confirm tests cover changed behavior.
5. Confirm docs were updated if public behavior changed.
6. Run `scripts/check.sh`.

## Review Checklist

- Does the change match the active phase in `TASKS.md`?
- Does it preserve the project rules in `AGENTS.md`?
- Are public API shapes compatible with `PROJECT_SPEC.md`?
- Are external services mocked in tests?
- Are errors clear and testable?
- Did verification pass?

## Handoff Summary

Report:

- Files changed.
- Main behavior added or changed.
- Verification result.
- Any known risks or follow-up tasks.
