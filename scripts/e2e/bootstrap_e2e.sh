#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

REQ_FILE="tests/e2e/requirements.txt"

if [ ! -f "$REQ_FILE" ]; then
    echo "ERROR: $REQ_FILE not found" >&2
    exit 1
fi

echo "=== BOOTSTRAP E2E VENV ==="
echo "ROOT_DIR=$ROOT_DIR"
echo "REQ_FILE=$REQ_FILE"

python3 -m venv .venv --clear
source .venv/bin/activate

echo "PYTHON=$(which python)"
echo "PYTHON_VERSION=$(python --version)"
echo "EXECUTABLE=$(python -c 'import sys; print(sys.executable)')"

python -m pip install --upgrade pip --quiet
python -m pip install --requirement "$REQ_FILE"
python -m pip check
python -m playwright install chromium firefox

echo ""
echo "=== VERIFY IMPORTS ==="
python - <<'PY'
import sys
import pytest
import playwright
import requests

print("PYTHON_EXECUTABLE=" + sys.executable)
print("PYTEST_VERSION=" + pytest.__version__)
print("REQUESTS_VERSION=" + requests.__version__)
print("IMPORT_CHECK=PASS")
PY

echo ""
echo "=== PLAYWRIGHT VERSION ==="
python -m playwright --version

echo ""
echo "=== BOOTSTRAP COMPLETE ==="
