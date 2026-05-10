# Skill: Design Architecture

Use this skill when adding or changing structure between modules.

## Goal

Design changes that preserve a clean gateway architecture and make later phases easier.

## Steps

1. Locate existing modules and naming patterns.
2. Keep API handlers thin.
3. Put routing logic outside FastAPI handlers.
4. Put backend-specific HTTP translation inside backend adapters.
5. Keep schemas explicit and Pydantic-based.
6. Keep cross-cutting concerns isolated:
   - Auth.
   - Rate limit.
   - Cache.
   - Metrics.
   - Request logs.
7. Prefer plain interfaces or protocols before complex inheritance.

## Architecture Checks

- Can this module be tested without a live server?
- Can this behavior be mocked deterministically?
- Does this preserve the OpenAI-compatible API contract?
- Does this avoid leaking Ollama-specific details into the API layer?

## Rules

- Add abstractions only when they clarify real boundaries.
- Avoid global mutable state unless the MVP explicitly calls for in-memory behavior.
- Keep configuration centralized.
