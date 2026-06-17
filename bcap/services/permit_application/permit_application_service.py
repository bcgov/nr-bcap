"""Create-time data transforms for the Permit Application POST."""

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
    def __init__(self, requirement_service=None):
        self._requirements = requirement_service or ProcessRequirementService()

    def create_application(self, data, save_application):
        """Save the application, deleting the cloned requirements if it's
        rejected (the two saves can't share one transaction)."""
        requirements = self._inject_requirements_from_templates(data)
        try:
            response = save_application()
            # The clones save with index=False, so index them now that the save
            # has linked them: their descriptor embeds the application, and the
            # resource-instance widget resolves its label by searching the index.
            # Neither shows in this response, but both show on the next get.
            for requirement in requirements:
                requirement.save_descriptors()
            bulk_index(requirements)
            return response
        except Exception:
            for requirement in requirements:
                requirement.delete()
            raise

    def _inject_requirements_from_templates(self, data):
        """Clone a working copy of each requirement template, link them to the
        application in flow order, and return the copies."""
        admin = (
            data[ALIASED_DATA]
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
