#!/usr/bin/env bash
set -euo pipefail

export PYTHONUNBUFFERED=1

exec pytest tests/search_components/cross_model_advanced_search/integration/test_search_comparison.py \
    -v -s --tb=short -W ignore \
    -k "${INTEGRATION_FILTER:-}"
