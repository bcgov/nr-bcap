"""Tests for the read-only, owner-scoped HCA Permit endpoints: a user lists and
GETs only the permits they created (principaluser), and the routes are GET-only."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from arches.app.models.models import ResourceInstance

from bcap.builders.resource_builder import ResourceBuilder
from tests.views.helpers import AuthTestHelper

UNKNOWN_ID = "00000000-0000-0000-0000-000000000000"


def make_hca_permit(builder, permit_number, owner):
    """A minimal HCA permit (just a permit number) owned by ``owner``."""
    permit = builder.new_resource("hca_permit")
    builder.append_blank_tile_for_group(
        permit, "permit_identification", {"permit_number": permit_number}
    )
    permit.save(**builder.save_kwargs)
    # principaluser (the "owner" the views filter on) isn't set by the builder,
    # so stamp it directly for deterministic ownership.
    ResourceInstance.objects.filter(pk=permit.pk).update(principaluser=owner)
    return permit


@override_settings(ROOT_URLCONF="tests.test_urls")
class HCAPermitViewTests(AuthTestHelper, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # admin is a superuser with the viewable nodegroups a GET needs; cls.user
        # (testuser) is the "other" user used to prove owner-scoping.
        cls.admin = get_user_model().objects.get(username="admin")
        builder = ResourceBuilder()
        cls.own = make_hca_permit(builder, "HCA-1000", cls.admin)
        cls.other = make_hca_permit(builder, "HCA-2000", cls.user)

    def setUp(self):
        super().setUp()
        self.idir_login_simulate(self.admin)

    def _detail_url(self, pk):
        return reverse("api_hca_permit", kwargs={"pk": pk})

    def test_get_returns_own_permit(self):
        resp = self.client.get(self._detail_url(self.own.pk))
        self.assertEqual(resp.status_code, 200)
        ident = resp.json()["aliased_data"]["permit_identification"]["aliased_data"]
        self.assertEqual(ident["permit_number"]["display_value"], "HCA-1000")

    def test_get_inaccessible_permit_returns_404(self):
        # Owner-scoping makes another user's permit indistinguishable from one
        # that doesn't exist: cls.other belongs to testuser, not the admin.
        for label, pk in [("other user's", self.other.pk), ("unknown", UNKNOWN_ID)]:
            with self.subTest(permit=label):
                self.assertEqual(self.client.get(self._detail_url(pk)).status_code, 404)

    def test_list_returns_only_own_permits(self):
        resp = self.client.get(reverse("api_hca_permit_list"))
        self.assertEqual(resp.status_code, 200)
        ids = {row["resourceinstanceid"] for row in resp.json()["results"]}
        self.assertIn(str(self.own.pk), ids)
        self.assertNotIn(str(self.other.pk), ids)

    def test_unauthenticated_request_is_rejected(self):
        self.client.logout()
        resp = self.client.get(self._detail_url(self.own.pk))
        # 302 -> redirect to login; 401/403 -> DRF rejection. Never the data.
        self.assertIn(resp.status_code, (302, 401, 403))

    def test_detail_is_get_only(self):
        # The view is a RetrieveAPIView, so write verbs aren't routed.
        url = self._detail_url(self.own.pk)
        self.assertEqual(
            self.client.put(
                url, data="{}", content_type="application/json"
            ).status_code,
            405,
        )
        self.assertEqual(self.client.delete(url).status_code, 405)
