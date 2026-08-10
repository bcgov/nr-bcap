import json
import tempfile
import uuid
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

from django.test import SimpleTestCase

from bcap.management.commands.reload_permit_models import (
    EXCLUDED_RESOURCE_MODELS,
    Command,
    _read_graph_meta,
)

_MODULE = "bcap.management.commands.reload_permit_models"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_graph_json(graphid, slug):
    """Minimal graph JSON payload."""
    return json.dumps({"graph": [{"graphid": str(graphid), "slug": slug}]})


def _cmd():
    return Command(stdout=StringIO(), stderr=StringIO())


def _write_graph(directory, filename, slug):
    """Write a graph JSON file and return (path_str, graphid_str)."""
    gid = str(uuid.uuid4())
    path = Path(directory) / filename
    path.write_text(_make_graph_json(gid, slug))
    return str(path), gid


class _GraphDoesNotExist(Exception):
    """Stand-in for Graph.DoesNotExist so the except clause can catch it."""


# ---------------------------------------------------------------------------
# _read_graph_meta
# ---------------------------------------------------------------------------


class TestReadGraphMeta(SimpleTestCase):
    def test_returns_graphid_and_slug(self):
        gid = str(uuid.uuid4())
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.json"
            path.write_text(_make_graph_json(gid, "my_slug"))
            graphid, slug = _read_graph_meta(str(path))
        self.assertEqual(graphid, gid)
        self.assertEqual(slug, "my_slug")

    def test_reads_first_graph_entry_only(self):
        gid = str(uuid.uuid4())
        data = json.dumps({
            "graph": [
                {"graphid": gid, "slug": "first"},
                {"graphid": str(uuid.uuid4()), "slug": "second"},
            ]
        })
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.json"
            path.write_text(data)
            graphid, slug = _read_graph_meta(str(path))
        self.assertEqual(slug, "first")
        self.assertEqual(graphid, gid)


# ---------------------------------------------------------------------------
# _permit_model_paths
# ---------------------------------------------------------------------------


class TestPermitModelPaths(SimpleTestCase):
    def test_excludes_slugs_in_excluded_set(self):
        excluded_slug = next(iter(EXCLUDED_RESOURCE_MODELS))
        with tempfile.TemporaryDirectory() as tmpdir:
            rm_dir = Path(tmpdir) / "graphs" / "resource_models"
            rm_dir.mkdir(parents=True)
            _write_graph(rm_dir, "excluded.json", excluded_slug)
            with patch(f"{_MODULE}._pkg", return_value=Path(tmpdir)):
                paths = Command._permit_model_paths()
        self.assertEqual(paths, [])

    def test_includes_non_excluded_slug(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rm_dir = Path(tmpdir) / "graphs" / "resource_models"
            rm_dir.mkdir(parents=True)
            path, _ = _write_graph(rm_dir, "permit.json", "permit_application")
            with patch(f"{_MODULE}._pkg", return_value=Path(tmpdir)):
                paths = Command._permit_model_paths()
        self.assertEqual(paths, [path])

    def test_mixes_excluded_and_included(self):
        excluded_slug = next(iter(EXCLUDED_RESOURCE_MODELS))
        with tempfile.TemporaryDirectory() as tmpdir:
            rm_dir = Path(tmpdir) / "graphs" / "resource_models"
            rm_dir.mkdir(parents=True)
            _write_graph(rm_dir, "excluded.json", excluded_slug)
            included_path, _ = _write_graph(rm_dir, "permit.json", "permit_application")
            with patch(f"{_MODULE}._pkg", return_value=Path(tmpdir)):
                paths = Command._permit_model_paths()
        self.assertEqual(paths, [included_path])

    def test_returns_sorted_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            rm_dir = Path(tmpdir) / "graphs" / "resource_models"
            rm_dir.mkdir(parents=True)
            path_b, _ = _write_graph(rm_dir, "b_model.json", "b_model")
            path_a, _ = _write_graph(rm_dir, "a_model.json", "a_model")
            with patch(f"{_MODULE}._pkg", return_value=Path(tmpdir)):
                paths = Command._permit_model_paths()
        self.assertEqual(paths, sorted([path_a, path_b]))


# ---------------------------------------------------------------------------
# _graph_paths
# ---------------------------------------------------------------------------


class TestGraphPaths(SimpleTestCase):
    def test_returns_path_for_existing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            branch_dir = Path(tmpdir) / "graphs" / "branches"
            branch_dir.mkdir(parents=True)
            (branch_dir / "My Branch.json").write_text("{}")
            with patch(f"{_MODULE}._pkg", return_value=Path(tmpdir)):
                paths = Command._graph_paths("branches", ["My Branch"])
        self.assertEqual(len(paths), 1)
        self.assertTrue(paths[0].endswith("My Branch.json"))

    def test_raises_for_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "graphs" / "branches").mkdir(parents=True)
            with patch(f"{_MODULE}._pkg", return_value=Path(tmpdir)):
                with self.assertRaises(FileNotFoundError):
                    Command._graph_paths("branches", ["Missing Branch"])


# ---------------------------------------------------------------------------
# handle() — option routing
# ---------------------------------------------------------------------------


class TestHandleRouting(SimpleTestCase):
    """handle() dispatches to the correct sub-methods based on CLI flags."""

    def _run(self, **overrides):
        cmd = _cmd()
        options = {
            "skip_graphs": False,
            "skip_lists": False,
            "skip_requirements": False,
            "delete_tiles": False,
            "skip_reindex": False,
        }
        options.update(overrides)
        with (
            patch.object(cmd, "reload_graphs") as mg,
            patch.object(cmd, "reload_lists") as ml,
            patch.object(cmd, "reload_requirement_templates") as mr,
            patch.object(cmd, "delete_permit_data") as md,
            patch.object(cmd, "reindex_resources") as mi,
            patch(f"{_MODULE}.cache") as mc,
        ):
            cmd.handle(**options)
            return mg, ml, mr, md, mi, mc

    def test_default_runs_all_methods(self):
        mg, ml, mr, md, mi, mc = self._run()
        mg.assert_called_once()
        ml.assert_called_once()
        mr.assert_called_once()
        md.assert_not_called()
        mi.assert_called_once()
        mc.clear.assert_called_once()

    def test_cache_is_always_cleared(self):
        *_, mc = self._run(skip_graphs=True, skip_lists=True, skip_requirements=True, skip_reindex=True)
        mc.clear.assert_called_once()

    def test_skip_graphs_omits_reload_graphs(self):
        mg, ml, *_ = self._run(skip_graphs=True)
        mg.assert_not_called()
        ml.assert_called_once()

    def test_skip_lists_omits_reload_lists(self):
        mg, ml, *_ = self._run(skip_lists=True)
        mg.assert_called_once()
        ml.assert_not_called()

    def test_skip_requirements_omits_reload_requirement_templates(self):
        _, _, mr, *_ = self._run(skip_requirements=True)
        mr.assert_not_called()

    def test_delete_tiles_calls_delete_permit_data(self):
        _, _, _, md, *_ = self._run(delete_tiles=True)
        md.assert_called_once()

    def test_no_delete_tiles_skips_delete_permit_data(self):
        _, _, _, md, *_ = self._run(delete_tiles=False)
        md.assert_not_called()

    def test_skip_reindex_omits_reindex_resources(self):
        *_, mi, _ = self._run(skip_reindex=True)
        mi.assert_not_called()


# ---------------------------------------------------------------------------
# _prepare_graphs_for_import
# ---------------------------------------------------------------------------


class TestPrepareGraphsForImport(SimpleTestCase):
    """_prepare_graphs_for_import correctly prepares each existing graph."""

    def _prepare(self, paths, valid_pubs=None, dangling_count=0, has_draft=False,
                 graph_does_not_exist=False):
        """
        Run _prepare_graphs_for_import with standard mocks.

        Returns (cmd, mock_graph, mock_models, mock_dangling_qs).
        """
        cmd = _cmd()
        valid_pubs = list(valid_pubs or [])

        mock_graph = MagicMock()
        mock_graph.get_draft_graph.return_value = MagicMock() if has_draft else None

        if graph_does_not_exist:
            mock_graph_get = Mock(side_effect=_GraphDoesNotExist())
        else:
            mock_graph_get = Mock(return_value=mock_graph)

        mock_dangling_qs = MagicMock()
        mock_dangling_qs.exists.return_value = dangling_count > 0
        mock_dangling_qs.update.return_value = dangling_count

        with (
            patch(f"{_MODULE}.arches_models") as mock_models,
            patch(f"{_MODULE}.Graph") as MockGraph,
        ):
            MockGraph.objects.get = mock_graph_get
            MockGraph.DoesNotExist = _GraphDoesNotExist
            mock_models.GraphXPublishedGraph.objects.values_list.return_value = valid_pubs
            (
                mock_models.Node.objects
                .filter.return_value
                .exclude.return_value
            ) = mock_dangling_qs
            cmd._prepare_graphs_for_import(paths)

        return cmd, mock_graph, mock_models, mock_dangling_qs

    def test_skips_prep_for_new_graph(self):
        """A graph not yet in the DB is silently skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path, _ = _write_graph(tmpdir, "new.json", "new_model")
            cmd, mock_graph, *_ = self._prepare([path], graph_does_not_exist=True)
        mock_graph.create_draft_graph.assert_not_called()
        mock_graph.promote_draft_graph_to_active_graph.assert_not_called()

    def test_creates_draft_when_none_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path, _ = _write_graph(tmpdir, "existing.json", "existing_model")
            cmd, mock_graph, *_ = self._prepare([path], has_draft=False)
        mock_graph.create_draft_graph.assert_called_once()

    def test_skips_create_draft_when_draft_already_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path, _ = _write_graph(tmpdir, "existing.json", "existing_model")
            cmd, mock_graph, *_ = self._prepare([path], has_draft=True)
        mock_graph.create_draft_graph.assert_not_called()

    def test_promotes_draft_to_active(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path, _ = _write_graph(tmpdir, "existing.json", "existing_model")
            cmd, mock_graph, *_ = self._prepare([path])
        mock_graph.promote_draft_graph_to_active_graph.assert_called_once()

    def test_clears_dangling_sourcebranchpublication_refs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path, _ = _write_graph(tmpdir, "existing.json", "existing_model")
            cmd, mock_graph, mock_models, mock_dangling = self._prepare(
                [path], dangling_count=3
            )
        mock_dangling.update.assert_called_once_with(sourcebranchpublication=None)

    def test_no_dangling_refs_skips_update(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path, _ = _write_graph(tmpdir, "existing.json", "existing_model")
            cmd, mock_graph, mock_models, mock_dangling = self._prepare(
                [path], dangling_count=0
            )
        mock_dangling.update.assert_not_called()

    def test_refresh_called_after_dangling_update(self):
        """refresh_from_database is called again after nulling dangling refs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path, _ = _write_graph(tmpdir, "existing.json", "existing_model")
            cmd, mock_graph, *_ = self._prepare([path], dangling_count=2)
        # First call is at the top of the loop; second is after clearing dangling refs.
        self.assertGreaterEqual(mock_graph.refresh_from_database.call_count, 2)

    def test_deletes_live_cnw_rows_after_promote(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path, _ = _write_graph(tmpdir, "existing.json", "existing_model")
            cmd, mock_graph, mock_models, *_ = self._prepare([path])
        mock_models.CardXNodeXWidget.objects.filter.return_value.delete.assert_called_once()

    def test_processes_multiple_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path_a, _ = _write_graph(tmpdir, "a.json", "model_a")
            path_b, _ = _write_graph(tmpdir, "b.json", "model_b")
            cmd = _cmd()
            mock_graph = MagicMock()
            mock_graph.get_draft_graph.return_value = None
            mock_dangling_qs = MagicMock()
            mock_dangling_qs.exists.return_value = False
            with (
                patch(f"{_MODULE}.arches_models") as mock_models,
                patch(f"{_MODULE}.Graph") as MockGraph,
            ):
                MockGraph.objects.get.return_value = mock_graph
                MockGraph.DoesNotExist = _GraphDoesNotExist
                mock_models.GraphXPublishedGraph.objects.values_list.return_value = []
                (
                    mock_models.Node.objects
                    .filter.return_value
                    .exclude.return_value
                ) = mock_dangling_qs
                cmd._prepare_graphs_for_import([path_a, path_b])
        self.assertEqual(mock_graph.promote_draft_graph_to_active_graph.call_count, 2)


# ---------------------------------------------------------------------------
# _publish_and_sync_resources
# ---------------------------------------------------------------------------


class TestPublishAndSyncResources(SimpleTestCase):
    def _publish(self, paths, updated_count=0):
        cmd = _cmd()
        pub_id = uuid.uuid4()
        mock_graph = MagicMock()
        mock_graph.publication_id = pub_id
        mock_ri_qs = MagicMock()
        mock_ri_qs.exclude.return_value.update.return_value = updated_count

        with (
            patch(f"{_MODULE}.arches_models") as mock_models,
            patch(f"{_MODULE}.Graph") as MockGraph,
        ):
            MockGraph.objects.get.return_value = mock_graph
            mock_models.ResourceInstance.objects.filter.return_value = mock_ri_qs
            cmd._publish_and_sync_resources(paths)

        return cmd, mock_graph, mock_ri_qs

    def test_publishes_each_graph(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            for name in ("a.json", "b.json"):
                p, _ = _write_graph(tmpdir, name, f"model_{name}")
                paths.append(p)
            cmd, mock_graph, _ = self._publish(paths)
        self.assertEqual(mock_graph.publish.call_count, 2)

    def test_publishes_with_reload_notes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path, _ = _write_graph(tmpdir, "a.json", "model_a")
            cmd, mock_graph, _ = self._publish([path])
        mock_graph.publish.assert_called_with(notes="reload_permit_models")

    def test_updates_resource_instances_to_new_publication(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path, _ = _write_graph(tmpdir, "a.json", "model_a")
            cmd, mock_graph, mock_ri_qs = self._publish([path], updated_count=5)
        mock_ri_qs.exclude.return_value.update.assert_called_once_with(
            graph_publication_id=mock_graph.publication_id
        )

    def test_no_output_when_no_instances_moved(self):
        out = StringIO()
        cmd = Command(stdout=out, stderr=StringIO(), no_color=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            path, _ = _write_graph(tmpdir, "a.json", "model_a")
            mock_graph = MagicMock()
            mock_ri_qs = MagicMock()
            mock_ri_qs.exclude.return_value.update.return_value = 0
            with (
                patch(f"{_MODULE}.arches_models") as mock_models,
                patch(f"{_MODULE}.Graph") as MockGraph,
            ):
                MockGraph.objects.get.return_value = mock_graph
                mock_models.ResourceInstance.objects.filter.return_value = mock_ri_qs
                cmd._publish_and_sync_resources([path])
        self.assertNotIn("moved", out.getvalue())

    def test_reports_moved_instances_when_nonzero(self):
        out = StringIO()
        cmd = Command(stdout=out, stderr=StringIO(), no_color=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            path, _ = _write_graph(tmpdir, "a.json", "model_a")
            mock_graph = MagicMock()
            mock_ri_qs = MagicMock()
            mock_ri_qs.exclude.return_value.update.return_value = 7
            with (
                patch(f"{_MODULE}.arches_models") as mock_models,
                patch(f"{_MODULE}.Graph") as MockGraph,
            ):
                MockGraph.objects.get.return_value = mock_graph
                mock_models.ResourceInstance.objects.filter.return_value = mock_ri_qs
                cmd._publish_and_sync_resources([path])
        self.assertIn("7", out.getvalue())
        self.assertIn("moved", out.getvalue())


# ---------------------------------------------------------------------------
# delete_permit_data
# ---------------------------------------------------------------------------


class TestDeletePermitData(SimpleTestCase):
    def _delete(self, slug="permit_application", tile_count=10, instance_count=2):
        cmd = _cmd()
        with tempfile.TemporaryDirectory() as tmpdir:
            rm_dir = Path(tmpdir) / "graphs" / "resource_models"
            rm_dir.mkdir(parents=True)
            _write_graph(rm_dir, "permit.json", slug)
            with (
                patch(f"{_MODULE}._pkg", return_value=Path(tmpdir)),
                patch(f"{_MODULE}.arches_models") as mock_models,
            ):
                mock_graphs = MagicMock()
                mock_models.GraphModel.objects.filter.return_value = mock_graphs
                mock_models.TileModel.objects.filter.return_value.delete.return_value = (tile_count, {})
                mock_models.ResourceInstance.objects.filter.return_value.delete.return_value = (instance_count, {})
                cmd.delete_permit_data()
                return cmd, mock_models

    def test_deletes_tiles(self):
        cmd, mock_models = self._delete()
        mock_models.TileModel.objects.filter.return_value.delete.assert_called_once()

    def test_deletes_resource_instances(self):
        cmd, mock_models = self._delete()
        mock_models.ResourceInstance.objects.filter.return_value.delete.assert_called_once()

    def test_reports_deleted_tile_count(self):
        out = StringIO()
        cmd = Command(stdout=out, stderr=StringIO(), no_color=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            rm_dir = Path(tmpdir) / "graphs" / "resource_models"
            rm_dir.mkdir(parents=True)
            _write_graph(rm_dir, "permit.json", "permit_application")
            with (
                patch(f"{_MODULE}._pkg", return_value=Path(tmpdir)),
                patch(f"{_MODULE}.arches_models") as mock_models,
            ):
                mock_models.GraphModel.objects.filter.return_value = MagicMock()
                mock_models.TileModel.objects.filter.return_value.delete.return_value = (42, {})
                mock_models.ResourceInstance.objects.filter.return_value.delete.return_value = (3, {})
                cmd.delete_permit_data()
        self.assertIn("42", out.getvalue())
        self.assertIn("3", out.getvalue())


# ---------------------------------------------------------------------------
# reindex_resources
# ---------------------------------------------------------------------------


class TestReindexResources(SimpleTestCase):
    def test_calls_es_command_for_each_model(self):
        cmd = _cmd()
        with tempfile.TemporaryDirectory() as tmpdir:
            rm_dir = Path(tmpdir) / "graphs" / "resource_models"
            rm_dir.mkdir(parents=True)
            _, gid1 = _write_graph(rm_dir, "a.json", "model_a")
            _, gid2 = _write_graph(rm_dir, "b.json", "model_b")
            with (
                patch(f"{_MODULE}._pkg", return_value=Path(tmpdir)),
                patch(f"{_MODULE}.call_command") as mock_call,
            ):
                cmd.reindex_resources()
        self.assertEqual(mock_call.call_count, 2)

    def test_uses_es_index_resources_by_type_subcommand(self):
        cmd = _cmd()
        with tempfile.TemporaryDirectory() as tmpdir:
            rm_dir = Path(tmpdir) / "graphs" / "resource_models"
            rm_dir.mkdir(parents=True)
            _, gid = _write_graph(rm_dir, "a.json", "model_a")
            with (
                patch(f"{_MODULE}._pkg", return_value=Path(tmpdir)),
                patch(f"{_MODULE}.call_command") as mock_call,
            ):
                cmd.reindex_resources()
        first_call = mock_call.call_args_list[0]
        self.assertEqual(first_call.args[0], "es")
        self.assertEqual(first_call.args[1], "index_resources_by_type")

    def test_passes_graphid_as_resource_type(self):
        cmd = _cmd()
        with tempfile.TemporaryDirectory() as tmpdir:
            rm_dir = Path(tmpdir) / "graphs" / "resource_models"
            rm_dir.mkdir(parents=True)
            _, gid = _write_graph(rm_dir, "a.json", "model_a")
            with (
                patch(f"{_MODULE}._pkg", return_value=Path(tmpdir)),
                patch(f"{_MODULE}.call_command") as mock_call,
            ):
                cmd.reindex_resources()
        first_call = mock_call.call_args_list[0]
        self.assertEqual(first_call.kwargs["resource_types"], [gid])


# ---------------------------------------------------------------------------
# reload_lists
# ---------------------------------------------------------------------------


class TestReloadLists(SimpleTestCase):
    def test_reads_every_skos_file(self):
        cmd = _cmd()
        with tempfile.TemporaryDirectory() as tmpdir:
            skos_dir = Path(tmpdir) / "reference_data" / "skos"
            skos_dir.mkdir(parents=True)
            (skos_dir / "list1.xml").write_text("<rdf/>")
            (skos_dir / "list2.xml").write_text("<rdf/>")
            with (
                patch(f"{_MODULE}._pkg", return_value=Path(tmpdir)),
                patch(f"{_MODULE}.SKOSReader") as MockSKOS,
            ):
                instance = MockSKOS.return_value
                cmd.reload_lists()
        self.assertEqual(instance.read_file.call_count, 2)
        self.assertEqual(instance.save_controlled_lists_from_skos.call_count, 2)

    def test_uses_overwrite_option(self):
        cmd = _cmd()
        with tempfile.TemporaryDirectory() as tmpdir:
            skos_dir = Path(tmpdir) / "reference_data" / "skos"
            skos_dir.mkdir(parents=True)
            (skos_dir / "list1.xml").write_text("<rdf/>")
            with (
                patch(f"{_MODULE}._pkg", return_value=Path(tmpdir)),
                patch(f"{_MODULE}.SKOSReader") as MockSKOS,
            ):
                instance = MockSKOS.return_value
                cmd.reload_lists()
        kwargs = instance.save_controlled_lists_from_skos.call_args.kwargs
        self.assertEqual(kwargs["overwrite_options"], "overwrite")

    def test_no_error_when_no_skos_files(self):
        cmd = _cmd()
        with tempfile.TemporaryDirectory() as tmpdir:
            skos_dir = Path(tmpdir) / "reference_data" / "skos"
            skos_dir.mkdir(parents=True)
            with (
                patch(f"{_MODULE}._pkg", return_value=Path(tmpdir)),
                patch(f"{_MODULE}.SKOSReader") as MockSKOS,
            ):
                cmd.reload_lists()  # Must not raise.
                MockSKOS.return_value.read_file.assert_not_called()


# ---------------------------------------------------------------------------
# reload_requirement_templates
# ---------------------------------------------------------------------------


class TestReloadRequirementTemplates(SimpleTestCase):
    def _templates(self, n):
        templates = {}
        for i in range(n):
            t = MagicMock()
            t.pk = uuid.uuid4()
            templates[str(i)] = t
        return templates

    def test_deletes_each_existing_template(self):
        cmd = _cmd()
        mock_service = MagicMock()
        mock_service._templates_by_id.return_value = self._templates(3)
        with (
            patch(f"{_MODULE}.ProcessRequirementService", return_value=mock_service),
            patch(f"{_MODULE}.Resource") as MockResource,
            patch(f"{_MODULE}.call_command"),
            patch(f"{_MODULE}.templates_exist", return_value=True),
        ):
            cmd.reload_requirement_templates()
        self.assertEqual(MockResource.objects.get.return_value.delete.call_count, 3)

    def test_calls_seed_template_requirements(self):
        cmd = _cmd()
        mock_service = MagicMock()
        mock_service._templates_by_id.return_value = {}
        with (
            patch(f"{_MODULE}.ProcessRequirementService", return_value=mock_service),
            patch(f"{_MODULE}.Resource"),
            patch(f"{_MODULE}.call_command") as mock_call,
            patch(f"{_MODULE}.templates_exist", return_value=True),
        ):
            cmd.reload_requirement_templates()
        mock_call.assert_called_once_with("seed_template_requirements")

    def test_raises_if_templates_missing_after_reseed(self):
        cmd = _cmd()
        mock_service = MagicMock()
        mock_service._templates_by_id.return_value = {}
        with (
            patch(f"{_MODULE}.ProcessRequirementService", return_value=mock_service),
            patch(f"{_MODULE}.Resource"),
            patch(f"{_MODULE}.call_command"),
            patch(f"{_MODULE}.templates_exist", return_value=False),
        ):
            with self.assertRaises(RuntimeError):
                cmd.reload_requirement_templates()

    def test_no_error_when_no_templates_to_delete(self):
        cmd = _cmd()
        mock_service = MagicMock()
        mock_service._templates_by_id.return_value = {}
        with (
            patch(f"{_MODULE}.ProcessRequirementService", return_value=mock_service),
            patch(f"{_MODULE}.Resource") as MockResource,
            patch(f"{_MODULE}.call_command"),
            patch(f"{_MODULE}.templates_exist", return_value=True),
        ):
            cmd.reload_requirement_templates()  # Must not raise.
        MockResource.objects.get.assert_not_called()
