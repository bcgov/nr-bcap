"""Builds and clones process_requirement resources.

All knowledge of the process_requirement graph shape lives here: constructing a
requirement from a spec, cloning a template into an editable working copy, and
linking a Document Submission requirement to a submission resource. The service
layer decides what to link where; the seed builders inherit these."""

from functools import cached_property
from urllib.parse import urlparse

from django.db import transaction
from django.utils import timezone

from arches.app.datatypes.datatypes import DataTypeFactory
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
from bcap.services.dashboard.base_graph_service import BaseGraphService
from bcap.util.graph import node_id, nodegroup_id
from bcap.util.i18n import localized_string
from bcap.util.links import app_url


class ProcessRequirementBuilder(ResourceBuilder):
    """Construct and clone process_requirement resources."""

    def make_blank_checklist_requirement(self, name):
        """A minimal, editable checklist requirement (no sub-requirements) for a
        staff member to flesh out afterward."""
        return self.make_process_requirement({"id": name, "name": name})

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
            {aliases.REQUIREMENT_PROCESS_DUE_DATE: spec.get("due")},
        )
        self.append_blank_tile_for_group(
            requirement,
            groups.SUB_REQUIREMENT_ASSESSMENT_N1,
            {
                aliases.REQUIREMENT_STATUS: spec.get("satisfied", False),
                aliases.ASSESSMENT_NOTES: self.localized(spec.get("notes", "")),
            },
        )
        # Drop requirement_data's auto-created blank row and add the real items.
        requirement_data = self.append_blank_tile_for_group(
            requirement, groups.REQUIREMENT_DATA, {}
        )
        requirement_data.aliased_data.sub_requirement_n1 = []
        for sub in spec.get("sub_requirements", []):
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

    def update_checklist(self, requirement_id, name, steps):
        """Set a requirement's name and reconcile its ordered checklist steps
        (dicts of an optional tile id, name, and description): steps matched by
        tile id are updated, new ones appended, the rest deleted.

        A partial save, so only the name and step tiles are touched and the rest
        of the requirement is left alone rather than reset by a full-tree
        replace. Partial saves ignore omitted child tiles, so removed steps are
        deleted explicitly."""
        requirement = self._get_requirement_by_id(requirement_id)
        identification = (
            requirement.aliased_data.requirement_identification.aliased_data
        )
        identification.requirement_name = self.localized(name)
        data = requirement.aliased_data.requirement_data
        if data is None:
            data = self.append_blank_tile_for_group(
                requirement, groups.REQUIREMENT_DATA, {}
            )
        existing = {
            str(tile.tileid): tile
            for tile in (data.aliased_data.sub_requirement_n1 or [])
        }
        reconciled = []
        for order, step in enumerate(steps, start=1):
            tile = existing.get(str(step.get("tileid")))
            if tile is None:
                tile = self.append_blank_tile_for_group(
                    data, groups.SUB_REQUIREMENT_N1, {}
                )
            sub = tile.aliased_data
            sub.checklist_item_name = self.localized(step.get("name", ""))
            sub.checklist_item_description = self.localized(step.get("description", ""))
            sub.checklist_item_sort_order = order
            reconciled.append(tile)
        kept = {str(tile.tileid) for tile in reconciled}
        removed = [tile for tileid, tile in existing.items() if tileid not in kept]
        data.aliased_data.sub_requirement_n1 = reconciled
        requirement.save(force_admin=True, partial=True, index=False)
        for tile in removed:
            Tile.objects.get(pk=tile.tileid).delete()
        return requirement

    def set_requirement_status(self, requirement_id, satisfied):
        """Set a requirement's assessment status (satisfied yes/no), creating the
        assessment tile if it has none. A partial save, so only the assessment
        nodegroup is touched."""
        requirement = self._get_requirement_by_id(requirement_id)
        assessment = requirement.aliased_data.sub_requirement_assessment_n1
        if assessment is None:
            assessment = self.append_blank_tile_for_group(
                requirement,
                groups.SUB_REQUIREMENT_ASSESSMENT_N1,
                {aliases.REQUIREMENT_STATUS: satisfied},
            )
        else:
            assessment.aliased_data.requirement_status = satisfied
        requirement.save(force_admin=True, partial=True, index=False)
        return requirement

    def clone_requirement(self, template_id, parent=None, submission=None):
        """A working copy of the requirement template with the given pk: every
        tile copied with a fresh GUID and the template flag cleared, so the copy
        is a real, editable requirement rather than another template.

        The grouping parent and submission host are linked in the same write, so
        a cloned-and-attached requirement costs one insert rather than a clone
        followed by a full re-save."""
        source = Resource.objects.get(pk=template_id)
        source.load_tiles()
        copy = self.copy_resource(source)
        self._clear_template_flag(copy)
        reference_tiles = self._write_link_references(copy, parent, submission)
        with transaction.atomic():
            super(Resource, copy).save()
            Tile.objects.bulk_create(copy.tiles)
            # bulk_create skips the datatype hooks, so run the resource-instance
            for tile, reference_node in reference_tiles:
                self._reference_datatype.post_tile_save(tile, reference_node, None)
        # Baseline descriptor so the copy is never descriptor-less when a
        # permit compiles its display; the clone hook re-saves it with the link.
        copy.save_descriptors()
        return copy

    @cached_property
    def _reference_datatype(self):
        return DataTypeFactory().get_instance("resource-instance")

    @staticmethod
    def _resource_reference(resource_id):
        """Tile data for a resource-instance node pointing at one resource, in the
        shape arches stores it. post_tile_save fills in the relationship id."""
        return [
            {
                "resourceId": str(resource_id),
                "ontologyProperty": "",
                "inverseOntologyProperty": "",
            }
        ]

    def _write_link_references(self, copy, parent, submission):
        """Set the grouping-parent and submission references directly in a cloned
        copy's tiles before it is persisted. parent_module lives on the existing
        is_template_requirement tile; the submission gets a fresh submission_data
        tile under requirement_data. Returns the (tile, node id) pairs whose
        resource_x_resource rows still need creating after the insert."""
        reference_tiles = []
        if parent is not None:
            parent_node = node_id(GraphSlugs.PROCESS_REQUIREMENT, aliases.PARENT_MODULE)
            parent_group = nodegroup_id(
                GraphSlugs.PROCESS_REQUIREMENT, aliases.PARENT_MODULE
            )
            tile = self._existing_tile(copy, parent_group)
            tile.data[parent_node] = self._resource_reference(parent.pk)
            reference_tiles.append((tile, parent_node))
        if submission is not None:
            # submission_data is its own single-node group, so the node id doubles
            # as the nodegroup id and the tile-data key.
            submission_node = node_id(
                GraphSlugs.PROCESS_REQUIREMENT, aliases.SUBMISSION_DATA
            )
            submission_tile = self._existing_tile(copy, submission_node)
            if submission_tile is None:
                data_group = nodegroup_id(
                    GraphSlugs.PROCESS_REQUIREMENT, groups.REQUIREMENT_DATA
                )
                submission_tile = Tile(
                    nodegroup_id=submission_node,
                    parenttile=self._existing_tile(copy, data_group),
                    resourceinstance=copy,
                    sortorder=0,
                )
                submission_tile.tiles = []
                copy.tiles.append(submission_tile)
            submission_tile.data[submission_node] = self._resource_reference(
                submission.pk
            )
            reference_tiles.append((submission_tile, submission_node))
        return reference_tiles

    @staticmethod
    def _existing_tile(resource, nodegroup):
        """The cloned copy's tile for a nodegroup id, or None if it has none."""
        return next(
            (t for t in resource.tiles if str(t.nodegroup_id) == nodegroup), None
        )

    def templates_by_id(self):
        """The is_template_requirement templates, keyed by their requirement id."""
        templates = self._requirements(id_only=True).filter(
            is_template_requirement=True
        )
        return {self._requirement_identification(t): t for t in templates}

    def link(self, requirement_id, parent=None, submission=None):
        """Link a cloned requirement to its grouping parent and/or submission host
        in one fetch and save."""
        requirement = self._get_requirement_by_id(requirement_id)
        self._apply_link(requirement, parent, submission)
        requirement.save(**self.save_kwargs)

    def _apply_link(self, requirement, parent, submission):
        """Set the grouping parent and submission host on an already-fetched
        requirement, without saving. parent_module lives on the
        is_template_requirement tile; the submission reuses the cardinality-1
        requirement_data tile, adding its submission_data sub-tile only when
        missing."""
        if parent is not None:
            identification = (
                requirement.aliased_data.requirement_identification.aliased_data
            )
            identification.is_template_requirement.aliased_data.parent_module = parent
        if submission is not None:
            data = requirement.aliased_data.requirement_data
            if data is None:
                data = self.append_blank_tile_for_group(
                    requirement, groups.REQUIREMENT_DATA, {}
                )
            if data.aliased_data.submission_data is None:
                self.append_blank_tile_for_group(data, aliases.SUBMISSION_DATA, {})
            submission_tile = data.aliased_data.submission_data.aliased_data
            submission_tile.submission_data = submission

    def _clear_template_flag(self, resource):
        nodeid = node_id(
            GraphSlugs.PROCESS_REQUIREMENT, aliases.IS_TEMPLATE_REQUIREMENT
        )
        self.set_node_value(resource, nodeid, False)

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

    def _requirements(self, id_only=False):
        """The aliased process_requirement tile-tree queryset. With id_only,
        hydrate just the identification and template-flag nodes, enough to key or
        filter templates without loading (and dereferencing) the rest of each
        requirement's tree."""
        nodes = None
        if id_only:
            nodes = BaseGraphService.nodes(
                GraphSlugs.PROCESS_REQUIREMENT,
                [aliases.REQUIREMENT_IDENTIFICATION, aliases.IS_TEMPLATE_REQUIREMENT],
            )
        return ResourceTileTree.get_tiles(GraphSlugs.PROCESS_REQUIREMENT, nodes=nodes)

    def _get_requirement_by_id(self, pk):
        """The requirement as an aliased tile tree, fetched by pk, for editing."""
        return self._requirements(id_only=True).get(pk=pk)

    def _requirement_identification(self, requirement):
        """The requirement's business identification (the REQ- string on its
        identification tile), which is what templates are keyed by, not its pk."""
        identification = (
            requirement.aliased_data.requirement_identification.aliased_data
        )
        return localized_string(identification.requirement_identification)
