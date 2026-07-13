"""Builds and clones process_requirement resources.

All knowledge of the process_requirement graph shape lives here: constructing a
requirement from a spec, cloning a template into an editable working copy, and
linking a Document Submission requirement to a submission resource. The service
layer decides what to link where; the seed builders inherit these."""

from urllib.parse import urlparse

from django.db import transaction
from django.utils import timezone

from arches.app.models.resource import Resource
from arches.app.models.tile import Tile

from arches_querysets.models import ResourceTileTree

from bcap.util.aliases.process_requirement import (
    ProcessRequirementAliases as aliases,
    ProcessRequirementGroupAliases as groups,
)
from bcap.util.bcap_aliases import GraphSlugs
from bcap.builders.resource_builder import ResourceBuilder
from bcap.util.controlled_list import reference_value
from bcap.util.graph import node_id
from bcap.util.i18n import localized_string
from bcap.util.links import app_url


class ProcessRequirementBuilder(ResourceBuilder):
    """Construct and clone process_requirement resources."""

    def make_process_requirement(self, spec):
        """Create and return a process requirement resource."""
        requirement = self.new_resource(GraphSlugs.PROCESS_REQUIREMENT)
        identification = self.append_blank_tile_for_group(
            requirement,
            aliases.REQUIREMENT_IDENTIFICATION,
            {
                aliases.REQUIREMENT_IDENTIFICATION: self.localized(spec["id"]),
                aliases.REQUIREMENT_NAME: self.localized(spec["name"]),
            },
        )
        template_data = identification.aliased_data.is_template_requirement.aliased_data
        template_data.is_template_requirement = spec.get("is_template", False)
        template_data.is_internal_requirement = spec.get("internal", True)
        template_data.process_requirement_type = reference_value(
            GraphSlugs.PROCESS_REQUIREMENT,
            aliases.PROCESS_REQUIREMENT_TYPE,
            label=spec.get("type", "Checklist"),
        )
        # TODO: Clean url up stuff later
        if spec.get("url"):
            url = app_url(spec["url"])
            # The url datatype rejects hosts without a dot, so use the loopback IP
            # in dev. TODO: drop once a public (dotted) origin is configured.
            if "." not in urlparse(url).netloc:
                url = url.replace("localhost", "127.0.0.1")
            template_data.workflow_url = {
                "url": url,
                "url_label": spec["resource"].replace("_", " ").title(),
            }
        self.append_blank_tile_for_group(
            requirement,
            groups.REQUIREMENT_EXECUTION_DURATION,
            {aliases.REQUIREMENT_PROCESS_DUE_DATE: spec["due"]},
        )
        self.append_blank_tile_for_group(
            requirement,
            groups.SUB_REQUIREMENT_ASSESSMENT_N1,
            {
                aliases.REQUIREMENT_STATUS: spec["satisfied"],
                aliases.ASSESSMENT_NOTES: self.localized(spec["notes"]),
            },
        )
        # Drop requirement_data's auto-created blank row and add the real items.
        requirement_data = self.append_blank_tile_for_group(
            requirement, groups.REQUIREMENT_DATA, {}
        )
        requirement_data.aliased_data.sub_requirement_n1 = []
        for sub in spec["sub_requirements"]:
            self.append_blank_tile_for_group(
                requirement_data,
                groups.SUB_REQUIREMENT_N1,
                {
                    aliases.CHECKLIST_ITEM_NAME: self.localized(sub["name"]),
                    aliases.CHECKLIST_ITEM_DESCRIPTION: self.localized(
                        sub["description"]
                    ),
                    aliases.CHECKLIST_ITEM_MANDATORY: sub.get("mandatory", False),
                    aliases.CHECKLIST_ITEM_COMPLETED: sub["sub_satisfied"],
                    aliases.CHECKLIST_ITEM_SORT_ORDER: sub["sort_order"],
                },
            )
        requirement.save(**self.save_kwargs)
        self.claim(requirement)
        return requirement

    def clone_requirement(self, template_id):
        """A working copy of the requirement template with the given pk: every
        tile copied with a fresh GUID and the template flag cleared, so the copy
        is a real, editable requirement rather than another template. The caller
        links any submission resource afterward."""
        source = Resource.objects.get(pk=template_id)
        source.load_tiles()
        copy = self.copy_resource(source)
        self._clear_template_flag(copy)
        with transaction.atomic():
            super(Resource, copy).save()
            Tile.objects.bulk_create(copy.tiles)
        # Baseline descriptor so the copy is never descriptor-less when a
        # permit compiles its display; the clone hook re-saves it with the link.
        copy.save_descriptors()
        return copy

    def templates_by_id(self):
        """The is_template_requirement templates, keyed by their requirement id."""
        templates = self._requirements().filter(is_template_requirement=True)
        return {self._requirement_identification(t): t for t in templates}

    def link_parent(self, requirement_id, parent):
        """Point the requirement's parent_requirement tile at the grouping
        parent."""
        requirement = self._get_requirement_by_id(requirement_id)
        self.append_blank_tile_for_group(
            requirement,
            aliases.PARENT_REQUIREMENT,
            {aliases.PARENT_REQUIREMENT: parent},
        )
        requirement.save(**self.save_kwargs)

    def _clear_template_flag(self, resource):
        nodeid = node_id(
            GraphSlugs.PROCESS_REQUIREMENT, aliases.IS_TEMPLATE_REQUIREMENT
        )
        self.set_node_value(resource, nodeid, False)

    def link_submission(self, requirement_id, submission):
        """Point the requirement's submission tile at the given resource. The
        clone already carries the cardinality-1 requirement_data tile, so reuse
        it (appending a second would fail) and only add the submission_data
        sub-tile when the clone lacks one."""
        requirement = self._get_requirement_by_id(requirement_id)
        data = requirement.aliased_data.requirement_data
        if data is None:
            data = self.append_blank_tile_for_group(
                requirement, groups.REQUIREMENT_DATA, {}
            )
        if data.aliased_data.submission_data is None:
            self.append_blank_tile_for_group(data, aliases.SUBMISSION_DATA, {})
        data.aliased_data.submission_data.aliased_data.submission_data = submission
        requirement.save(**self.save_kwargs)

    def make_resource(self, graph_slug):
        """An empty resource of the given graph, owned by the caller."""
        resource = Resource(
            graph_id=self.graph_id(graph_slug),
            resource_instance_lifecycle_state=self.state,
            createdtime=timezone.now(),
            principaluser=self.owner,
        )
        resource.save(user=self.owner, index=False)
        # Without descriptors, rendering a tile that references this resource
        # (the requirement's submission link) hits a None descriptor and fails.
        resource.save_descriptors()
        return resource

    def _requirements(self):
        """The aliased process_requirement tile-tree queryset."""
        return ResourceTileTree.get_tiles(GraphSlugs.PROCESS_REQUIREMENT)

    def _get_requirement_by_id(self, pk):
        """The requirement as an aliased tile tree, fetched by pk, for editing."""
        return self._requirements().get(pk=pk)

    def _requirement_identification(self, requirement):
        """The requirement's business identification (the REQ- string on its
        identification tile), which is what templates are keyed by, not its pk."""
        identification = (
            requirement.aliased_data.requirement_identification.aliased_data
        )
        return localized_string(identification.requirement_identification)
