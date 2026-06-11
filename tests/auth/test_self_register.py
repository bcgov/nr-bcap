"""First-login self-registration for external identities.

A first-time BCSC/BCeID login auto-creates the account (the loginSource is in
settings' allowed_self_register_domains) and lands it in the overridden default
groups -- Guest + Submitter, not the shared lib's Guest + Resource Exporter.
This also guards the DEFAULT_GROUPS override applied in BcapConfig.ready().
Internal (idir) logins are not in the allow-list, so they don't self-register.

    python manage.py test tests.auth.test_self_register \\
        --settings="tests.test_settings" --keepdb
"""

from django.contrib.auth.models import Group
from django.test import TestCase

from bcgov_arches_common.util.auth.oauth_session_control import _self_register

from bcap.permissions.groups import Groups


def _userinfo(login_source, username):
    return {
        "loginSource": login_source,
        "preferred_username": username,
        "given_name": "Test",
        "family_name": "User",
    }


class SelfRegisterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for name in (Groups.GUEST, Groups.SUBMITTER):
            Group.objects.get_or_create(name=name)

    def _groups(self, user):
        return set(user.groups.values_list("name", flat=True))

    def test_bcsc_first_login_creates_a_submitter(self):
        user = _self_register(_userinfo("bcsc", "bcsc/jdoe"))
        self.assertIsNotNone(user)
        self.assertEqual(self._groups(user), {Groups.GUEST, Groups.SUBMITTER})

    def test_bceid_first_login_creates_a_submitter(self):
        user = _self_register(_userinfo("bceid", "jdoe@bceid"))
        self.assertIsNotNone(user)
        self.assertEqual(self._groups(user), {Groups.GUEST, Groups.SUBMITTER})

    def test_idir_does_not_self_register(self):
        user = _self_register(_userinfo("idir", "idir\\jdoe"))
        self.assertIsNone(user)

    def test_unknown_source_does_not_self_register(self):
        user = _self_register(_userinfo("google", "jdoe@google"))
        self.assertIsNone(user)
