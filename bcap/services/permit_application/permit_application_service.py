"""Submission-time transforms for a permit application: on the update that
first sets the submission date, assign the application id and attach the
requirement working copies."""

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

    @staticmethod
    def allocate_permit_application_id():
        """Next APP-<n> from the sequence (atomic across concurrent saves)."""
        with connection.cursor() as cur:
            cur.execute("SELECT nextval('bcap_permit_application_id_seq')")
            return f"APP-{cur.fetchone()[0]}"

    def create(self, data, save):
        """Seed the application id when the application is created."""
        self._assign_application_id(data)
        return save()

    def submit(self, instance, data, save):
        """Attach the requirement working copies on the first update that sets
        the submission date, deleting the clones if the save is rejected (the
        two saves can't share one transaction)."""
        if not self._first_submission(instance, data):
            return save()
        requirements = self._inject_requirements_from_templates(data)
        try:
            response = save()
            self._index_requirements(requirements)
            return response
        except Exception:
            for requirement in requirements:
                requirement.delete()
            raise

    def _first_submission(self, instance, data):
        """The submission date is being set now and wasn't already stored."""
        groups = data.get(ALIASED_DATA, {})
        admin = groups.get(group_aliases.APPLICATION_ADMIN, {})
        incoming = admin.get(ALIASED_DATA, {}).get(aliases.APPLICATION_SUBMISSION_DATE)
        stored = instance.aliased_data.application_admin
        return bool(incoming) and not (
            stored and stored.aliased_data.application_submission_date
        )

    def _assign_application_id(self, data):
        """Stamp the sequence-assigned id onto the identification tile."""
        ident = data.setdefault(ALIASED_DATA, {}).setdefault(
            group_aliases.APPLICATION_IDENTIFICATION, {ALIASED_DATA: {}}
        )
        ident.setdefault(ALIASED_DATA, {})[
            aliases.APPLICATION_ID
        ] = self.allocate_permit_application_id()

    def _index_requirements(self, requirements):
        """Index the clones once save has linked them to the application (the
        descriptor embeds it)."""
        for requirement in requirements:
            requirement.save_descriptors()
        bulk_index(requirements)

    def _inject_requirements_from_templates(self, data):
        """Clone a working copy of each requirement template, link them to the
        application in flow order, and return the copies."""
        admin = (
            data.setdefault(ALIASED_DATA, {})
            .setdefault(group_aliases.APPLICATION_ADMIN, {ALIASED_DATA: {}})
            .setdefault(ALIASED_DATA, {})
        )
        copies = self._requirements.create_working_copies()
        admin[aliases.PROCESS_REQUIREMENT] = [
            {
                ALIASED_DATA: {
                    aliases.PROCESS_REQUIREMENT: str(copy.pk),
                    aliases.PROCESS_REQUIREMENT_ORDER: order,
                }
            }
            for order, copy in enumerate(copies, start=1)
        ]
        return copies
