"""
Unit tests for SiteVisitDescriptors.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import TestCase

from bcap.functions.bcap_site_descriptors import BCAPSiteDescriptors
from bcap.functions.process_requirement_descriptors import (
    ProcessRequirementDescriptors,
)
from bcap.functions.site_visit_descriptors import SiteVisitDescriptors
from bcap.util.aliases.site_visit import SiteVisitAliases as A
from tests.functions.descriptor_helpers import DescriptorTestCase


class SiteVisitTestCase(DescriptorTestCase):
    descriptor_class = SiteVisitDescriptors
    node_names = {
        A.ASSOCIATED_PERMIT: "Associated Permit",
        A.LAST_DATE_OF_SITE_VISIT: "Last Date",
        A.AFFILIATION: "Affiliation",
        A.SITE_VISIT_TYPE: "Site Visit Type",
        A.PROJECT_DESCRIPTION: "Project Description",
        A.ARCHAEOLOGICAL_SITE: "Archaeological Site",
    }

    def setUp(self):
        super().setUp()
        models = patch("bcap.functions.site_visit_descriptors.models")
        self.mock_models = models.start()
        self.addCleanup(models.stop)
        # The card descriptor fetches the site-visit-type tiles once and hands
        # them down; an empty list makes the base re-query per nodegroup.
        self.mock_models.TileModel.objects.filter.return_value.all.return_value = [
            MagicMock()
        ]
        base_models = patch(
            "bcgov_arches_common.functions.abstract_primary_descriptors.models"
        )
        base_models.start()
        self.addCleanup(base_models.stop)


class TestGetNameDescriptor(SiteVisitTestCase):
    def name(self):
        return self.describe(descriptor="name")

    def test_joins_permit_date_and_affiliation(self):
        self.values = {
            A.ASSOCIATED_PERMIT: "1993-123",
            A.LAST_DATE_OF_SITE_VISIT: "2024-05-01",
            A.AFFILIATION: "Crew A",
        }
        assert self.name() == "1993-123 - 2024/05/01 - Crew A"

    def test_missing_permit_falls_back_to_non_permit_label(self):
        self.values = {A.LAST_DATE_OF_SITE_VISIT: "2024-05-01"}
        assert self.name() == "Non-permit - 2024/05/01"

    def test_date_separators_become_slashes(self):
        # Dashes would otherwise collide with the " - " field connector.
        self.values = {
            A.ASSOCIATED_PERMIT: "1993-123",
            A.LAST_DATE_OF_SITE_VISIT: "2024-05-01",
        }
        result = self.name()
        assert "2024/05/01" in result
        assert result.count(" - ") == 1

    def test_permit_only_returns_bare_permit(self):
        self.values = {A.ASSOCIATED_PERMIT: "1993-123"}
        assert self.name() == "1993-123"

    def test_nothing_set_returns_non_permit_label(self):
        assert self.name() == "Non-permit"


class TestGetSearchCardDescriptor(SiteVisitTestCase):
    def test_description_labels_each_card_node(self):
        self.values = {
            A.SITE_VISIT_TYPE: "Field Inspection",
            A.PROJECT_DESCRIPTION: "Roadside survey",
            A.ARCHAEOLOGICAL_SITE: "DjRi-123",
        }
        result = self.describe()
        for label, value in (
            ("Site Visit Type", "Field Inspection"),
            ("Project Description", "Roadside survey"),
            ("Archaeological Site", "DjRi-123"),
        ):
            assert label in result
            assert value in result

    def test_description_with_no_values_returns_empty_string(self):
        assert self.describe() == ""

    def test_first_only_returns_on_first_truthy_value_and_stops(self):
        self.values = {
            A.SITE_VISIT_TYPE: "Field Inspection",
            A.PROJECT_DESCRIPTION: "Roadside survey",
        }
        result = self.describe(first_only=True, show_name=False)
        assert result == "Field Inspection"
        assert self.reads == [A.SITE_VISIT_TYPE]


class TestGetMapPopupDescriptor(SiteVisitTestCase):
    def test_popup_aliases_are_empty_so_popup_is_empty(self):
        """No _popup_node_aliases is declared, so this inherits the base's []."""
        assert self.describe(descriptor="map_popup") == ""
        assert self.reads == []


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
