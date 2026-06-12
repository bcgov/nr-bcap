import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class RegistrationLink(models.Model):
    """An admin-issued, single-use invite binding a Contributor to the next
    BC government login. The id is the bearer token; redeeming it stamps the
    user's username onto the Contributor's bcap_username."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Existing Contributor ResourceInstance to attach the user to. A bare UUID
    # (not an FK) to keep this Django model decoupled from the Arches resource
    # tables, as ResourceDraft.resourceinstanceid does. Null when the invite is
    # for a not-yet-created Contributor; filled in at redemption.
    contributor_id = models.UUIDField(null=True, blank=True)
    # Details for a Contributor created lazily at redemption, so an invite that
    # is never redeemed leaves no orphan resource. Mutually exclusive with
    # contributor_id.
    new_contributor = models.JSONField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="registration_links_issued",
    )
    created = models.DateTimeField(auto_now_add=True)
    expires = models.DateTimeField()
    # When/who consumed the link; null until used.
    used = models.DateTimeField(null=True, blank=True)
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registration_links_used",
    )

    class Meta:
        db_table = "bcap_registration_links"
        verbose_name = "Registration Link"
        verbose_name_plural = "Registration Links"
        indexes = [models.Index(fields=["contributor_id"])]

    @property
    def is_redeemable(self):
        """True when the link has neither been used nor expired."""
        return self.used is None and self.expires > timezone.now()

    def __str__(self):
        state = (
            "used" if self.used else "redeemable" if self.is_redeemable else "expired"
        )
        return (
            f"RegistrationLink({self.id}, contributor={self.contributor_id}, {state})"
        )
