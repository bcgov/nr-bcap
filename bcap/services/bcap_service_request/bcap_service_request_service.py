"""Create- and submission-time transforms for a BCAP service request: seed the
service request id on create, and attach the requirement working copies whenever
a create or update sets the submission date."""

from collections import defaultdict
from itertools import chain

from arches.app.models.models import ResourceInstance
from arches_querysets.models import ResourceTileTree

from bcap.permissions.groups import is_internal_user
from bcap.permissions.permit_access import PermitAccess
from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)
from bcap.util.aliases.bcap_service_request import (
    BcapServiceRequestAliases as aliases,
    BcapServiceRequestGroupAliases as group_aliases,
)
from bcap.util.bcap_aliases import ALIASED_DATA, GraphSlugs
from bcap.util.reference_number import allocate_reference_number
from bcap.util.tiles import group_data
from bcap.util.indexing import bulk_index

# Map each service_request_type controlled-list label to the process-requirement
# module that should be seeded when the service request is first submitted.
_MODULE_FOR_REQUEST_TYPE = {
    "Start a New Project (Permit)": "permit",
    "Submit a Site Visit": "site_visit",
    "Ask a question": "information_request",
    "Request Information about a property, area, or site": "information_request",
    "Submit a non-Project report": "document_submission",
}


class BcapServiceRequestService:
    """Assigns the id and attaches requirements on first submission."""

    @staticmethod
    def base_query(user, resource_ids=None):
        """Every service request for branch staff; for everyone else the ones
        they filed themselves."""
        queryset = ResourceTileTree.get_tiles(
            GraphSlugs.BCAP_SERVICE_REQUEST,
            resource_ids=resource_ids,
            as_representation=True,
        ).select_related("graph", "resource_instance_lifecycle_state")
        if is_internal_user(user):
            return queryset
        return queryset.filter(createdby=user)

    def __init__(self, request=None, requirement_service=None):
        # Passed through so requirement saves log the acting user.
        self._requirements = requirement_service or ProcessRequirementService(request)

    def submission_context_ids_for_service_requests(
        self, service_requests, requirements_by_service_request=None
    ):
        """Map each service request to the resource ids its unresolved counts
        span, two levels deep:

          SR → requirements → hosts (PA, Document Submission, ...)
          PA hosts → PA requirements → hosts (Investigation, ...)

        Pass known requirement ids to skip the first-level query."""
        service_request_ids = [str(sr.pk) for sr in service_requests]
        contexts = {pk: {pk} for pk in service_request_ids}

        if requirements_by_service_request is None:
            requirements_by_service_request = (
                self._requirements.requirement_ids_by_permit(
                    service_request_ids,
                    graph_slug=GraphSlugs.BCAP_SERVICE_REQUEST,
                )
            )
        all_requirement_ids = set(
            chain.from_iterable(requirements_by_service_request.values())
        )
        hosts_by_requirement = self._requirements.host_ids_by_requirement(
            all_requirement_ids
        )

        # Level 1: SR → requirements → submission hosts (PA, Doc Submission, etc.)
        all_host_ids = set()
        for sr_id, requirement_ids in requirements_by_service_request.items():
            for requirement_id in requirement_ids:
                contexts[sr_id].add(str(requirement_id))
                for host_id in hosts_by_requirement.get(str(requirement_id), ()):
                    contexts[sr_id].add(str(host_id))
                    all_host_ids.add(str(host_id))

        # Level 2: PA hosts → their requirements → Investigation hosts.
        pa_ids = set(
            str(pk)
            for pk in ResourceInstance.objects.filter(
                pk__in=all_host_ids,
                graph__slug=GraphSlugs.PERMIT_APPLICATION,
            ).values_list("pk", flat=True)
        )
        if not pa_ids:
            return contexts

        # Map each PA back to the SR(s) whose context it belongs in.
        pa_to_sr_ids = defaultdict(set)
        for sr_id, requirement_ids in requirements_by_service_request.items():
            for requirement_id in requirement_ids:
                for host_id in hosts_by_requirement.get(str(requirement_id), ()):
                    if str(host_id) in pa_ids:
                        pa_to_sr_ids[str(host_id)].add(sr_id)

        pa_requirements_by_pa = self._requirements.requirement_ids_by_permit(
            list(pa_ids)
            # graph_slug defaults to PERMIT_APPLICATION
        )
        all_pa_req_ids = set(chain.from_iterable(pa_requirements_by_pa.values()))
        pa_hosts_by_req = self._requirements.host_ids_by_requirement(all_pa_req_ids)

        for pa_id, pa_req_ids in pa_requirements_by_pa.items():
            for sr_id in pa_to_sr_ids.get(pa_id, ()):
                for req_id in pa_req_ids:
                    contexts[sr_id].add(req_id)
                    contexts[sr_id].update(pa_hosts_by_req.get(req_id, ()))

        return contexts

    @staticmethod
    def allocate_service_request_id():
        return allocate_reference_number(
            GraphSlugs.BCAP_SERVICE_REQUEST, aliases.SERVICE_REQUEST_ID
        )

    def create(self, data, save):
        """If the create body already sets the submission date, attach the
        requirement working copies; otherwise just save."""
        if not self._incoming_submission_date(data):
            return save()
        return self._attach_requirements_and_save(data, save)

    def submit(self, instance, data, user, save):
        """Attach the requirement working copies on the first update that sets
        the submission date. Edit access to the filing gates the whole update."""
        PermitAccess.require_change(user, str(instance.pk))
        if not self._first_submission(instance, data):
            return save()
        return self._attach_requirements_and_save(
            data, save, service_request_id=instance.pk
        )

    def _attach_requirements_and_save(self, data, save, service_request_id=None):
        """Clone and attach requirements for the SR type; delete clones on rejection.
        Falls through to save() when the type has no module."""
        module_name = self._module_for_request_type(data)
        if module_name is None:
            return save()
        cloned = self._inject_requirements_from_templates(data, module_name)
        try:
            response = save()
            self._link_service_request_to_itself(
                cloned, service_request_id or self._saved_id(response)
            )
            self._index_requirements(cloned.requirements)
            return response
        except Exception:
            for requirement in [
                r for r in [cloned.parent, *cloned.requirements] if r is not None
            ]:
                requirement.delete()
            raise

    def _link_service_request_to_itself(self, cloned, service_request_id):
        """Link and satisfy the module's self-hosted requirement. Deferred
        because create provides no resource id until save returns."""
        if cloned.self_hosted is None or service_request_id is None:
            return
        self._requirements.link_submission(cloned.self_hosted.pk, service_request_id)
        self._requirements.builder.set_requirement_status(cloned.self_hosted.pk, True)

    @staticmethod
    def _saved_id(response):
        """Resource id from the create response, or None."""
        return (getattr(response, "data", None) or {}).get("resourceinstanceid")

    def _first_submission(self, instance, data):
        """The submission date is being set now and wasn't already stored."""
        stored = instance.aliased_data.service_request_admin
        return bool(self._incoming_submission_date(data)) and not (
            stored and stored.aliased_data.application_submission_date
        )

    def _incoming_submission_date(self, data):
        """The submission date carried in the request body, or None."""
        admin = data.get(ALIASED_DATA, {}).get(group_aliases.SERVICE_REQUEST_ADMIN, {})
        return admin.get(ALIASED_DATA, {}).get(aliases.APPLICATION_SUBMISSION_DATE)

    @staticmethod
    def _module_for_request_type(data):
        """Module name for the SR type, or None if unmapped.
        Reads ``display_value`` from the reference node directly (no list lookup)."""
        type_node = (
            data.get(ALIASED_DATA, {})
            .get(group_aliases.SERVICE_REQUEST_IDENTIFICATION, {})
            .get(ALIASED_DATA, {})
            .get(aliases.SERVICE_REQUEST_TYPE)
        )
        if not isinstance(type_node, dict):
            return None
        label = type_node.get("display_value") or ""
        return _MODULE_FOR_REQUEST_TYPE.get(label)

    def _index_requirements(self, requirements):
        """Index the clones once save has linked them to the service request
        (the descriptor embeds it)."""
        for requirement in requirements:
            requirement.save_descriptors()
        bulk_index(requirements)

    def _inject_requirements_from_templates(self, data, module_name):
        """Clone a working copy of each requirement template for the given module,
        link the children to the service request in flow order, and return the
        cloned module so a rejected save can delete everything it created."""
        admin = group_data(data, group_aliases.SERVICE_REQUEST_ADMIN)
        cloned = self._requirements.create_working_copies(module_name)
        modules = admin.setdefault(group_aliases.PROCESS_MODULE, [])
        modules.append(
            {
                ALIASED_DATA: {
                    aliases.MODULE_NAME: cloned.name,
                    aliases.MODULE_ORDER: len(modules) + 1,
                    aliases.PROCESS_REQUIREMENT: [
                        {
                            ALIASED_DATA: {
                                aliases.PROCESS_REQUIREMENT: str(copy.pk),
                                aliases.PROCESS_REQUIREMENT_ORDER: order,
                            }
                        }
                        for order, copy in enumerate(cloned.requirements, start=1)
                    ],
                }
            }
        )
        return cloned
