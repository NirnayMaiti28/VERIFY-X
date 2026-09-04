#!/bin/bash
# VERIFY-X 2.0 — Text Model Training Script
set -e

echo "═══════════════════════════════════════════"
echo "  VERIFY-X 2.0 — Text Model Training"
echo "═══════════════════════════════════════════"

CONFIG="${1:-ml/configs/text_qlora.yaml}"

echo "Config: $CONFIG"
echo ""

python ml/training/train_text.py --config "$CONFIG"
