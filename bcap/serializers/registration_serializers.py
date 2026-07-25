"""Request/response shapes for the admin signup-link API. Thin Serializers so
drf-spectacular documents them and the frontend's generated types follow."""

from django.conf import settings

from rest_framework.serializers import (
    Serializer,
    CharField,
    DateTimeField,
    EmailField,
    ListField,
    UUIDField,
    ValidationError,
)
from rest_framework_dataclasses.serializers import DataclassSerializer

from bcap.services.contributor_service import ContributorService, ContributorSummary


class NewContributorSerializer(Serializer):
    """Details for a Contributor created as part of the invite (for someone who
    has no Contributor record yet)."""

    name = CharField(help_text="Last name (or organization name) (required).")
    first_name = CharField(
        required=False, allow_blank=True, help_text="Given name, for a person."
    )
    email = EmailField(help_text="Contact email (required).")
    phone = CharField(
        required=False, allow_blank=True, help_text="Contact phone number."
    )


class RegistrationLinkRequestSerializer(Serializer):
    contributor_id = UUIDField(
        required=False,
        help_text="Existing Contributor to link the invited user to.",
    )
    new_contributor = NewContributorSerializer(
        required=False,
        help_text="Create a new Contributor and invite to it instead.",
    )
    groups = ListField(
        child=CharField(),
        required=False,
        help_text="Django group names to grant the invited user.",
    )

    def validate(self, data):
        contributor_id = data.get("contributor_id")
        if bool(contributor_id) == bool(data.get("new_contributor")):
            raise ValidationError(
                "Provide exactly one of contributor_id or new_contributor."
            )
        if contributor_id and not ContributorService().is_invitable(contributor_id):
            raise ValidationError(
                "That Contributor doesn't exist or is already linked to an account."
            )
        names = data.get("groups") or []
        if not_allowed := set(names) - set(settings.SELF_MANAGE_ROLE_GROUPS):
            raise ValidationError(
                f"Group(s) not allowed: {', '.join(sorted(not_allowed))}."
            )
        return data


class RegistrationLinkResponseSerializer(Serializer):
    signup_url = CharField(help_text="Single-use link to send to the invited user.")
    expires = DateTimeField(help_text="When the link stops being redeemable.")


class ContributorSummarySerializer(DataclassSerializer):
    """The contributor pick-list option shape, derived from the dataclass."""

    class Meta:
        dataclass = ContributorSummary
