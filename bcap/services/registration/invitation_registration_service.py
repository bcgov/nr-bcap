"""Issue and redeem admin registration links. The Contributor reads and writes
these orchestrate live on the Contributor service."""

import logging
from dataclasses import asdict
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.db import transaction
from django.utils import timezone

from bcgov_arches_common.util.auth.oauth_session_control import _clean_username

from bcap.models import RegistrationLink
from bcap.services.dashboard.contributor_service import (
    ContributorService,
    NewContributor,
)

logger = logging.getLogger(__name__)

# Session key the claim flow parks a token under between the anonymous landing
# and the authenticated redemption.
PENDING_REGISTRATION_SESSION_KEY = "pending_registration_token"


class InvitationRegistrationService:
    def __init__(self, contributor_service=None):
        self._contributors = contributor_service or ContributorService()

    def issue_link(self, created_by, contributor_id=None, new_contributor=None):
        """Create a single-use, expiring link for an existing Contributor or, if
        given new_contributor instead, one created only at redemption (so an
        unredeemed invite leaves no orphan). Exactly one is given."""
        link = RegistrationLink.objects.create(
            contributor_id=contributor_id,
            new_contributor=asdict(new_contributor) if new_contributor else None,
            created_by=created_by,
            expires=timezone.now()
            + timedelta(days=settings.REGISTRATION_LINK_TTL_DAYS),
        )
        return link

    def redeem_link(self, token, user):
        """Bind the link's Contributor to this user and grant the configured
        groups. Returns the link, or None if the token is missing, expired/used,
        or the Contributor is already linked to another account."""
        if not (
            link := RegistrationLink.objects.filter(
                pk=token, used__isnull=True, expires__gt=timezone.now()
            ).first()
        ):
            logger.warning(
                "Registration token %s redeemed by user %s is missing, expired, "
                "or used.",
                token,
                user.pk,
            )
            return None
        created = link.contributor_id is None
        if created:
            link.contributor_id = self._contributors.create_contributor(
                NewContributor(**link.new_contributor)
            )
        try:
            with transaction.atomic():
                linked = self._contributors.set_bcap_username(
                    link.contributor_id, user.username
                )
                if not linked:
                    logger.warning(
                        "Registration link %s: Contributor %s already linked to "
                        "an account; user %s could not redeem.",
                        link.id,
                        link.contributor_id,
                        user.pk,
                    )
                    return None
                groups = Group.objects.filter(
                    name__in=settings.REGISTRATION_IDIR_GROUPS
                )
                user.groups.add(*groups)
                link.used = timezone.now()
                link.used_by = user
                link.save()
        except Exception:
            if created:
                self._contributors.delete_contributor(link.contributor_id)
            raise
        return link

    def ensure_invited_user(self, request, token):
        """Invite-only IDIR access: on the OAuth callback, create the Django
        user for a first-time invitee so login can proceed. No account is made
        without a pending invite, so an uninvited IDIR sign-in still falls
        through to unauthorized. The callback then calls redeem_pending."""
        if request.session.get(PENDING_REGISTRATION_SESSION_KEY) is None:
            return
        userinfo = (token or {}).get("userinfo", {})
        if userinfo.get("loginSource") != "IDIR":
            return
        username = _clean_username(userinfo.get("preferred_username"))
        if not username or User.objects.filter(username=username).exists():
            return
        user = User(
            username=username,
            first_name=userinfo.get("given_name", ""),
            last_name=userinfo.get("family_name", ""),
        )
        user.set_unusable_password()
        user.save()

    def redeem_pending(self, request):
        """Redeem an invite stashed before login, for the now-authenticated
        user. Invites are for BC government staff, so only an IDIR login
        redeems; the token is left for a later IDIR sign-in otherwise. A no-op
        when login didn't complete or nothing is pending."""
        if not request.user.is_authenticated:
            return
        oauth_token = request.session.get("oauth_token") or {}
        if oauth_token.get("userinfo", {}).get("loginSource") != "IDIR":
            return
        if token := request.session.pop(PENDING_REGISTRATION_SESSION_KEY, None):
            self.redeem_link(token, request.user)
