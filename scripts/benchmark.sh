#!/bin/bash
# VERIFY-X 2.0 — Adversarial Benchmark Script
set -e

echo "═══════════════════════════════════════════"
echo "  VERIFY-X 2.0 — Adversarial Benchmark"
echo "═══════════════════════════════════════════"

python -m ml.evaluation.benchmark "$@"
