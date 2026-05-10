# Skill: Update Docs

Use this skill when public behavior, architecture, or workflow changes.

## Goal

Keep documentation accurate enough for the next Agent to continue safely.

## Docs To Consider

- `README.md`
- `PROJECT_SPEC.md`
- `TASKS.md`
- `AGENTS.md`
- Relevant files in `skills/`

## Steps

1. Identify whether the change affects setup, usage, API behavior, architecture, or task status.
2. Update the smallest relevant documentation file.
3. Mark tasks complete only after code and tests are complete.
4. Keep docs consistent with the current implementation.
5. Run `scripts/check.sh`.

## Rules

- Do not mark future phases complete early.
- Do not document behavior that is not implemented.
- Prefer concrete commands and endpoint names over vague prose.
