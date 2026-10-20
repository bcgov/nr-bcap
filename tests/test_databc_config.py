"""
Structural tests for bcap.databc_config.GRAPHS.

These verify that the config has the required shape that generate_databc_views
and the contract test depend on, catching typos and missing keys early.
"""

from django.test import SimpleTestCase

from bcap.databc_config import GRAPHS


class TestDatabcConfigStructure(SimpleTestCase):
    def test_every_graph_has_the_required_shape(self):
        self.assertTrue(GRAPHS)
        for slug, cfg in GRAPHS.items():
            with self.subTest(slug=slug):
                for key in ("arches_slug", "flat_grains", "view_names"):
                    self.assertIn(key, cfg, f"missing {key!r}")

                self.assertIsInstance(cfg["arches_slug"], str)
                self.assertTrue(cfg["arches_slug"], "arches_slug is empty")

                grains = cfg["flat_grains"]
                self.assertIsInstance(grains, list)
                for grain in grains:
                    self.assertIsInstance(grain, str, f"grain {grain!r} is not str")
                self.assertEqual(
                    len(grains), len(set(grains)), "duplicate flat_grains entries"
                )

                view_names = cfg["view_names"]
                self.assertIsInstance(view_names, dict)
                for alias, stable in view_names.items():
                    self.assertIn(alias, grains, f"{alias!r} not in flat_grains")
                    self.assertIsInstance(stable, str, f"{alias!r} value is not str")

    def test_arches_slugs_are_unique(self):
        slugs = [cfg["arches_slug"] for cfg in GRAPHS.values()]
        self.assertEqual(len(slugs), len(set(slugs)), f"duplicates in {slugs}")
