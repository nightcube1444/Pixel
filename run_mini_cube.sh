#!/bin/bash

cd "$(dirname "$0")"

source venv/bin/activate

python3 run_pipeline.py

echo ""
echo "=================================="
echo "MINI CUBE COMPLETE"
echo "=================================="

cat data/daily_report.txt