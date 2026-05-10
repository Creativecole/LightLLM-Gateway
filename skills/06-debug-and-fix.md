# Skill: Debug And Fix

Use this skill when checks fail or behavior is incorrect.

## Goal

Find the smallest correct fix for a failure.

## Steps

1. Reproduce the failure.
2. Read the traceback or failing assertion.
3. Identify whether the failure is from lint, tests, import, runtime behavior, or environment setup.
4. Inspect the smallest relevant code region.
5. Make a focused fix.
6. Add a regression test if one is missing.
7. Run `scripts/check.sh` again.

## Debugging Rules

- Fix root causes, not symptoms.
- Do not delete tests to pass verification.
- Do not add broad `except Exception` blocks unless the behavior requires them.
- Do not add `# noqa` unless there is a clear reason.
- Keep unrelated files untouched.

## Common Failure Types

- Schema mismatch: update Pydantic models or tests to match the spec.
- Async issue: ensure async functions are awaited and tests use the right pytest mode.
- Import issue: check module paths and package `__init__.py` files.
- Streaming issue: inspect exact SSE output format.
