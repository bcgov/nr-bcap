"""Request/response shapes for the admin signup-link API. Thin Serializers so
drf-spectacular documents them and the frontend's generated types follow."""

from dataclasses import dataclass, field
from uuid import UUID

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

from bcap.services.contributor.contributor_service import (
    ContributorService,
    NewContributor,
)


@dataclass
class RegistrationLinkRequest:
    """The issue-link POST body: exactly one of an existing Contributor or the
    details of one to create, plus the groups to grant on redemption."""

    contributor_id: UUID | None = None
    new_contributor: NewContributor | None = None
    groups: list[str] = field(default_factory=list)


class NewContributorSerializer(DataclassSerializer):
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

    class Meta:
        dataclass = NewContributor
        # contributor_type is settled at creation, not by the inviter.
        fields = ["name", "first_name", "email", "phone"]


class RegistrationLinkRequestSerializer(DataclassSerializer):
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

    class Meta:
        dataclass = RegistrationLinkRequest

    def validate(self, body):
        if bool(body.contributor_id) == bool(body.new_contributor):
            raise ValidationError(
                "Provide exactly one of contributor_id or new_contributor."
            )
        if body.contributor_id and not ContributorService().is_invitable(
            body.contributor_id
        ):
            raise ValidationError(
                "That Contributor doesn't exist or is already linked to an account."
            )
        if not_allowed := set(body.groups) - set(settings.SELF_MANAGE_ROLE_GROUPS):
            raise ValidationError(
                f"Group(s) not allowed: {', '.join(sorted(not_allowed))}."
            )
        return body


class RegistrationLinkResponseSerializer(Serializer):
    signup_url = CharField(help_text="Single-use link to send to the invited user.")
    expires = DateTimeField(help_text="When the link stops being redeemable.")
