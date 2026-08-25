"""
Structural tests for bcap.databc_config.GRAPHS.

These verify that the config has the required shape that generate_databc_views
and the contract test depend on, catching typos and missing keys early.
"""

from django.test import SimpleTestCase

from bcap.databc_config import GRAPHS


class TestDatabcConfigStructure(SimpleTestCase):
    """Each entry in GRAPHS must have the required keys and correct types."""

    def test_graphs_is_non_empty_dict(self):
        self.assertIsInstance(GRAPHS, dict)
        self.assertGreater(len(GRAPHS), 0)

    def test_all_graphs_have_arches_slug(self):
        for slug, cfg in GRAPHS.items():
            with self.subTest(slug=slug):
                self.assertIn("arches_slug", cfg, f"{slug!r} missing 'arches_slug'")
                self.assertIsInstance(cfg["arches_slug"], str)
                self.assertTrue(cfg["arches_slug"], f"{slug!r} arches_slug is empty")

    def test_all_graphs_have_flat_grains(self):
        for slug, cfg in GRAPHS.items():
            with self.subTest(slug=slug):
                self.assertIn("flat_grains", cfg, f"{slug!r} missing 'flat_grains'")
                self.assertIsInstance(cfg["flat_grains"], list)

    def test_all_graphs_have_view_names(self):
        for slug, cfg in GRAPHS.items():
            with self.subTest(slug=slug):
                self.assertIn("view_names", cfg, f"{slug!r} missing 'view_names'")
                self.assertIsInstance(cfg["view_names"], dict)

    def test_view_names_keys_are_in_flat_grains(self):
        """Every key in view_names must be a member of flat_grains."""
        for slug, cfg in GRAPHS.items():
            with self.subTest(slug=slug):
                for alias in cfg["view_names"]:
                    self.assertIn(
                        alias,
                        cfg["flat_grains"],
                        f"{slug!r}: view_names key {alias!r} not in flat_grains",
                    )

    def test_flat_grain_entries_are_strings(self):
        for slug, cfg in GRAPHS.items():
            with self.subTest(slug=slug):
                for grain in cfg["flat_grains"]:
                    self.assertIsInstance(
                        grain, str, f"{slug!r}: grain {grain!r} is not str"
                    )

    def test_view_names_values_are_strings(self):
        for slug, cfg in GRAPHS.items():
            with self.subTest(slug=slug):
                for alias, stable in cfg["view_names"].items():
                    self.assertIsInstance(
                        stable,
                        str,
                        f"{slug!r}: view_names[{alias!r}] value is not str",
                    )

    def test_arches_slugs_are_unique(self):
        arches_slugs = [cfg["arches_slug"] for cfg in GRAPHS.values()]
        self.assertEqual(
            len(arches_slugs),
            len(set(arches_slugs)),
            f"Duplicate arches_slug values: {arches_slugs}",
        )

    def test_no_duplicate_flat_grains_within_a_graph(self):
        for slug, cfg in GRAPHS.items():
            with self.subTest(slug=slug):
                grains = cfg["flat_grains"]
                self.assertEqual(
                    len(grains),
                    len(set(grains)),
                    f"{slug!r} has duplicate flat_grains entries",
                )
