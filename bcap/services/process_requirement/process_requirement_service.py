"""Process-requirement service.

Orchestrates process-requirement work for a permit: cloning the seeded templates
into editable working copies and attaching them to a permit in flow order. The
graph mechanics (build, clone, submission and parent linking) live in
ProcessRequirementBuilder; this layer decides what to clone and where it goes."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from arches.app.models.models import ResourceInstance, TileModel
from arches.app.models.resource import Resource
from arches.app.models.tile import Tile

from arches_querysets.models import ResourceTileTree

from bcap.util.aliases.permit_application import (
    PermitApplicationAliases as pa,
    PermitApplicationGroupAliases as pa_groups,
)
from bcap.util.aliases.process_requirement import ProcessRequirementAliases as prq
from bcap.util.bcap_aliases import GraphSlugs, RESOURCE_ID
from bcap.util.graph import node_id
from bcap.util.indexing import bulk_index
from bcap.util.tiles import referenced_resource_ids, references_by_source
from bcap.builders.process_requirement_builder import ProcessRequirementBuilder
from bcap.util.save import acting_request
from bcap.services.dashboard.base_graph_service import BaseGraphService
from bcap.services.process_requirement.template_specs import (
    host_graph,
    load,
    module_graph,
)


@dataclass
class ClonedModule:
    """A cloned module ready to attach to a permit: its grouping parent resource,
    the child working copies in flow order, and the module name. The unique module
    id and each requirement id are filled in by the assign-module-ids save hook."""

    parent: object
    requirements: list
    name: str
    # The child whose submission is the module's own resource. For the permit
    # module that resource is the permit application itself, which doesn't exist
    # yet at create time, so the caller links it once the permit is saved.
    self_hosted: object = None


class ProcessRequirementService:
    """Clone the seeded templates into independent working copies and attach them
    to a permit; the frontend fills in their values afterward."""

    # The default module every permit application gets (the grouping parent plus
    # Recommend Referral, Recommend Decision, Decision Summary).
    _DEFAULT_MODULE = "permit"

    # The application_admin module tree: the only leaves attaching or adding a
    # module reads or writes. Loading just these keeps the permit fetch and its
    # partial save off every other nodegroup (module_id is minted by the save
    # hook; a partial save leaves the unloaded nodes untouched).
    _ADMIN_NODES = [
        pa.MODULE_NAME,
        pa.MODULE_ORDER,
        pa.PROCESS_REQUIREMENT,
        pa.PROCESS_REQUIREMENT_ORDER,
    ]

    def __init__(self, request=None):
        self._request = request
        self._save_as = {"request": acting_request(request)}
        self._builder = None

    @property
    def builder(self):
        """Built lazily so the read-only reference lookups skip the builder's
        setup queries (lifecycle state and the admin user)."""
        if self._builder is None:
            self._builder = ProcessRequirementBuilder(
                skip_refresh=True, tag_as_seed=False, request=self._request
            )
        return self._builder

    def create_working_copies(self):
        """The default module, cloned for the caller to wrap in a process_module
        tile."""
        return self._clone_module(self._DEFAULT_MODULE)

    def attach_requirements(self, permit_id, permit_type, host=None):
        """Clone the permit type's module and attach its requirements to the permit
        as a new process_module, in flow order; returns the child copies."""
        cloned = self._clone_module(permit_type, host)
        self._attach_to_permit(permit_id, cloned)
        created = [cloned.parent, *cloned.requirements]
        # Re-save descriptors now the permit link exists, so a requirement's
        # descriptor resolves the application id instead of showing "(Unknown)".
        for requirement in created:
            requirement.save_descriptors()
        bulk_index(created)
        return cloned.requirements

    def remove_module(self, permit_id, module_tileid):
        """Drop a module's process_module tile and delete the requirement working
        copies it created (grouping parent, children, hosts)."""
        if not self._module_belongs_to_permit(permit_id, module_tileid):
            return

        reference_node = node_id(GraphSlugs.PERMIT_APPLICATION, pa.PROCESS_REQUIREMENT)
        requirement_ids = referenced_resource_ids(
            TileModel.objects.filter(parenttile_id=module_tileid), reference_node
        )
        parent_node = node_id(GraphSlugs.PROCESS_REQUIREMENT, prq.PARENT_MODULE)
        to_delete = set(requirement_ids)
        # The children's grouping parent and submission hosts follow the same
        # requirement -> resource reference shape, one node id each.
        for grouped in (
            references_by_source(requirement_ids, parent_node),
            self.host_ids_by_requirement(requirement_ids),
        ):
            for ids in grouped.values():
                to_delete.update(ids)

        # The permit module hosts its own submission on the permit, which must
        # outlive the module.
        to_delete.discard(str(permit_id))
        Tile.objects.get(pk=module_tileid).delete()
        self._delete_resources(to_delete)

    def reorder_requirements(self, permit_id, module_tileid, ordered_requirement_ids):
        """Renumber a module's process requirements to match the given order of
        requirement ids, updating each child tile's order node and sortorder."""
        if not self._module_belongs_to_permit(permit_id, module_tileid):
            return
        reference_node = node_id(GraphSlugs.PERMIT_APPLICATION, pa.PROCESS_REQUIREMENT)
        order_node = node_id(
            GraphSlugs.PERMIT_APPLICATION, pa.PROCESS_REQUIREMENT_ORDER
        )
        position = {str(rid): i + 1 for i, rid in enumerate(ordered_requirement_ids)}
        for child in TileModel.objects.filter(parenttile_id=module_tileid):
            referenced = referenced_resource_ids([child], reference_node)
            order = next((position[r] for r in referenced if r in position), None)
            if order is None:
                continue
            child.data[order_node] = order
            child.sortorder = order
            child.save(update_fields=["data", "sortorder"])

    def remove_requirement(self, permit_id, module_tileid, requirement_id):
        """Delete one process requirement from a module: its child tile plus the
        requirement resource and submission host. The module's grouping parent is
        shared by the other requirements, so it is left in place."""
        child = self._module_child_tile(permit_id, module_tileid, requirement_id)
        if child is None:
            return
        to_delete = {str(requirement_id)}
        for hosts in self.host_ids_by_requirement({str(requirement_id)}).values():
            to_delete.update(hosts)
        to_delete.discard(str(permit_id))
        Tile.objects.get(pk=child.pk).delete()
        self._delete_resources(to_delete)

    def set_ministry_assignee(
        self, permit_id, module_tileid, requirement_id, contributor_id
    ):
        """Point a module requirement's ministry_assignee at a Contributor, or
        clear it with None. Returns False for a requirement that isn't on the
        module. The save writes the edit log the dashboard reads the assignment
        date from."""
        permit = self._load_application_admin(
            permit_id, [pa.PROCESS_REQUIREMENT, pa.MINISTRY_ASSIGNEE]
        )
        module = self._module_by_tileid(
            permit.aliased_data.application_admin, module_tileid
        )
        child = self._requirement_child(module, requirement_id)
        if child is None:
            return False
        child.aliased_data.ministry_assignee = (
            str(contributor_id) if contributor_id else None
        )
        permit.save(**self._save_as, partial=True)
        return True

    def add_blank_requirement(self, permit_id, module_tileid, name="New requirement"):
        """Create a blank process requirement and attach it to the module after
        the existing ones. Returns the new requirement, or None for an unknown
        module."""
        permit = self._load_application_admin(permit_id)
        module = self._module_by_tileid(
            permit.aliased_data.application_admin, module_tileid
        )
        if module is None:
            return None
        requirement = self.builder.make_blank_checklist_requirement(name)
        order = len(module.aliased_data.process_requirement or []) + 1
        self.builder.append_blank_tile_for_group(
            module,
            pa.PROCESS_REQUIREMENT,
            {
                pa.PROCESS_REQUIREMENT: requirement,
                pa.PROCESS_REQUIREMENT_ORDER: order,
            },
        )
        permit.save(**self._save_as, partial=True, index=False)
        # make_process_requirement returns a tile tree; descriptors and indexing
        # live on the Resource proxy.
        resource = Resource.objects.get(pk=requirement.pk)
        resource.save_descriptors()
        bulk_index([resource])
        return requirement

    def save_checklist(self, requirement_id, name, steps):
        """Save a requirement's name and checklist steps (create/update/delete/
        reorder reconciled server-side), then index."""
        requirement = self.builder.update_checklist(requirement_id, name, steps)
        bulk_index([Resource.objects.get(pk=requirement.pk)])
        return requirement

    def set_requirement_status(self, requirement_id, satisfied):
        """Mark a requirement satisfied/unsatisfied on its assessment tile, then
        index."""
        requirement = self.builder.set_requirement_status(requirement_id, satisfied)
        bulk_index([Resource.objects.get(pk=requirement.pk)])
        return requirement

    def set_module_completed(self, permit_id, module_tileid, completed):
        """Flip a module's completion flag and stamp (or clear) its completed
        date on the process_module tile directly, leaving the module's other card
        nodes (order, name, id) untouched. Returns False for a stray module id
        that isn't one of the permit's."""
        if not self._module_belongs_to_permit(permit_id, module_tileid):
            return False
        completed_node = node_id(GraphSlugs.PERMIT_APPLICATION, pa.IS_MODULE_COMPLETED)
        date_node = node_id(GraphSlugs.PERMIT_APPLICATION, pa.MODULE_COMPLETED_DATE)
        tile = TileModel.objects.get(pk=module_tileid)
        tile.data[completed_node] = completed
        tile.data[date_node] = date.today().isoformat() if completed else None
        tile.save(update_fields=["data"])
        bulk_index([Resource.objects.get(pk=permit_id)])
        return True

    @staticmethod
    def _requirement_child(module, requirement_id):
        """The module's child tile referencing this requirement, in a loaded
        module tree, or None."""
        for child in (module and module.aliased_data.process_requirement) or []:
            referenced = child.aliased_data.process_requirement
            if referenced and str(referenced.pk) == str(requirement_id):
                return child
        return None

    @staticmethod
    def _module_child_tile(permit_id, module_tileid, requirement_id):
        """The module's child tile referencing this requirement, or None."""
        reference_node = node_id(GraphSlugs.PERMIT_APPLICATION, pa.PROCESS_REQUIREMENT)
        return TileModel.objects.filter(
            parenttile_id=module_tileid,
            resourceinstance_id=permit_id,
            data__contains={reference_node: [{RESOURCE_ID: str(requirement_id)}]},
        ).first()

    @staticmethod
    def _module_belongs_to_permit(permit_id, module_tileid):
        """Whether the process_module tile is one of this permit's, so a stray id
        can't reach into another application's module."""
        return TileModel.objects.filter(
            pk=module_tileid, resourceinstance_id=permit_id
        ).exists()

    @staticmethod
    def _module_by_tileid(admin, module_tileid):
        """The process_module tile under application_admin with this tile id, or
        None (including when the permit has no application_admin yet)."""
        modules = (admin and admin.aliased_data.process_module) or []
        return next((m for m in modules if str(m.tileid) == str(module_tileid)), None)

    @staticmethod
    def _delete_resources(resource_ids):
        """Delete resources one at a time so each de-indexes and cascades its tiles
        (a bulk queryset delete would skip that)."""
        for resource in Resource.objects.filter(pk__in=list(resource_ids)):
            resource.delete()

    def permit_module_tiles(self, permit_id, permit_type):
        """The host resources of the permit type's module attached to the permit,
        read straight from tile data (faster and null-descriptor safe)."""
        host_slug = host_graph(permit_type)
        if not host_slug:
            return []
        requirement_ids = self.requirement_ids_by_permit([permit_id]).get(
            str(permit_id), set()
        )
        host_ids = set().union(*self.host_ids_by_requirement(requirement_ids).values())
        host_ids = list(
            ResourceInstance.objects.filter(
                pk__in=host_ids, graph__slug=host_slug
            ).values_list("pk", flat=True)
        )
        if not host_ids:
            return []
        return ResourceTileTree.get_tiles(host_slug, resource_ids=host_ids)

    def requirement_ids_by_permit(self, permit_ids):
        """Each permit id mapped to the process requirement ids attached to it."""
        return references_by_source(
            permit_ids, node_id(GraphSlugs.PERMIT_APPLICATION, pa.PROCESS_REQUIREMENT)
        )

    def host_ids_by_requirement(self, requirement_ids):
        """Each requirement id mapped to the submission host resource ids its
        submission child references."""
        return references_by_source(
            requirement_ids,
            node_id(GraphSlugs.PROCESS_REQUIREMENT, prq.SUBMISSION_DATA),
        )

    def module_message_contexts(self, permit_id: str):
        """Each process_module tile mapped to the resource its messages file
        against: its first requirement's submission host in flow order, or the
        permit itself when it has none. Matches the message dialog."""
        node = node_id(GraphSlugs.PERMIT_APPLICATION, pa.PROCESS_REQUIREMENT)
        requirements = defaultdict(list)
        all_ids = set()
        for child in TileModel.objects.filter(
            resourceinstance_id=permit_id,
            parenttile__isnull=False,
            data__has_key=node,
        ).order_by("sortorder"):
            ids = referenced_resource_ids([child], node)
            requirements[str(child.parenttile_id)] += ids
            all_ids |= ids
        hosts = self.host_ids_by_requirement(all_ids)
        return self._module_hosts(requirements, hosts, default=permit_id)

    @staticmethod
    def _module_hosts(requirements, hosts, default):
        """Each module mapped to its first requirement's submission host in flow
        order, or the default when none of its requirements has one."""
        module_hosts = {}
        for module, requirement_ids in requirements.items():
            host = default
            for rid in requirement_ids:
                if hosts.get(rid):
                    host = next(iter(hosts[rid]))
                    break
            module_hosts[module] = host
        return module_hosts

    def _clone_module(self, permit_type, host=None):
        """Clone the module's grouping parent and child requirements, linking each
        child to the parent and to its submission resource (the host or a fresh
        one) as it is cloned. The module and requirement ids are stamped later by
        the save hook."""
        parent_spec = load(permit_type)
        graph = module_graph(permit_type)
        templates = self.builder.templates_by_id()
        parent = self.builder.clone_requirement(templates[parent_spec["id"]].pk)
        requirements = []
        self_hosted = None
        for child in parent_spec["requirements"]:
            submission = None
            own_submission = child["resource"] == graph
            if own_submission:
                submission = host
            elif child["resource"]:
                submission = self.builder.make_resource(child["resource"])
            requirement = self.builder.clone_requirement(
                templates[child["id"]].pk, parent=parent, submission=submission
            )
            if own_submission and submission is None:
                self_hosted = requirement
            requirements.append(requirement)
        return ClonedModule(parent, requirements, parent_spec["name"], self_hosted)

    def link_submission(self, requirement_id, resource_id):
        """Point a requirement's submission host at a resource that already
        exists (the permit application links its own module this way)."""
        self.builder.link(
            requirement_id, submission=Resource.objects.get(pk=resource_id)
        )

    def clone_by_id(self, template_id):
        return self.builder.clone_requirement(template_id)

    def _templates_by_id(self):
        return self.builder.templates_by_id()

    def _attach_to_permit(self, permit_id, cloned):
        """Attach the cloned module's requirements as a new process_module under
        application_admin, after any modules already there. The module id and the
        requirement ids are filled in by the assign-module-ids save hook."""
        permit = self._load_application_admin(permit_id)
        admin = permit.aliased_data.application_admin
        # Keep only real modules, then append the new one after them.
        self.builder.prune_blank_tiles(admin, pa_groups.PROCESS_MODULE, pa.MODULE_NAME)
        module_order = len(admin.aliased_data.process_module or []) + 1
        module = self.builder.append_blank_tile_for_group(
            admin,
            pa_groups.PROCESS_MODULE,
            {
                pa.MODULE_NAME: self.builder.localized(cloned.name),
                pa.MODULE_ORDER: module_order,
            },
        )
        self.builder.prune_blank_tiles(module, pa.PROCESS_REQUIREMENT)
        for order, requirement in enumerate(cloned.requirements, start=1):
            self.builder.append_blank_tile_for_group(
                module,
                pa.PROCESS_REQUIREMENT,
                {
                    pa.PROCESS_REQUIREMENT: requirement,
                    pa.PROCESS_REQUIREMENT_ORDER: order,
                },
            )
        permit.save(**self._save_as, partial=True, index=False)

    def _load_application_admin(self, permit_id, nodes=None):
        """The permit hydrated with only its application_admin module tree, its
        admin tile created when the permit has none yet. Restricting the load
        keeps both the fetch and the partial save off every other nodegroup,
        while a resource-level save still takes the cheap targeted-refresh path
        (a tile-scoped save would re-fetch the whole nodegroup afterward)."""
        permit = ResourceTileTree.get_tiles(
            GraphSlugs.PERMIT_APPLICATION,
            nodes=BaseGraphService.nodes(
                GraphSlugs.PERMIT_APPLICATION, nodes or self._ADMIN_NODES
            ),
        ).get(pk=permit_id)
        if permit.aliased_data.application_admin is None:
            permit.append_tile(pa_groups.APPLICATION_ADMIN)
        return permit
