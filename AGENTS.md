# AGENTS.md

This file defines the operating rules for AI Coding Agents working on LightLLM-Gateway.

## Project Goal

LightLLM-Gateway is an AI infrastructure and AI coding project that builds a lightweight, observable, OpenAI-compatible gateway for local and private LLM backends.

The project should eventually provide:

- An OpenAI-compatible API surface for chat completions.
- A model router that can dispatch requests to multiple backends.
- An Ollama backend implementation.
- Streaming responses through Server-Sent Events.
- API key authentication and simple rate limiting.
- Prompt cache support for repeated requests.
- Metrics, request logs, and benchmark tooling.
- A small dashboard for inspecting runtime behavior.

The current phase is Harness Engineering: create the constraints, docs, task structure, skills, and verification script that future AI Coding Agents must follow.

## Engineering Rules

- Keep changes small, explicit, and easy to review.
- Prefer simple, readable Python over clever abstractions.
- Use FastAPI, Pydantic, httpx, pytest, pytest-asyncio, and ruff as the default stack.
- Preserve OpenAI-compatible request and response shapes where the project spec requires them.
- Separate concerns clearly:
  - API schema and route handlers.
  - Routing logic.
  - Backend adapters.
  - Streaming utilities.
  - Auth and rate limit middleware.
  - Cache, metrics, logs, and benchmark code.
- Write tests for every behavior change.
- Keep mock backends deterministic.
- Avoid adding network calls to tests unless explicitly required and guarded.
- Document public behavior when it changes.
- Every change must pass `scripts/check.sh` before being considered complete.

## Development Workflow

Follow this loop for every task:

1. Read `PROJECT_SPEC.md`, `TASKS.md`, and the relevant files before editing.
2. Identify the current phase and the exact task being implemented.
3. Use the relevant skill document from `skills/`.
4. Make the smallest coherent code or documentation change.
5. Add or update tests if behavior changed.
6. Run:

   ```bash
   scripts/check.sh
   ```

7. Fix any lint, test, or import failures.
8. Update `TASKS.md` only when a task is actually completed.
9. Summarize:
   - What changed.
   - Which files changed.
   - What verification was run.
   - Any known limitations.

## Required Checks

Every modification must run `scripts/check.sh`.

The check script must include:

- `ruff check .`
- `pytest`
- An application import check.

If checks cannot run because dependencies are missing, install dependencies first or clearly report the blocker.

## Forbidden Actions

- Do not implement full business functionality before the planned phase.
- Do not bypass `scripts/check.sh`.
- Do not silently change public API shapes.
- Do not introduce unrelated refactors while completing a focused task.
- Do not add heavyweight dependencies without justification.
- Do not commit secrets, tokens, API keys, local environment files, or private endpoint URLs.
- Do not make tests depend on a real Ollama server by default.
- Do not remove or weaken tests to make checks pass.
- Do not hide failures in scripts with broad `|| true` behavior.
- Do not overwrite user changes without reading them first.

## Agent Handoff Rules

When handing work to the next Agent:

- Leave the repository in a checkable state.
- Keep task status accurate in `TASKS.md`.
- Prefer explicit TODOs only when they map to a listed task.
- Explain any incomplete work and why it is incomplete.
- Never assume the next Agent knows unstated context.
