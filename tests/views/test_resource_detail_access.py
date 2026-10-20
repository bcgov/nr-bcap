"""The generic resource route authorizes nothing at the gate, so the
per-instance check is all that stands between an applicant and another
applicant's filing."""

from django.test import TestCase, override_settings
from django.urls import reverse

from arches.app.models.models import ResourceInstance

from bcap.util.bcap_aliases import GraphSlugs
from tests.builders import FixtureBuilder
from tests.controlled_list_fixtures import ControlledListFixtures
from tests.permit_fixtures import build_permit
from tests.services.contributor_fixtures import make_contributor, make_party, make_user
from tests.views.helpers import login_as


@override_settings(ROOT_URLCONF="tests.test_urls")
class ResourceDetailAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        builder = FixtureBuilder()

        acme = make_contributor(builder, "Acme Corp")
        cls.applicant, _ = make_party(
            builder, "applicant", "Amy", "Applicant", associated_organization=acme
        )
        cls.outsider = make_user("outsider")
        cls.staff = make_user("staff", internal=True)

        cls.own_permit = build_permit(builder, "Acme App", organization=acme)
        cls.other_permit = build_permit(builder, "Someone Else's")
        ResourceInstance.objects.filter(pk=cls.other_permit.pk).update(
            principaluser=cls.outsider
        )

    def get_permit(self, user, permit, login_source="BCEID"):
        login_as(self.client, user, login_source)
        return self.client.get(
            reverse(
                "api-resource",
                kwargs={"graph": GraphSlugs.PERMIT_APPLICATION, "pk": permit.pk},
            )
        )

    def test_applicant_reads_their_own_filing(self):
        response = self.get_permit(self.applicant, self.own_permit)

        self.assertEqual(response.status_code, 200)

    def test_applicant_is_refused_another_applicants_filing(self):
        response = self.get_permit(self.applicant, self.other_permit)

        self.assertEqual(response.status_code, 403)

    def test_staff_read_any_filing(self):
        response = self.get_permit(self.staff, self.other_permit, login_source="IDIR")

        self.assertEqual(response.status_code, 200)

    def test_applicant_cannot_write_through_the_route(self):
        login_as(self.client, self.applicant, "BCEID")
        url = reverse(
            "api-resource",
            kwargs={
                "graph": GraphSlugs.PERMIT_APPLICATION,
                "pk": self.own_permit.pk,
            },
        )

        response = self.client.patch(url, data={}, content_type="application/json")

        self.assertEqual(response.status_code, 403)
