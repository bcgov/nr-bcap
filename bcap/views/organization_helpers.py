"""View-layer glue for the organization stamp: service refusals as responses.

OrganizationService raises plain built-in exceptions so it stays framework-free;
the translation to status codes belongs here, where the request does.
"""

from dataclasses import dataclass

from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework_dataclasses.serializers import DataclassSerializer

from bcap.services.contributor.organization_service import OrganizationService
from bcap.permissions.groups import is_internal_user
from bcap.util.bcap_aliases import ALIASED_DATA
from bcap.util.tiles import group_data, resource_instance_value


@dataclass
class OrganizationChoice:
    """The organization a create body picked to file under, if any."""

    organization_id: str = ""


class OrganizationChoiceSerializer(DataclassSerializer):
    class Meta:
        dataclass = OrganizationChoice


def organization_to_stamp(user, picked="", field="organization_id"):
    """The organization id to record on what the user is creating, given the one
    they picked (if any). 403 when the pick isn't one of theirs, 400 on the named
    field when they belong to several and picked none."""
    try:
        return OrganizationService().resolve_organization(user, picked or "")
    except PermissionError:
        raise PermissionDenied("You do not belong to that organization.")
    except ValueError:
        raise ValidationError(
            {field: ["Choose which organization to file this under."]}
        )


def stamp_organization(request, group, alias):
    """Write the user's organization into a group of an incoming create body, so
    it saves in the same tile as the rest of that group. Any resource type with
    an owning-organization node gets its stamp this way."""
    picked = OrganizationChoiceSerializer(data=request.data, partial=True)
    picked.is_valid(raise_exception=True)
    group_data(request.data, group)[alias] = resource_instance_value(
        organization_to_stamp(request.user, picked.save().organization_id)
    )


def block_organization(request, group, alias):
    """Drop an owning organization the caller may not set: only branch staff move
    a resource between companies. Read without building the path, so a body that
    never mentioned the group is left alone."""
    if is_internal_user(request.user):
        return
    group_body = ((request.data or {}).get(ALIASED_DATA) or {}).get(group) or {}
    (group_body.get(ALIASED_DATA) or {}).pop(alias, None)
