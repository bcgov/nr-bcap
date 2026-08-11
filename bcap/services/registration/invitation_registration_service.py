"""Issue and redeem admin registration links. The Contributor reads and writes
these orchestrate live on the Contributor service."""

import logging
import uuid
from dataclasses import asdict
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.db import transaction
from django.utils import timezone

from bcgov_arches_common.util.auth.oauth_session_control import _clean_username

from bcap.models import RegistrationLink
from bcap.services.contributor.contributor_service import (
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

    def issue_link(
        self, created_by, contributor_id=None, new_contributor=None, groups=None
    ):
        """Create a single-use, expiring link for an existing Contributor or, if
        given new_contributor instead, one created only at redemption (so an
        unredeemed invite leaves no orphan). Exactly one is given. groups are the
        Django group names to grant on redemption."""
        link = RegistrationLink.objects.create(
            contributor_id=contributor_id,
            new_contributor=asdict(new_contributor) if new_contributor else None,
            groups=groups or [],
            created_by=created_by,
            expires=timezone.now()
            + timedelta(days=settings.REGISTRATION_LINK_TTL_DAYS),
        )
        return link

    def _redeemable_link(self, token):
        """The redeemable link for this token, or None when the token is
        missing, malformed, expired, or already used."""
        try:
            pk = uuid.UUID(str(token))
        except (ValueError, TypeError):
            return None
        return RegistrationLink.objects.filter(
            pk=pk, used__isnull=True, expires__gt=timezone.now()
        ).first()

    def redeem_link(self, token, user):
        """Bind the link's Contributor to this user and grant the configured
        groups. Returns the link, or None if the token is missing, expired/used,
        the user already holds a Contributor, or the Contributor is already
        linked to another account."""
        if not (link := self._redeemable_link(token)):
            logger.warning(
                "Registration token %s redeemed by user %s is missing, expired, "
                "or used.",
                token,
                user.pk,
            )
            return None
        # One user maps to at most one Contributor; check before creating any,
        # so a rejected redeem leaves no orphan.
        existing = self._contributors.username_contributor_id(user.username)
        if existing is not None:
            logger.warning(
                "Registration link %s: user %s already holds Contributor %s; "
                "a user may hold only one Contributor.",
                link.id,
                user.pk,
                existing,
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
                # Enforce the whitelist again here, in case a link was issued
                # with groups that have since dropped off it.
                allowed = [
                    g for g in link.groups if g in settings.SELF_MANAGE_ROLE_GROUPS
                ]
                group_names = allowed or ["Guest"]
                user.groups.add(*Group.objects.filter(name__in=group_names))
                link.used = timezone.now()
                link.used_by = user
                link.save()
        except Exception:
            if created:
                self._contributors.delete_contributor(link.contributor_id)
            raise
        return link

    def ensure_invited_user(self, request, token):
        """Invite-only access: on the OAuth callback, create the Django user for
        a first-time invitee so login can proceed. The redeemable invite link is
        the authorization -- no account is made without one, so an uninvited
        sign-in still falls through to unauthorized. The callback then calls
        redeem_pending."""
        pending = request.session.get(PENDING_REGISTRATION_SESSION_KEY)
        if not self._redeemable_link(pending):
            return
        userinfo = (token or {}).get("userinfo", {})
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
        user. A no-op when login didn't complete or nothing is pending."""
        if not request.user.is_authenticated:
            return
        if token := request.session.pop(PENDING_REGISTRATION_SESSION_KEY, None):
            self.redeem_link(token, request.user)
