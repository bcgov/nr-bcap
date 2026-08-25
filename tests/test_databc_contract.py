"""
Contract test: vw_*.sql ↔ mv_*_flat.sql

Verifies that every column referenced by the static DataBC API views (vw_*.sql)
exists in the corresponding generated flat materialized views (mv_*_flat.sql).

No database connection required — pure file parsing.

Run with:
    python manage.py test tests.test_databc_contract

Also run automatically after regenerating views:
    python manage.py generate_databc_views && python manage.py test tests.test_databc_contract
"""

import os
import re
import unittest

from bcap.databc_config import GRAPHS

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_BCAP_DIR = os.path.join(os.path.dirname(__file__), "..", "bcap")
_MV_BASE = os.path.join(_BCAP_DIR, "migrations", "sql", "materialized_views")
_VW_DIR = os.path.join(_BCAP_DIR, "migrations", "sql", "views", "databc")


# ---------------------------------------------------------------------------
# Helper: build flat-table-name → mv SQL file mapping from databc_config
# ---------------------------------------------------------------------------


def _build_flat_table_map():
    """
    Returns a dict mapping "{schema}.{view_name}_flat" (or "{schema}.resource_flat")
    to the absolute path of the corresponding mv_*_flat.sql file.

    Uses databc_config.py's view_names to resolve stable wrapper names back to
    grain aliases (which determine the MV file name).
    """
    mapping = {}
    for slug, cfg in GRAPHS.items():
        schema = cfg["arches_slug"].replace("-", "_")
        schema_dir = os.path.join(_MV_BASE, schema)
        view_names = cfg.get("view_names", {})

        # resource_flat → mv_resource_flat.sql
        mapping[f"{schema}.resource_flat"] = os.path.join(
            schema_dir, "mv_resource_flat.sql"
        )

        # grain flats: stable view_name_flat → mv_{grain_alias}_flat.sql
        for grain in cfg["flat_grains"]:
            stable_name = view_names.get(grain, grain)
            mapping[f"{schema}.{stable_name}_flat"] = os.path.join(
                schema_dir, f"mv_{grain}_flat.sql"
            )

    return mapping


# ---------------------------------------------------------------------------
# Helper: parse defined columns from a generated MV SQL file
# ---------------------------------------------------------------------------


def _defined_columns(mv_sql_path):
    """
    Parse a mv_*_flat.sql file and return the set of column names it defines.

    Columns are defined as:
      - expr AS col_name  (aliased)
      - r.col_name,       (unaliased reference, e.g. geometry cols like r.site_boundary_geom)
    """
    if not os.path.exists(mv_sql_path):
        return None  # file missing — caller reports the error

    with open(mv_sql_path) as fh:
        sql = fh.read()

    cols = set()

    # Aliased: "... AS col_name"
    for m in re.finditer(r"\bAS\s+([a-z][a-z0-9_]*)\b", sql, re.IGNORECASE):
        cols.add(m.group(1).lower())

    # Unaliased direct references: "    r.col_name," (geometry columns passed through)
    for m in re.finditer(r"^\s+r\.([a-z][a-z0-9_]*),?\s*$", sql, re.MULTILINE):
        cols.add(m.group(1).lower())

    # Always present but might not appear with AS in some generators
    cols.add("resourceinstanceid")

    return cols


# ---------------------------------------------------------------------------
# Helper: parse columns referenced from a source table in a vw_*.sql file
# ---------------------------------------------------------------------------

_KEYWORDS = frozenset(
    {
        "select",
        "from",
        "where",
        "and",
        "or",
        "as",
        "left",
        "null",
        "case",
        "when",
        "then",
        "else",
        "end",
        "join",
        "on",
        "true",
        "false",
        "not",
        "is",
        "distinct",
        "create",
        "or",
        "replace",
        "view",
        "comment",
        "schema",
        "if",
        "exists",
        "do",
        "declare",
        "begin",
        "for",
        "loop",
        "end",
        "raise",
        "execute",
        "format",
        "into",
        "language",
        "plpgsql",
        "commit",
        "return",
        "databc",
    }
)


def _referenced_columns(vw_sql_path, source_table):
    """
    Parse vw_sql_path and return the set of source column names referenced
    in any SELECT block whose FROM clause is exactly `source_table`.

    Handles:
      col_name,
      LEFT(col_name, 4000) AS alias,
      col_name::type AS alias,
      col_name  -- comment
    """
    if not os.path.exists(vw_sql_path):
        return None

    with open(vw_sql_path) as fh:
        sql = fh.read()

    sql = sql.replace("\r\n", "\n")

    # Split into individual CREATE OR REPLACE VIEW blocks so we don't
    # accidentally merge columns from multiple views.
    view_blocks = re.split(
        r"(?=CREATE\s+OR\s+REPLACE\s+VIEW\b)", sql, flags=re.IGNORECASE
    )

    cols = set()
    for block in view_blocks:
        # Within this block, find "SELECT ... FROM source_table"
        m = re.search(
            r"\bSELECT\s(.*?)\bFROM\s+" + re.escape(source_table) + r"\b",
            block,
            re.DOTALL | re.IGNORECASE,
        )
        if m:
            cols.update(_parse_select_cols(m.group(1)))

    return cols


def _parse_select_cols(select_body):
    """Extract source column names from a SELECT clause body."""
    cols = set()

    # LEFT(col, N) — the col inside LEFT()
    for m in re.finditer(r"\bLEFT\s*\(\s*([a-z_][a-z0-9_]*)\s*,", select_body):
        cols.add(m.group(1))

    # col::type (type cast, possibly followed by AS alias)
    for m in re.finditer(r"\b([a-z_][a-z0-9_]*)::\w+", select_body):
        name = m.group(1)
        if name.lower() not in _KEYWORDS:
            cols.add(name)

    # Bare identifiers on their own line (geometry cols, index cols, boolean cols, date cols)
    # Pattern: leading whitespace + identifier + optional trailing comma/comment
    for m in re.finditer(
        r"^\s+([a-z_][a-z0-9_]*)\s*(?:,\s*)?(?:--[^\n]*)?\s*$",
        select_body,
        re.MULTILINE,
    ):
        name = m.group(1).lower()
        if name not in _KEYWORDS:
            cols.add(name)

    return cols


# ---------------------------------------------------------------------------
# Discover vw_*.sql files and extract their source table references
# ---------------------------------------------------------------------------


def _discover_vw_sources():
    """
    Scan all vw_*.sql files and return:
        [(vw_path, source_table)]
    where source_table is of the form "schema.table_name".
    """
    results = []
    if not os.path.isdir(_VW_DIR):
        return results

    for fname in sorted(os.listdir(_VW_DIR)):
        if not (fname.startswith("vw_") and fname.endswith(".sql")):
            continue
        vw_path = os.path.join(_VW_DIR, fname)
        with open(vw_path) as fh:
            sql = fh.read()

        # Find all "FROM schema.table" references (not subqueries — just top-level FROMs)
        for m in re.finditer(
            r"\bFROM\s+([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)\b",
            sql,
            re.IGNORECASE,
        ):
            schema = m.group(1).lower()
            table = m.group(2).lower()
            if schema == "databc":
                continue  # skip self-references
            source_table = f"{schema}.{table}"
            results.append((vw_path, source_table))

    return results


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class DataBCContractTest(unittest.TestCase):
    """
    Asserts that every column referenced in a vw_*.sql file exists in the
    corresponding mv_*_flat.sql materialized view.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.flat_table_map = _build_flat_table_map()
        cls.vw_sources = _discover_vw_sources()

    def test_all_vw_columns_exist_in_mv(self):
        """Every column referenced by vw_*.sql must exist in the backing mv_*_flat.sql."""
        failures = []

        # Deduplicate (vw_path, source_table) pairs
        seen = set()
        for vw_path, source_table in self.vw_sources:
            key = (vw_path, source_table)
            if key in seen:
                continue
            seen.add(key)

            vw_name = os.path.basename(vw_path)

            mv_path = self.flat_table_map.get(source_table)
            if mv_path is None:
                # This source table is not tracked in databc_config — skip silently.
                # (Could be a schema not in our config, e.g., a cross-schema join.)
                continue

            if not os.path.exists(mv_path):
                failures.append(
                    f"{vw_name} references {source_table}\n"
                    f"  → Expected MV file not found: {mv_path}\n"
                    f"  → Run: python manage.py generate_databc_views"
                )
                continue

            referenced = _referenced_columns(vw_path, source_table)
            defined = _defined_columns(mv_path)

            if not referenced:
                # No columns parsed — the regex might not have matched;
                # emit a warning rather than silently passing.
                failures.append(
                    f"{vw_name}: could not parse any column references "
                    f"for source table {source_table}. "
                    f"Check the SQL format or update _referenced_columns()."
                )
                continue

            missing = referenced - defined

            if missing:
                mv_name = os.path.basename(mv_path)
                failures.append(
                    f"{vw_name} references {source_table} but these columns "
                    f"are missing from {mv_name}:\n"
                    + "".join(f"    - {c}\n" for c in sorted(missing))
                    + f"  Regenerate with: python manage.py generate_databc_views"
                )

        if failures:
            self.fail(
                "DataBC contract violations detected "
                f"({len(failures)} issue(s)):\n\n" + "\n".join(failures)
            )

    def test_mv_files_exist_for_all_configured_graphs(self):
        """mv_resource_flat.sql must exist for every graph in databc_config.py."""
        missing = []
        for slug, cfg in GRAPHS.items():
            schema = cfg["arches_slug"].replace("-", "_")
            schema_dir = os.path.join(_MV_BASE, schema)
            flat_mv = os.path.join(schema_dir, "mv_resource_flat.sql")
            if not os.path.exists(flat_mv):
                missing.append(f"  {slug} ({schema}): {flat_mv}")
        if missing:
            self.fail(
                "Missing mv_resource_flat.sql for configured graph(s):\n"
                + "\n".join(missing)
                + "\nRun: python manage.py generate_databc_views"
            )

    def test_grain_mv_files_exist(self):
        """mv_{grain}_flat.sql must exist for every configured flat_grain."""
        missing = []
        for slug, cfg in GRAPHS.items():
            schema = cfg["arches_slug"].replace("-", "_")
            schema_dir = os.path.join(_MV_BASE, schema)
            for grain in cfg["flat_grains"]:
                grain_mv = os.path.join(schema_dir, f"mv_{grain}_flat.sql")
                if not os.path.exists(grain_mv):
                    missing.append(f"  {slug}.{grain}: {grain_mv}")
        if missing:
            self.fail(
                "Missing grain flat MV file(s):\n"
                + "\n".join(missing)
                + "\nRun: python manage.py generate_databc_views"
            )


if __name__ == "__main__":
    unittest.main()
