"""What an external applicant may reach: their own permit application, the
requirements attached to it, and a requirement's submission host, but nothing
hanging off someone else's permit. Ministry staff pass on their route gate."""

from django.test import TestCase

from rest_framework.exceptions import PermissionDenied

from arches.app.models.models import ResourceInstance

from bcap.permissions.permit_resource_access import PermitResourceAccess
from bcap.util.bcap_aliases import GraphSlugs
from tests.builders import FixtureBuilder
from tests.controlled_list_fixtures import ControlledListFixtures
from tests.permit_fixtures import RequirementRow, build_permit, make_requirement
from tests.services.contributor_fixtures import make_contributor, make_party, make_user


class ResourceAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        builder = FixtureBuilder()

        acme = make_contributor(builder, "Acme Corp")
        cls.applicant, _ = make_party(
            builder, "applicant", "Amy", "Applicant", associated_organization=acme
        )
        cls.colleague, _ = make_party(
            builder, "colleague", "Cal", "League", associated_organization=acme
        )
        cls.outsider = make_user("outsider")
        cls.staff = make_user("staff", internal=True)

        # permit -> requirement -> submission host, the chain an applicant's
        # module screen walks.
        cls.host = builder.make_resource(GraphSlugs.INVESTIGATION)
        cls.requirement = make_requirement(builder, "Referral")
        builder.link(str(cls.requirement.pk), submission=cls.host)
        cls.permit = build_permit(
            builder, "Acme App", [RequirementRow(cls.requirement)], organization=acme
        )
        cls.own_permit = build_permit(builder, "Unstamped App")
        # Filed under a company the applicant is not in: creating it does not
        # keep it, since a stamped filing belongs to whoever paid for it.
        cls.former_permit = build_permit(
            builder,
            "Former Corp App",
            organization=make_contributor(builder, "Former Corp"),
        )
        cls.other_permit = build_permit(builder, "Someone Else's")
        for permit, owner in (
            (cls.permit, cls.applicant),
            (cls.own_permit, cls.applicant),
            (cls.former_permit, cls.applicant),
            (cls.other_permit, cls.outsider),
        ):
            ResourceInstance.objects.filter(pk=permit.pk).update(principaluser=owner)

    def test_applicant_reaches_their_organizations_permit(self):
        self.assertTrue(PermitResourceAccess.can_view(self.applicant, self.permit.pk))

    def test_applicant_reaches_a_requirement_on_that_permit(self):
        self.assertTrue(
            PermitResourceAccess.can_view(self.applicant, self.requirement.pk)
        )

    def test_applicant_reaches_the_requirements_submission_host(self):
        self.assertTrue(PermitResourceAccess.can_view(self.applicant, self.host.pk))

    def test_a_colleague_in_the_owning_organization_reaches_it_too(self):
        self.assertTrue(
            PermitResourceAccess.can_view(self.colleague, self.requirement.pk)
        )

    def test_applicant_reaches_a_permit_they_created_under_no_organization(self):
        self.assertTrue(
            PermitResourceAccess.can_view(self.applicant, self.own_permit.pk)
        )

    def test_an_outsider_reaches_neither_the_permit_nor_what_hangs_off_it(self):
        for resource in (self.permit, self.requirement, self.host):
            self.assertFalse(PermitResourceAccess.can_view(self.outsider, resource.pk))

    def test_a_colleagues_organization_does_not_reach_an_unstamped_permit(self):
        # Created by the applicant under no organization: theirs alone.
        self.assertFalse(
            PermitResourceAccess.can_view(self.colleague, self.own_permit.pk)
        )

    def test_creating_a_filing_does_not_survive_leaving_the_company(self):
        self.assertFalse(
            PermitResourceAccess.can_view(self.applicant, self.former_permit.pk)
        )

    def test_internal_staff_reach_anything(self):
        self.assertTrue(PermitResourceAccess.can_view(self.staff, self.other_permit.pk))

    def test_no_resource_is_denied(self):
        self.assertFalse(PermitResourceAccess.can_view(self.applicant, None))

    def test_require_raises_for_an_outsider(self):
        with self.assertRaises(PermissionDenied):
            PermitResourceAccess.require_view(self.outsider, self.requirement.pk)
        PermitResourceAccess.require_view(self.applicant, self.requirement.pk)
