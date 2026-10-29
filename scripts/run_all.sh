#!/usr/bin/env bash
# One-shot: generate → validate → reproducibility check
set -euo pipefail
cd "$(dirname "$0")/.."

MODE="${1:-starter}"
SEED="${2:-20261022}"

echo ">>> Generating ($MODE, seed=$SEED)"
python -m src.generate --mode "$MODE" --seed "$SEED"

echo ">>> Validating"
python -m src.validate

echo ">>> Reproducibility check"
python -m src.reproducibility_check --mode "$MODE" --seed "$SEED"

echo ">>> Done. Artefacts in data/"
