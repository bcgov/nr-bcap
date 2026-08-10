"""
Unit tests for SiteVisitDescriptors.

Django/Arches is already configured by the test runner; individual ORM calls
are mocked with @patch so no database access is required.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import TestCase

# DataTypeFactory() is evaluated at class-body level when the module is first
# imported. In CI the DB tables don't exist at collection time, so we mock it
# for the duration of the import to prevent a premature DB query.
with patch("arches.app.datatypes.datatypes.DataTypeFactory"):
    from bcap.functions.bcap_site_descriptors import BCAPSiteDescriptors
    from bcap.functions.process_requirement_descriptors import (
        ProcessRequirementDescriptors,
    )
    from bcap.functions.site_visit_descriptors import SiteVisitDescriptors

from bcap.util.aliases.site_visit import SiteVisitAliases as A


def _make_node(alias, name, datatype="string", nodegroup_id="ng-1", nodeid="node-1"):
    node = MagicMock()
    node.alias = alias
    node.name = name
    node.datatype = datatype
    node.nodegroup_id = nodegroup_id
    node.nodeid = nodeid
    return node


def _reset_class_state():
    """Reset class-level caches between tests."""
    SiteVisitDescriptors._initialized = False
    SiteVisitDescriptors._nodes = {}
    SiteVisitDescriptors._datatypes = {}
    SiteVisitDescriptors._html_nodes = []


class TestGetNameDescriptor(TestCase):
    def setUp(self):
        _reset_class_state()
        SiteVisitDescriptors._initialized = True  # skip initialize()
        SiteVisitDescriptors._nodes = {
            A.ASSOCIATED_PERMIT: _make_node(A.ASSOCIATED_PERMIT, "Associated Permit"),
            A.LAST_DATE_OF_SITE_VISIT: _make_node(
                A.LAST_DATE_OF_SITE_VISIT, "Last Date"
            ),
            A.AFFILIATION: _make_node(A.AFFILIATION, "Affiliation"),
        }
        self.fn = SiteVisitDescriptors()

        models_patch = patch("bcap.functions.site_visit_descriptors.models")
        self.mock_models = models_patch.start()
        self.addCleanup(models_patch.stop)
        self.addCleanup(_reset_class_state)

    def _name(self, values):
        with patch.object(
            SiteVisitDescriptors,
            "_get_value_from_node",
            side_effect=lambda node_alias, **kwargs: values.get(node_alias),
        ):
            return self.fn.get_primary_descriptor_from_nodes(
                MagicMock(), config={}, descriptor="name"
            )

    def test_joins_permit_date_and_affiliation(self):
        result = self._name(
            {
                A.ASSOCIATED_PERMIT: "1993-123",
                A.LAST_DATE_OF_SITE_VISIT: "2024-05-01",
                A.AFFILIATION: "Crew A",
            }
        )
        assert result == "1993-123 - 2024/05/01 - Crew A"

    def test_missing_permit_falls_back_to_non_permit_label(self):
        result = self._name({A.LAST_DATE_OF_SITE_VISIT: "2024-05-01"})
        assert result == "Non-permit - 2024/05/01"

    def test_date_separators_become_slashes(self):
        # Dashes would otherwise collide with the " - " field connector.
        result = self._name(
            {A.ASSOCIATED_PERMIT: "1993-123", A.LAST_DATE_OF_SITE_VISIT: "2024-05-01"}
        )
        assert "2024/05/01" in result
        assert result.count(" - ") == 1

    def test_permit_only_returns_bare_permit(self):
        assert self._name({A.ASSOCIATED_PERMIT: "1993-123"}) == "1993-123"

    def test_nothing_set_returns_non_permit_label(self):
        assert self._name({}) == "Non-permit"


class TestGetSearchCardDescriptor(TestCase):
    def setUp(self):
        _reset_class_state()
        SiteVisitDescriptors._initialized = True
        SiteVisitDescriptors._nodes = {
            A.SITE_VISIT_TYPE: _make_node(A.SITE_VISIT_TYPE, "Site Visit Type"),
            A.PROJECT_DESCRIPTION: _make_node(
                A.PROJECT_DESCRIPTION, "Project Description"
            ),
            A.ARCHAEOLOGICAL_SITE: _make_node(
                A.ARCHAEOLOGICAL_SITE, "Archaeological Site"
            ),
        }
        self.fn = SiteVisitDescriptors()

        models_patch = patch("bcap.functions.site_visit_descriptors.models")
        self.mock_models = models_patch.start()
        self.addCleanup(models_patch.stop)
        # The descriptor fetches the site-visit-type tiles once and hands them
        # down; an empty list would make the base re-query per nodegroup.
        self.mock_models.TileModel.objects.filter.return_value.all.return_value = [
            MagicMock()
        ]
        base_models = patch(
            "bcgov_arches_common.functions.abstract_primary_descriptors.models"
        )
        self.mock_base_models = base_models.start()
        self.addCleanup(base_models.stop)
        self.addCleanup(_reset_class_state)

    def test_description_labels_each_card_node(self):
        values = {
            A.SITE_VISIT_TYPE: "Field Inspection",
            A.PROJECT_DESCRIPTION: "Roadside survey",
            A.ARCHAEOLOGICAL_SITE: "DjRi-123",
        }
        with patch.object(
            SiteVisitDescriptors,
            "_get_value_from_node",
            side_effect=lambda node_alias, **kwargs: values.get(node_alias),
        ):
            result = self.fn.get_primary_descriptor_from_nodes(
                MagicMock(),
                config={"first_only": False, "show_name": True},
                descriptor="description",
            )

        for label, value in (
            ("Site Visit Type", "Field Inspection"),
            ("Project Description", "Roadside survey"),
            ("Archaeological Site", "DjRi-123"),
        ):
            assert label in result
            assert value in result

    def test_description_with_no_values_returns_empty_string(self):
        with patch.object(
            SiteVisitDescriptors, "_get_value_from_node", return_value=None
        ):
            result = self.fn.get_primary_descriptor_from_nodes(
                MagicMock(),
                config={"first_only": False, "show_name": True},
                descriptor="description",
            )
        assert result == ""

    def test_first_only_returns_on_first_truthy_value_and_stops(self):
        call_log: list[str] = []

        def side_effect(node_alias, **kwargs):
            call_log.append(node_alias)
            return "Field Inspection"

        with patch.object(
            SiteVisitDescriptors, "_get_value_from_node", side_effect=side_effect
        ):
            result = self.fn.get_primary_descriptor_from_nodes(
                MagicMock(),
                config={"first_only": True, "show_name": False},
                descriptor="description",
            )

        assert result == "Field Inspection"
        assert call_log == [A.SITE_VISIT_TYPE]


class TestGetMapPopupDescriptor(TestCase):
    def setUp(self):
        _reset_class_state()
        SiteVisitDescriptors._initialized = True
        self.addCleanup(_reset_class_state)

    def test_popup_aliases_are_empty_so_popup_is_empty(self):
        """No _popup_node_aliases is declared, so this inherits the base's []."""
        result = SiteVisitDescriptors().get_primary_descriptor_from_nodes(
            MagicMock(),
            config={"first_only": False, "show_name": True},
            descriptor="map_popup",
        )
        assert result == ""


class TestSiblingClassesDoNotShareState(TestCase):
    """The three descriptors share one base. Assigning config onto the base
    instead of the subclass would make whichever initialized last win."""

    DESCRIPTORS = (
        SiteVisitDescriptors,
        BCAPSiteDescriptors,
        ProcessRequirementDescriptors,
    )

    def test_each_declares_its_own_graph_slug(self):
        slugs = set()
        for cls in self.DESCRIPTORS:
            assert "_graph_slug" in cls.__dict__, f"{cls.__name__} inherits _graph_slug"
            slugs.add(cls._graph_slug)
        assert len(slugs) == len(self.DESCRIPTORS)

    def test_each_declares_its_own_alias_lists(self):
        for cls in self.DESCRIPTORS:
            assert "_name_node_aliases" in cls.__dict__
            assert "_card_node_aliases" in cls.__dict__

    def test_initialize_assigns_node_caches_per_subclass(self):
        for cls in self.DESCRIPTORS:
            cls._initialized = False
            cls._nodes = {}
        with patch(
            "bcgov_arches_common.functions.abstract_primary_descriptors.models"
        ) as mock_models:
            mock_models.Node.objects.filter.return_value.first.return_value = None
            mock_models.CardXNodeXWidget.objects.filter.return_value.filter.return_value.all.return_value = (
                []
            )
            SiteVisitDescriptors.initialize()

        assert "_nodes" in SiteVisitDescriptors.__dict__
        assert SiteVisitDescriptors._initialized is True
        assert BCAPSiteDescriptors._initialized is False
        assert ProcessRequirementDescriptors._initialized is False

        for cls in self.DESCRIPTORS:
            cls._initialized = False
            cls._nodes = {}
