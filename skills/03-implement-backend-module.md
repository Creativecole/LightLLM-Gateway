# Skill: Implement Backend Module

Use this skill when implementing mock, Ollama, or future backend adapters.

## Goal

Create backend code that is isolated, testable, and compatible with the gateway routing layer.

## Steps

1. Read the backend requirements in `PROJECT_SPEC.md`.
2. Identify the backend interface expected by the router.
3. Keep backend request and response translation inside the backend module.
4. Use `httpx` for HTTP backends.
5. Configure timeouts explicitly.
6. For tests, mock HTTP calls instead of requiring real backend services.
7. Return internal or OpenAI-compatible objects consistently with existing code.

## Mock Backend Rules

- Keep output deterministic.
- Avoid sleeps, randomness, and network calls.
- Make streaming chunks predictable.

## Ollama Backend Rules

- Make base URL configurable.
- Support `stream=false` first.
- Add `stream=true` only in the planned streaming phase.
- Translate errors into clear gateway errors.

## Verification

Run:

```bash
scripts/check.sh
```
