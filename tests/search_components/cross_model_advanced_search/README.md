# Cross-Model Advanced Search Tests

The integration test compares search result counts between the existing
Advanced Search and the Cross-Model Advanced Search. For every searchable
card and qualifier combination, the suite asserts that both search
implementations return the same count.

## Prerequisites

### Playwright (inside of the `bcap7-6` container)

```bash
python3.11 -m pip install playwright pytest-playwright
playwright install --with-deps chromium
```

### Environment Variables

The test suite reads credentials from the project root `.env` file
automatically. You should add the following if they are not already present:

```
BCAP_IDIR_USER=your_idir
BCAP_IDIR_PASSWORD=your_password
```

Docker is detected automatically. The base URL defaults to port 80 inside
a container and port 82 on the host. Both can be overridden with
`BCAP_BASE_URL` if needed.

### Just (optional)

[Just](https://github.com/casey/just) is a command runner similar to `make`
but without the build-system baggage. It is only needed if you want to use the
shorthand recipes in the `justfile` (e.g. `just integration`). Everything can
be run without it by calling `docker exec` or `pytest` directly.

Install: https://github.com/casey/just#installation

## Running Tests

### Unit and Mock Tests

These run directly inside the container with no browser required:

```bash
# With Just (from the host)
just unit
just mock

# Or inside the container
python3.11 -m pytest tests/search_components/cross_model_advanced_search/unit/ -v
python3.11 -m pytest tests/search_components/cross_model_advanced_search/mock/ -v
```

### Scenario Tests

Scenario tests verify the full `Intersector` and `Translator` pipeline against
synthetic, deterministic data topologies. Each scenario seeds a known set of
graphs, resources, and relationships, then asserts the exact set of resource IDs
the pipeline must produce. No database, Elasticsearch, or browser required.

```bash
# With Just (from the host)
just scenario

# Or inside the container
python3.11 -m pytest tests/search_components/cross_model_advanced_search/scenario/ -v
```

To add a new scenario, append a `Scenario(...)` to `_build_scenarios()` in
`scenario/test_scenario.py`. Define the graph topology, ES matches,
relationships, target graph, operation, and expected output.

### Snapshot Tests

Snapshot tests run real cross-model queries against the database and compare
result counts to stored baselines:

```bash
# With Just (from the host)
just snapshot

# Update baselines after intentional changes
just snapshot-update
```

### Integration Tests (headless)

From inside the container, with the environment variables above exported:

```bash
pytest tests/search_components/cross_model_advanced_search/integration/test_search_comparison.py -v -s
```

To run a specific card, pass `-k` with a filter:

```bash
pytest tests/search_components/cross_model_advanced_search/integration/test_search_comparison.py -v -s -k 2_Identification
```

### Integration Tests (browser via CDP)

This mode connects Playwright to a [Google Chrome](https://www.google.com/chrome/)
instance on your host machine so you can watch the tests run in your browser.

```bash
just integration
```

This launches Chrome with remote debugging, starts the CDP proxy, and runs the
tests.

If you are not using Just, you will need to manually launch Chrome with
`--remote-debugging-port=9222`, start the CDP proxy (`python integration/proxy.py`),
then run:

```bash
docker exec -it \
  -e PYTHONUNBUFFERED=1 \
  -e INTEGRATION_FILTER=2_Identification \
  -e INTEGRATION_CLEAR_CACHE=1 \
  -e BCAP_CDP=http://host.docker.internal:9223 \
  -e BCAP_BASE_URL=http://localhost:82/bcap \
  bcap7-6 bash tests/search_components/cross_model_advanced_search/integration/run_integration.sh
```

## Clearing the Cache

The suite caches Advanced Search counts and the node inventory to avoid
redundant browser interactions on subsequent runs. To clear the cache:

```bash
# From the host
just integration-clear-cache

# Or inside the container
rm -rf tests/search_components/cross_model_advanced_search/integration/.cache
```

Alternatively, pass `clear=1` (the default) when running via Just, or export
`INTEGRATION_CLEAR_CACHE=1` when running directly.

## Just Recipes

| Recipe                      | Description                                   |
| --------------------------- | --------------------------------------------- |
| `just unit`                 | Run unit tests                                |
| `just mock`                 | Run mock tests                                |
| `just scenario`             | Run scenario tests                            |
| `just snapshot`             | Run snapshot tests                            |
| `just snapshot-update`      | Update snapshot baselines                     |
| `just integration`          | Launch Chrome + proxy + run integration tests |
| `just integration-headless` | Run integration tests headless inside Docker  |
| `just integration-baseline` | Run the unfiltered totals comparison test     |
| `just integration-clear-cache` | Clear all cached data                      |
| `just chrome`               | Launch Chrome with remote debugging           |
| `just proxy`                | Start the CDP proxy                           |
