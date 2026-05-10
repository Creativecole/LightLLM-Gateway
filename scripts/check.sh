#!/usr/bin/env bash
set -euo pipefail

if [ -d ".venv/bin" ]; then
  PATH="$PWD/.venv/bin:$PATH"
fi

echo "==> ruff lint"
ruff check .

echo "==> pytest"
pytest

echo "==> app import check"
python -c "from gateway.app import create_app; app = create_app(); assert app is not None"

echo "==> all checks passed"
