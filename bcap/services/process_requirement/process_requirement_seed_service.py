"""Seed a permit type's process requirements onto a permit application.

Create a grouping parent (left unattached) and the four child requirements
below, link each child to a fresh module resource where the spec calls for one,
and attach the children to the permit in flow order. Built fresh for now;
eventually clones of the Process Requirement templates.

"Type" is the process_requirment_type value; "Module" is the resource linked
through submission_data ({type} is the permit type's own model, "-" links
nothing). Who sets is_internal_requirement: Permitting Arch internal, else not.

    Name                        Who              Type                 Module
    Document {label} Approach   Proponent        Workflow             {type}
    Review {label} Approach     Permitting Arch  Checklist            -
    Submit {label} Outcome      Proponent        Document Submission  Requirement Submission
    Review {label} Outcome      Permitting Arch  Checklist            -
"""

from dataclasses import dataclass

from django.utils import timezone

from arches.app.models.resource import Resource
from arches_querysets.models import ResourceTileTree

from bcap.util.aliases.permit_application import (
    PermitApplicationAliases as pa,
    PermitApplicationGroupAliases as pa_groups,
)
from bcap.util.aliases.process_requirement import (
    ProcessRequirementAliases as aliases,
    ProcessRequirementGroupAliases as groups,
)
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.dashboard.resource_builder import ResourceBuilder

# Route segment -> human label used in the requirement names.
PERMIT_TYPES = {
    GraphSlugs.INSPECTION: "Inspection",
    GraphSlugs.INVESTIGATION: "Investigation",
    GraphSlugs.ALTERATION: "Alteration",
}

# Sentinel in the spec: link to the permit type's own resource model.
_TYPE_RESOURCE = "<permit-type>"


@dataclass(frozen=True)
class _ReqSpec:
    name: str  # {label} resolves to the permit type's human name
    internal: bool  # Permitting Arch is internal, Proponent is not
    type_label: str  # process_requirment_type controlled-list value
    module: str  # graph slug to create and link, _TYPE_RESOURCE, or "" for none


_REQUIREMENTS = [
    _ReqSpec("Document {label} Approach", False, "Workflow", _TYPE_RESOURCE),
    _ReqSpec("Review {label} Approach", True, "Checklist", ""),
    _ReqSpec(
        "Submit {label} Outcome",
        False,
        "Document Submission",
        GraphSlugs.REQUIREMENT_SUBMISSION,
    ),
    _ReqSpec("Review {label} Outcome", True, "Checklist", ""),
]


class _RealResourceBuilder(ResourceBuilder):
    """Builder for real route data: don't tag with the seed legacyid, so
    clear_dashboard_data never deletes these."""

    _TAG_AS_SEED = False


class ProcessRequirementSeedService:
    """Create the per-type process requirements and attach them to a permit."""

    def __init__(self, user=None):
        self.builder = _RealResourceBuilder(skip_refresh=True, owner=user)

    def seed(self, permit_id, permit_type):
        """Create the parent and four requirements for the type, link their
        modules, and attach the four to the permit. Returns the created
        resources."""
        label = PERMIT_TYPES[permit_type]
        parent = self._make_requirement(
            f"{label} Requirements", internal=True, type_label="Grouping"
        )
        requirements = [
            self._make_requirement(
                spec.name.format(label=label),
                internal=spec.internal,
                type_label=spec.type_label,
                parent=parent,
                module_slug=self._module_slug(spec.module, permit_type),
            )
            for spec in _REQUIREMENTS
        ]
        self._attach_to_permit(permit_id, requirements)
        return {"parent": parent, "requirements": requirements}

    @staticmethod
    def _module_slug(module, permit_type):
        if not module:
            return None
        return permit_type if module == _TYPE_RESOURCE else module

    def _make_requirement(
        self, name, *, internal, type_label, parent=None, module_slug=None
    ):
        """Build and save one process requirement, linking a parent and module
        resource when given."""
        requirement = self.builder.new_resource(GraphSlugs.PROCESS_REQUIREMENT)
        identification = self.builder.append_blank_tile_for_group(
            requirement,
            aliases.REQUIREMENT_IDENTIFICATION,
            {
                aliases.REQUIREMENT_IDENTIFICATION: self.builder.localized(name),
                aliases.REQUIREMENT_NAME: self.builder.localized(name),
            },
        )
        # is_template_requirement is a cardinality-1 child auto-created blank with
        # the identification tile; set the flags and required type on it.
        template = identification.aliased_data.is_template_requirement.aliased_data
        template.is_template_requirement = False
        template.is_internal_requirement = internal
        template.process_requirment_type = self.builder.reference_value(
            GraphSlugs.PROCESS_REQUIREMENT,
            aliases.PROCESS_REQUIRMENT_TYPE,
            label=type_label,
        )
        if parent is not None:
            self.builder.append_blank_tile_for_group(
                requirement,
                aliases.PARENT_REQUIREMENT,
                {aliases.PARENT_REQUIREMENT: parent},
            )
        if module_slug is not None:
            self._link_module(requirement, module_slug)
        requirement.save(**self.builder.save_kwargs)
        self.builder.claim(requirement)
        return requirement

    def _link_module(self, requirement, slug):
        """Create an empty module resource and point submission_data at it."""
        module = self._make_module(slug)
        data = self.builder.append_blank_tile_for_group(
            requirement, groups.REQUIREMENT_DATA, {}
        )
        # requirement_data auto-creates blank children: a cardinality-n checklist
        # row that would fail its required fields (drop it) and the cardinality-1
        # submission_data tile (set its value).
        data.aliased_data.sub_requirement_n1 = []
        data.aliased_data.submission_data.aliased_data.submission_data = module

    def _make_module(self, slug):
        """An empty resource of the module graph, owned by the caller. The
        proponent fills it in later."""
        module = Resource(
            graph_id=self.builder.graph_id(slug),
            resource_instance_lifecycle_state=self.builder.state,
            createdtime=timezone.now(),
            principaluser=self.builder.owner,
        )
        module.save(user=self.builder.owner, index=False)
        return module

    def _attach_to_permit(self, permit_id, requirements):
        """Link the requirements to the permit's application_admin group in flow
        order, after any already attached."""
        permit = ResourceTileTree.get_tiles(GraphSlugs.PERMIT_APPLICATION).get(
            pk=permit_id
        )
        admin = permit.aliased_data.application_admin
        if admin is None:
            permit.append_tile(pa_groups.APPLICATION_ADMIN)
            admin = permit.aliased_data.application_admin
        # process_requirement is a cardinality-n child; appending its parent
        # auto-creates one blank row. Reuse a trailing blank before appending,
        # and number after the children that already point at a requirement.
        children = admin.aliased_data.process_requirement or []
        filled = [c for c in children if c.aliased_data.process_requirement]
        for offset, requirement in enumerate(requirements):
            index = len(filled) + offset
            if index < len(children):
                child = children[index]
            else:
                admin.append_tile(pa.PROCESS_REQUIREMENT)
                child = admin.aliased_data.process_requirement[-1]
            child.aliased_data.process_requirement = requirement
            child.aliased_data.process_requirement_order = index + 1
        permit.save(force_admin=True, partial=True, index=False)
