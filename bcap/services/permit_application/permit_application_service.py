"""Create- and submission-time transforms for a permit application: seed the
application id on create, and attach the requirement working copies whenever a
create or update sets the submission date."""

from itertools import chain

from django.db import connection

from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)
from bcap.util.aliases.permit_application import (
    PermitApplicationAliases as aliases,
    PermitApplicationGroupAliases as group_aliases,
)
from bcap.util.bcap_aliases import ALIASED_DATA
from bcap.util.indexing import bulk_index


class PermitApplicationService:
    """Assigns the id and attaches requirements on first submission."""

    def __init__(self, requirement_service=None):
        self._requirements = requirement_service or ProcessRequirementService()

    def submission_context_ids_for_permits(self, permits, requirements_by_permit=None):
        """Map each permit to the resource ids its unread counts span (the permit
        and its requirements' submission hosts); pass known requirement ids to
        skip a query."""
        permit_ids = [str(permit.pk) for permit in permits]
        contexts = {pk: {pk} for pk in permit_ids}

        if requirements_by_permit is None:
            requirements_by_permit = self._requirements.requirement_ids_by_permit(
                permit_ids
            )
        all_requirement_ids = set(chain.from_iterable(requirements_by_permit.values()))
        hosts_by_requirement = self._requirements.host_ids_by_requirement(
            all_requirement_ids
        )
        for permit_id, requirement_ids in requirements_by_permit.items():
            for requirement_id in requirement_ids:
                hosts = hosts_by_requirement.get(requirement_id, ())
                contexts[permit_id].update(hosts)
        return contexts

    @staticmethod
    def allocate_permit_application_id():
        """Next APP-<n> from the sequence (atomic across concurrent saves)."""
        with connection.cursor() as cur:
            cur.execute("SELECT nextval('bcap_permit_application_id_seq')")
            return f"APP-{cur.fetchone()[0]}"

    def create(self, data, save):
        """If the create body already sets the submission date, attach the
        requirement working copies; otherwise just save."""
        if not self._incoming_submission_date(data):
            return save()
        return self._attach_requirements_and_save(data, save)

    def submit(self, instance, data, save):
        """Attach the requirement working copies on the first update that sets
        the submission date."""
        if not self._first_submission(instance, data):
            return save()
        return self._attach_requirements_and_save(data, save, permit_id=instance.pk)

    def _attach_requirements_and_save(self, data, save, permit_id=None):
        """Clone and attach the requirements, deleting every clone (the grouping
        parent included) if the save is rejected (the two saves can't share one
        transaction)."""
        cloned = self._inject_requirements_from_templates(data)
        try:
            response = save()
            self._link_permit_to_itself(cloned, permit_id or self._saved_id(response))
            self._index_requirements(cloned.requirements)
            return response
        except Exception:
            for requirement in [cloned.parent, *cloned.requirements]:
                requirement.delete()
            raise

    def _link_permit_to_itself(self, cloned, permit_id):
        """Point the module's own-submission requirement at the permit. Deferred
        until here because on create the permit has no id until save returns."""
        if cloned.self_hosted is None or permit_id is None:
            return
        self._requirements.link_submission(cloned.self_hosted.pk, permit_id)

    @staticmethod
    def _saved_id(response):
        """The permit id out of the create response, or None if it carries none."""
        return (getattr(response, "data", None) or {}).get("resourceinstanceid")

    def _first_submission(self, instance, data):
        """The submission date is being set now and wasn't already stored."""
        stored = instance.aliased_data.application_admin
        return bool(self._incoming_submission_date(data)) and not (
            stored and stored.aliased_data.application_submission_date
        )

    def _incoming_submission_date(self, data):
        """The submission date carried in the request body, or None."""
        admin = data.get(ALIASED_DATA, {}).get(group_aliases.APPLICATION_ADMIN, {})
        return admin.get(ALIASED_DATA, {}).get(aliases.APPLICATION_SUBMISSION_DATE)

    def _index_requirements(self, requirements):
        """Index the clones once save has linked them to the application (the
        descriptor embeds it)."""
        for requirement in requirements:
            requirement.save_descriptors()
        bulk_index(requirements)

    def _inject_requirements_from_templates(self, data):
        """Clone a working copy of each requirement template, link the children
        to the application in flow order, and return the cloned module so a
        rejected save can delete everything it created. The module id and
        requirement ids are filled in by the assign-module-ids save hook."""
        admin = (
            data.setdefault(ALIASED_DATA, {})
            .setdefault(group_aliases.APPLICATION_ADMIN, {ALIASED_DATA: {}})
            .setdefault(ALIASED_DATA, {})
        )
        cloned = self._requirements.create_working_copies()
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
