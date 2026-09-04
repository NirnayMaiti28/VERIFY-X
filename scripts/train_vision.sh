#!/bin/bash
# VERIFY-X 2.0 — Vision Model Training Script (OPTIONAL)
set -e

echo "═══════════════════════════════════════════"
echo "  VERIFY-X 2.0 — Vision Model Training"
echo "  NOTE: This is OPTIONAL."
echo "═══════════════════════════════════════════"

CONFIG="${1:-ml/configs/vision_qlora.yaml}"

echo "Config: $CONFIG"
echo ""

python ml/training/train_vision.py --config "$CONFIG"
