#!/bin/bash
# VERIFY-X 2.0 — Evaluation Script
set -e

echo "═══════════════════════════════════════════"
echo "  VERIFY-X 2.0 — Evaluation"
echo "═══════════════════════════════════════════"

python -m ml.evaluation.metrics "$@"
