"""Process-requirement service.

Orchestrates process-requirement work for a permit: cloning the seeded templates
into editable working copies and attaching them to a permit in flow order. The
graph mechanics (build, clone, submission and parent linking) live in
ProcessRequirementBuilder; this layer decides what to clone and where it goes."""

from collections import defaultdict

from arches.app.models.models import TileModel

from arches_querysets.models import ResourceTileTree

from bcap.util.aliases.permit_application import (
    PermitApplicationAliases as pa,
    PermitApplicationGroupAliases as pa_groups,
)
from bcap.util.aliases.process_requirement import ProcessRequirementAliases as prq
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.graph import node_id
from bcap.util.indexing import bulk_index
from bcap.builders.process_requirement_builder import ProcessRequirementBuilder
from bcap.services.process_requirement.template_specs import host_graph, load


class ProcessRequirementService:
    """Clone the seeded templates into independent working copies and attach them
    to a permit; the frontend fills in their values afterward."""

    # The default module every permit application gets (the grouping parent plus
    # Recommend Referral, Recommend Decision, Decision Summary).
    _DEFAULT_MODULE = "permit"

    def __init__(self, user=None):
        self._user = user
        self._builder = None

    @property
    def builder(self):
        """Built lazily so the read-only reference lookups skip the builder's
        setup queries (lifecycle state and the admin user)."""
        if self._builder is None:
            self._builder = ProcessRequirementBuilder(
                skip_refresh=True, owner=self._user, tag_as_seed=False
            )
        return self._builder

    def create_working_copies(self):
        """The default module's grouping parent and child working copies, in flow
        order; the caller attaches the children and cleans them up on a rejection."""
        return self._clone_module(self._DEFAULT_MODULE)

    def attach_requirements(self, permit_id, permit_type, host=None):
        """Clone the permit type's module and attach its requirements (not the
        grouping parent) to the permit in flow order; returns the child copies."""
        parent, requirements = self._clone_module(permit_type, host)
        self._attach_to_permit(permit_id, requirements)
        created = [parent, *requirements]
        # Re-save descriptors now the permit link exists, so a requirement's
        # descriptor resolves the application id instead of showing "(Unknown)".
        for requirement in created:
            requirement.save_descriptors()
        bulk_index(created)
        return requirements

    def permit_module_hosts(self, permit_id, permit_type):
        """The host resources of the permit type's module attached to the permit,
        read straight from tile data (faster and null-descriptor safe)."""
        host_slug = host_graph(permit_type)
        if not host_slug:
            return []
        requirement_ids = self.requirement_ids_by_permit([permit_id]).get(
            str(permit_id), set()
        )
        host_ids = set().union(*self.host_ids_by_requirement(requirement_ids).values())
        if not host_ids:
            return []
        # Loading by the host graph drops any submission ids of other graphs.
        return ResourceTileTree.get_tiles(host_slug, resource_ids=list(host_ids))

    def requirement_ids_by_permit(self, permit_ids):
        """Each permit id mapped to the process requirement ids attached to it."""
        return self._references_by_source(
            permit_ids, node_id(GraphSlugs.PERMIT_APPLICATION, pa.PROCESS_REQUIREMENT)
        )

    def host_ids_by_requirement(self, requirement_ids):
        """Each requirement id mapped to the submission host resource ids its
        submission child references."""
        return self._references_by_source(
            requirement_ids,
            node_id(GraphSlugs.PROCESS_REQUIREMENT, prq.SUBMISSION_DATA),
        )

    @staticmethod
    def _references_by_source(source_ids, nodeid):
        """Map each source resource id to the resource ids it references through a
        resource-instance node, read from raw tile data."""
        grouped = defaultdict(set)
        tiles = TileModel.objects.filter(
            resourceinstance_id__in=list(source_ids), data__has_key=nodeid
        )
        for tile in tiles:
            references = tile.data.get(nodeid) or []
            resource_ids = (
                ref["resourceId"] for ref in references if ref.get("resourceId")
            )
            grouped[str(tile.resourceinstance_id)].update(resource_ids)
        return grouped

    def _clone_module(self, permit_type, host=None):
        """Clone the module's grouping parent and child requirements, linking each
        child to the parent and to its submission resource (the host or a fresh one)."""
        parent_spec = load(permit_type)
        templates = self.builder.templates_by_id()
        parent = self.builder.clone_requirement(templates[parent_spec["id"]].pk)
        requirements = []
        for child in parent_spec["requirements"]:
            requirement = self.builder.clone_requirement(templates[child["id"]].pk)
            self.builder.link_parent(requirement.pk, parent)
            if child["resource"]:
                submission = (
                    host
                    if child["resource"] == permit_type
                    else self.builder.make_resource(child["resource"])
                )
                self.builder.link_submission(requirement.pk, submission)
            requirements.append(requirement)
        return parent, requirements

    def clone_by_id(self, template_id):
        return self.builder.clone_requirement(template_id)

    def _templates_by_id(self):
        return self.builder.templates_by_id()

    def _attach_to_permit(self, permit_id, requirements):
        """Link the requirements to the permit's application_admin group in flow
        order, after any already attached."""
        permit = ResourceTileTree.get_tiles(GraphSlugs.PERMIT_APPLICATION).get(
            pk=permit_id
        )
        if permit.aliased_data.application_admin is None:
            permit.append_tile(pa_groups.APPLICATION_ADMIN)
        admin = permit.aliased_data.application_admin
        # Drop the blank row append_tile auto-creates, keeping only the already
        # attached requirements, then append the new ones after them.
        children = admin.aliased_data.process_requirement or []
        filled = [c for c in children if c.aliased_data.process_requirement]
        admin.aliased_data.process_requirement = filled
        for order, requirement in enumerate(requirements, start=len(filled) + 1):
            self.builder.append_blank_tile_for_group(
                admin,
                pa.PROCESS_REQUIREMENT,
                {
                    pa.PROCESS_REQUIREMENT: requirement,
                    pa.PROCESS_REQUIREMENT_ORDER: order,
                },
            )
        permit.save(force_admin=True, partial=True, index=False)
