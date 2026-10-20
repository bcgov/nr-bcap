#!/usr/bin/env bash
set -euo pipefail

export PYTHONUNBUFFERED=1

exec pytest tests/search_components/cross_model_advanced_search/snapshot/test_snapshot.py \
    -v -s --tb=short -W ignore \
    -k "${SNAPSHOT_FILTER:-not test_update}"
