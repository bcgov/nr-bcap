"""
Unit tests for bcap.migrations.databc.generator.SpecGenerator.

SpecGenerator is pure Python (no Django ORM) so SimpleTestCase is sufficient.
"""

import os
import tempfile
import types

from django.test import SimpleTestCase

from bcap.migrations.databc.generator import SpecGenerator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _spec(
    graph_id="aaaa-0000-1111-2222",
    schema="test_schema",
    slug="test",
    flat_grains=None,
    flat_grain_view_names=None,
    ng=None,
):
    """Build a minimal SimpleNamespace spec for SpecGenerator."""
    return types.SimpleNamespace(
        GRAPH_ID=graph_id,
        SCHEMA=schema,
        SLUG=slug,
        FLAT_GRAINS=flat_grains or [],
        FLAT_GRAIN_VIEW_NAMES=flat_grain_view_names or {},
        NG=ng or [],
    )


def _ng(alias, ngid, parent=None, cardinality="1", fields=None):
    """Build a nodegroup tuple."""
    return (alias, ngid, parent, cardinality, fields or [])


def _field(alias, nodeid, datatype="string", datefmt=None):
    """Build a field tuple."""
    return (alias, nodeid, datatype, datefmt)


def _make_gen(spec_kwargs=None, out_dir=None):
    s = _spec(**(spec_kwargs or {}))
    return SpecGenerator(s, out_dir or tempfile.gettempdir())


# ---------------------------------------------------------------------------
# _grain_view_name
# ---------------------------------------------------------------------------


class TestGrainViewName(SimpleTestCase):
    def test_returns_alias_when_no_override(self):
        gen = _make_gen()
        self.assertEqual(gen._grain_view_name("my_grain"), "my_grain")

    def test_returns_override_when_configured(self):
        gen = _make_gen({"flat_grain_view_names": {"old_alias": "stable_name"}})
        self.assertEqual(gen._grain_view_name("old_alias"), "stable_name")

    def test_unrelated_alias_not_overridden(self):
        gen = _make_gen({"flat_grain_view_names": {"other": "something"}})
        self.assertEqual(gen._grain_view_name("my_grain"), "my_grain")


# ---------------------------------------------------------------------------
# get_all_flat_tables
# ---------------------------------------------------------------------------


class TestGetAllFlatTables(SimpleTestCase):
    def test_resource_flat_always_present(self):
        gen = _make_gen()
        self.assertIn("resource_flat", gen.get_all_flat_tables())

    def test_grain_flat_uses_grain_alias_when_no_override(self):
        spec_kw = {
            "flat_grains": ["my_grain"],
            "ng": [_ng("my_grain", "ng-uuid-1")],
        }
        gen = _make_gen(spec_kw)
        self.assertIn("my_grain_flat", gen.get_all_flat_tables())

    def test_grain_flat_uses_stable_name_when_override_set(self):
        spec_kw = {
            "flat_grains": ["old_alias"],
            "flat_grain_view_names": {"old_alias": "stable_name"},
            "ng": [_ng("old_alias", "ng-uuid-1")],
        }
        gen = _make_gen(spec_kw)
        tables = gen.get_all_flat_tables()
        self.assertIn("stable_name_flat", tables)
        self.assertNotIn("old_alias_flat", tables)

    def test_multiple_grains_produce_multiple_keys(self):
        spec_kw = {
            "flat_grains": ["grain_a", "grain_b"],
            "ng": [
                _ng("grain_a", "ng-uuid-1"),
                _ng("grain_b", "ng-uuid-2"),
            ],
        }
        gen = _make_gen(spec_kw)
        tables = gen.get_all_flat_tables()
        self.assertIn("grain_a_flat", tables)
        self.assertIn("grain_b_flat", tables)

    def test_geom_columns_present_in_resource_flat(self):
        """Geometry columns appear in resource_flat when a geom field exists."""
        spec_kw = {
            "ng": [
                _ng(
                    "boundary",
                    "ng-uuid-1",
                    fields=[
                        _field(
                            "geom_field", "node-uuid-1", "geojson-feature-collection"
                        ),
                    ],
                ),
            ],
        }
        gen = _make_gen(spec_kw)
        tables = gen.get_all_flat_tables()
        col_names = [c for c, _ in tables["resource_flat"]]
        self.assertIn("geom_field_geom", col_names)
        self.assertIn("geom_field_polygons", col_names)


# ---------------------------------------------------------------------------
# get_flat_columns
# ---------------------------------------------------------------------------


class TestGetFlatColumns(SimpleTestCase):
    def _string_spec(self):
        return {
            "ng": [
                _ng(
                    "branch",
                    "ng-uuid-1",
                    fields=[
                        _field("title", "node-uuid-1", "string"),
                    ],
                )
            ],
        }

    def test_string_field_produces_text_column(self):
        gen = _make_gen(self._string_spec())
        cols = gen.get_flat_columns(None)
        names = [c for c, _ in cols]
        self.assertIn("title", names)

    def test_date_field_produces_date_type(self):
        spec_kw = {
            "ng": [
                _ng(
                    "branch",
                    "ng-uuid-1",
                    fields=[
                        _field("start_date", "node-uuid-2", "date", "YYYY-MM-DD"),
                    ],
                )
            ],
        }
        gen = _make_gen(spec_kw)
        cols = {c: t for c, t in gen.get_flat_columns(None)}
        self.assertIn("start_date", cols)
        self.assertEqual(cols["start_date"], "date")

    def test_number_field_produces_numeric_type(self):
        spec_kw = {
            "ng": [
                _ng(
                    "branch",
                    "ng-uuid-1",
                    fields=[
                        _field("count", "node-uuid-3", "number"),
                    ],
                )
            ],
        }
        gen = _make_gen(spec_kw)
        cols = {c: t for c, t in gen.get_flat_columns(None)}
        self.assertIn("count", cols)
        self.assertEqual(cols["count"], "numeric")

    def test_boolean_field_produces_boolean_type(self):
        spec_kw = {
            "ng": [
                _ng(
                    "branch",
                    "ng-uuid-1",
                    fields=[
                        _field("is_active", "node-uuid-4", "boolean"),
                    ],
                )
            ],
        }
        gen = _make_gen(spec_kw)
        cols = {c: t for c, t in gen.get_flat_columns(None)}
        self.assertIn("is_active", cols)
        self.assertEqual(cols["is_active"], "boolean")

    def test_reference_field_produces_label_and_ids_pair(self):
        spec_kw = {
            "ng": [
                _ng(
                    "branch",
                    "ng-uuid-1",
                    fields=[
                        _field("status", "node-uuid-5", "reference"),
                    ],
                )
            ],
        }
        gen = _make_gen(spec_kw)
        col_names = [c for c, _ in gen.get_flat_columns(None)]
        self.assertIn("status", col_names)
        self.assertIn("status_ids", col_names)

    def test_resource_instance_produces_name_and_id_pair(self):
        spec_kw = {
            "ng": [
                _ng(
                    "branch",
                    "ng-uuid-1",
                    fields=[
                        _field("permit", "node-uuid-6", "resource-instance"),
                    ],
                )
            ],
        }
        gen = _make_gen(spec_kw)
        col_names = [c for c, _ in gen.get_flat_columns(None)]
        self.assertIn("permit", col_names)
        self.assertIn("permit_id", col_names)

    def test_resource_instance_list_produces_names_and_ids_pair(self):
        spec_kw = {
            "ng": [
                _ng(
                    "branch",
                    "ng-uuid-1",
                    fields=[
                        _field("permits", "node-uuid-7", "resource-instance-list"),
                    ],
                )
            ],
        }
        gen = _make_gen(spec_kw)
        col_names = [c for c, _ in gen.get_flat_columns(None)]
        self.assertIn("permits", col_names)
        self.assertIn("permits_ids", col_names)

    def test_geojson_field_excluded_from_scalar_columns(self):
        """Geometry fields are excluded from the _flat column list (handled separately)."""
        spec_kw = {
            "ng": [
                _ng(
                    "boundary",
                    "ng-uuid-1",
                    fields=[
                        _field("geom", "node-uuid-8", "geojson-feature-collection"),
                        _field("title", "node-uuid-9", "string"),
                    ],
                )
            ],
        }
        gen = _make_gen(spec_kw)
        col_names = [c for c, _ in gen.get_flat_columns(None)]
        self.assertNotIn("geom", col_names)
        self.assertIn("title", col_names)


# ---------------------------------------------------------------------------
# generate() — file output
# ---------------------------------------------------------------------------


class TestGenerate(SimpleTestCase):
    def _run_generate(self, spec_kwargs=None):
        with tempfile.TemporaryDirectory() as out_dir:
            spec = _spec(**(spec_kwargs or {}))
            gen = SpecGenerator(spec, out_dir)
            result = gen.generate()
            schema_dir = os.path.join(out_dir, spec.SCHEMA)
            files = set(os.listdir(schema_dir))
        return result, files

    def _minimal_spec_kwargs(self):
        return {
            "schema": "my_schema",
            "ng": [
                _ng(
                    "branch",
                    "ng-uuid-1",
                    fields=[
                        _field("title", "node-uuid-1", "string"),
                    ],
                )
            ],
        }

    def test_returns_dict_with_expected_keys(self):
        result, _ = self._run_generate(self._minimal_spec_kwargs())
        for key in (
            "slug",
            "schema",
            "graph_id",
            "tops",
            "geoms",
            "grains",
            "grain_view_names",
        ):
            self.assertIn(key, result)

    def test_branch_mv_file_written(self):
        _, files = self._run_generate(self._minimal_spec_kwargs())
        self.assertIn("mv_branch.sql", files)

    def test_mv_resource_file_written(self):
        _, files = self._run_generate(self._minimal_spec_kwargs())
        self.assertIn("mv_resource.sql", files)

    def test_mv_resource_flat_file_written(self):
        _, files = self._run_generate(self._minimal_spec_kwargs())
        self.assertIn("mv_resource_flat.sql", files)

    def test_resource_view_file_written(self):
        _, files = self._run_generate(self._minimal_spec_kwargs())
        self.assertIn("resource_view.sql", files)

    def test_flat_views_file_written(self):
        _, files = self._run_generate(self._minimal_spec_kwargs())
        self.assertIn("flat_views.sql", files)

    def test_refresh_resource_file_written(self):
        _, files = self._run_generate(self._minimal_spec_kwargs())
        self.assertIn("refresh_resource.sql", files)

    def test_refresh_flat_file_written(self):
        _, files = self._run_generate(self._minimal_spec_kwargs())
        self.assertIn("refresh_flat.sql", files)

    def test_alignment_test_file_written(self):
        _, files = self._run_generate(self._minimal_spec_kwargs())
        self.assertIn("alignment_test.sql", files)

    def test_grain_flat_file_written_for_configured_grain(self):
        spec_kw = {
            "schema": "my_schema",
            "flat_grains": ["branch"],
            "ng": [
                _ng(
                    "branch",
                    "ng-uuid-1",
                    cardinality="n",
                    fields=[
                        _field("title", "node-uuid-1", "string"),
                    ],
                )
            ],
        }
        _, files = self._run_generate(spec_kw)
        self.assertIn("mv_branch_flat.sql", files)

    def test_grain_flat_file_uses_alias_name_not_view_name(self):
        """The MV file is named after the nodegroup alias, not the stable view name."""
        spec_kw = {
            "schema": "my_schema",
            "flat_grains": ["old_alias"],
            "flat_grain_view_names": {"old_alias": "stable_name"},
            "ng": [
                _ng(
                    "old_alias",
                    "ng-uuid-1",
                    cardinality="n",
                    fields=[
                        _field("title", "node-uuid-1", "string"),
                    ],
                )
            ],
        }
        _, files = self._run_generate(spec_kw)
        self.assertIn("mv_old_alias_flat.sql", files)
        self.assertNotIn("mv_stable_name_flat.sql", files)

    def test_geom_mv_file_written(self):
        spec_kw = {
            "schema": "my_schema",
            "ng": [
                _ng(
                    "boundary",
                    "ng-uuid-1",
                    fields=[
                        _field(
                            "site_boundary", "node-uuid-1", "geojson-feature-collection"
                        ),
                    ],
                )
            ],
        }
        _, files = self._run_generate(spec_kw)
        self.assertIn("mv_geom_site_boundary.sql", files)

    def test_result_tops_matches_top_level_nodegroups(self):
        result, _ = self._run_generate(self._minimal_spec_kwargs())
        self.assertIn("branch", result["tops"])

    def test_result_schema_matches_spec(self):
        result, _ = self._run_generate(self._minimal_spec_kwargs())
        self.assertEqual(result["schema"], "my_schema")


# ---------------------------------------------------------------------------
# _alignment_test — no _v1 suffix
# ---------------------------------------------------------------------------


class TestAlignmentTest(SimpleTestCase):
    def test_no_v1_suffix_in_alignment_test_output(self):
        spec_kw = {
            "schema": "my_schema",
            "flat_grains": ["items"],
            "ng": [
                _ng(
                    "branch",
                    "ng-uuid-1",
                    cardinality="n",
                    fields=[
                        _field("name", "node-uuid-1", "string"),
                    ],
                ),
                _ng(
                    "items",
                    "ng-uuid-2",
                    parent="branch",
                    cardinality="n",
                    fields=[
                        _field("label", "node-uuid-3", "string"),
                    ],
                ),
            ],
        }
        spec = _spec(**spec_kw)
        gen = SpecGenerator(spec, tempfile.gettempdir())
        res_cols = gen._build_table(None)
        grain_tables = [(g, gen._build_table(g)) for g in gen.GRAINS]
        output = gen._alignment_test(res_cols, grain_tables)
        self.assertNotIn("_v1", output)

    def test_no_alignment_groups_produces_comment(self):
        """A spec with no cardinality-n nodegroups yields the 'no groups found' comment."""
        spec_kw = {
            "ng": [
                _ng(
                    "branch",
                    "ng-uuid-1",
                    cardinality="1",
                    fields=[
                        _field("title", "node-uuid-1", "string"),
                    ],
                )
            ],
        }
        spec = _spec(**spec_kw)
        gen = SpecGenerator(spec, tempfile.gettempdir())
        res_cols = gen._build_table(None)
        output = gen._alignment_test(res_cols, [])
        self.assertIn("No alignment groups found", output)
