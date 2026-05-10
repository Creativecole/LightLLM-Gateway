# Skill: Understand Requirement

Use this skill before implementing any task.

## Goal

Convert a user request or task list item into a clear, bounded engineering objective.

## Steps

1. Read the user request fully.
2. Read `AGENTS.md`, `PROJECT_SPEC.md`, and `TASKS.md`.
3. Identify the active phase.
4. Identify the expected input, output, and user-visible behavior.
5. List files likely to change.
6. Check whether the request asks for code, docs, tests, or review.
7. Call out anything that conflicts with the project spec.

## Output

Before editing, be able to state:

- The exact task.
- The phase it belongs to.
- The acceptance criteria.
- The likely verification command.

## Rules

- Do not expand scope without a reason.
- Do not implement future phases early.
- If requirements are ambiguous, choose the smallest behavior consistent with `PROJECT_SPEC.md`.
