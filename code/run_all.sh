#!/usr/bin/env bash
# Regenerates every number, table and figure used in the report.
#
#   bash run_all.sh           all data; writes ../results/ and ../report.pdf
#   bash run_all.sh --quick   first 100,000 vectors, smaller Part 4; writes ../results_quick/
#
# Expects the data files in ../data/ (see README.md).
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(cd .. && pwd)"

if [ "${1:-}" = "--quick" ]; then
  export A3_RESULTS_DIR="$ROOT/results_quick"
  NTRAIN=(--n-train 100000)
  QUICK=(--quick)
  SCALING=(--sizes 100000)
  PART4=(--n 50000)
else
  NTRAIN=()
  QUICK=()
  SCALING=()
  PART4=()
fi

python -m pytest -q tests
python -u exact.py "${NTRAIN[@]}"
python -u bench_ann.py "${NTRAIN[@]}" "${QUICK[@]}"
python -u scaling.py "${SCALING[@]}"
python -u part4.py "${PART4[@]}"
python -u analyze.py

if [ "${1:-}" != "--quick" ] && command -v pdflatex >/dev/null 2>&1; then
  (cd "$ROOT/report" && pdflatex -interaction=nonstopmode report.tex >/dev/null \
    && pdflatex -interaction=nonstopmode report.tex >/dev/null)
  cp "$ROOT/report/report.pdf" "$ROOT/report.pdf"
fi
echo "done"
