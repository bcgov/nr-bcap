import ast
from pathlib import Path
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION = REPO_ROOT / "bcap" / "migrations" / "1436_reapply_qgis_views_epsg_3005.py"
EXPECTED_VIEWS = {
    "bc_labelled_site_visit_geometries": "site_visit",
    "bc_labelled_geojson_geometries": None,
    "bc_labelled_sandcastle_geometries": "sandcastle",
    "bc_labelled_site_geometries": "archaeological_site",
}
VIEW_SQL_DIR = REPO_ROOT / "bcap" / "migrations" / "sql" / "views"


def _literal_assignment(tree, name):
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == name
                for target in node.targets
            ):
                return ast.literal_eval(node.value)
    raise AssertionError(f"{name} is not a literal assignment")


class QGISProjectionUpgradeMigrationTests(unittest.TestCase):
    """Protect upgrades whose database has already recorded migration 855."""

    def setUp(self):
        self.assertTrue(
            MIGRATION.exists(),
            "Changing already-applied migration 855 does not update deployed databases; "
            "a new forward migration is required.",
        )
        self.tree = ast.parse(MIGRATION.read_text(encoding="utf-8"))

    def test_new_forward_migration_depends_on_current_leaf(self):
        dependencies = _literal_assignment(self.tree, "DEPENDENCIES")
        self.assertIn(("bcap", "1435_permission_role_groups"), dependencies)

    def test_new_forward_migration_reprojects_all_qgis_views_to_epsg_3005(self):
        view_sql = _literal_assignment(self.tree, "VIEW_SQL")
        self.assertEqual(set(view_sql), set(EXPECTED_VIEWS))
        for view, graph_slug in EXPECTED_VIEWS.items():
            sql = view_sql[view]
            # PostgreSQL refuses CREATE OR REPLACE when the geometry typmod
            # changes from EPSG:4326 to EPSG:3005, so an upgrade must replace
            # the view rather than only replace its query.
            self.assertIn(f"drop view if exists public.{view}", sql.lower())
            self.assertIn(f"create view public.{view}", sql.lower())
            self.assertIn(
                "ST_Transform(g.geom, 3005)::geometry(Geometry, 3005) as geom",
                sql,
            )
            self.assertNotIn("g.*", sql)
            if graph_slug is not None:
                self.assertIn(f"gr.slug = '{graph_slug}'", sql)

    def test_checked_in_view_sql_declares_epsg_3005_metadata(self):
        expected = "ST_Transform(g.geom, 3005)::geometry(Geometry, 3005) as geom"
        for view in EXPECTED_VIEWS:
            sql = (VIEW_SQL_DIR / f"{view}.sql").read_text(encoding="utf-8")
            self.assertIn(expected, sql)

    def test_reverse_sql_restores_pre_fix_view_definitions(self):
        reverse_sql = _literal_assignment(self.tree, "REVERSE_SQL")
        self.assertEqual(set(reverse_sql), set(EXPECTED_VIEWS))
        for view, sql in reverse_sql.items():
            self.assertIn(f"drop view if exists public.{view}", sql.lower())
            self.assertIn(f"create view public.{view}", sql.lower())
            self.assertIn("g.*", sql)
            self.assertNotIn("ST_Transform(g.geom, 3005)", sql)


if __name__ == "__main__":
    unittest.main()
