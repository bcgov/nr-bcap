#!/usr/bin/env bash
#
# Regenerate the API contract end to end:
#   1. OpenAPI spec — DRF views (bcap.documented_api_urls) → schema.yml
#   2. Zod schemas  — schema.yml → bcap/src/bcap/client/zod/ (orval)
#                       one .zod.ts file per spec tag; runtime validation + types
#                       (via z.infer). The fetch layer lives in components/pages/api.ts.
#
#   ./scripts/generate_api_contract.sh
#
# Run this after changing any documented serializer, view, or route -- or an
# Arches resource model, since the tile schemas are derived from the graph.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "1/2 Generating OpenAPI spec (DRF views -> schema.yml)..."
python3 manage.py spectacular --urlconf bcap.documented_api_urls --file schema.yml

echo "2/2 Generating API client (schema.yml -> bcap/src/bcap/client/)..."
npm run openapi:gen

echo "Done. schema.yml and bcap/src/bcap/client/ are up to date."
