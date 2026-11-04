"""What an external applicant may reach: their own permit application, the
requirements attached to it, and a requirement's submission host, but nothing
hanging off someone else's permit. Ministry staff pass on their route gate."""

from django.test import TestCase

from rest_framework.exceptions import PermissionDenied

from arches.app.models.models import ResourceInstance

from bcap.permissions.permit_access import PermitAccess
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

        acme = cls.acme = make_contributor(builder, "Acme Corp")
        cls.stranger = make_contributor(builder, "Stranger Co")
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
        # A graph no applicant is granted, on a resource one created anyway.
        cls.own_site = builder.make_resource(GraphSlugs.ARCHAEOLOGICAL_SITE)
        for permit, owner in (
            (cls.permit, cls.applicant),
            (cls.own_permit, cls.applicant),
            (cls.former_permit, cls.applicant),
            (cls.other_permit, cls.outsider),
            (cls.own_site, cls.applicant),
        ):
            ResourceInstance.objects.filter(pk=permit.pk).update(principaluser=owner)

    def test_reaches(self):
        for name, user, resource in (
            ("their organizations permit", self.applicant, self.permit),
            ("a requirement on that permit", self.applicant, self.requirement),
            ("the requirements submission host", self.applicant, self.host),
            ("a colleague in the owning org", self.colleague, self.requirement),
            ("a permit filed under no org", self.applicant, self.own_permit),
            ("a contributor on a permit they see", self.applicant, self.acme),
            ("internal staff reach anything", self.staff, self.other_permit),
        ):
            with self.subTest(name):
                self.assertTrue(PermitAccess.can_view(user, resource.pk))

    def test_does_not_reach(self):
        for name, user, resource in (
            ("an outsider on the permit", self.outsider, self.permit),
            ("an outsider on its requirement", self.outsider, self.requirement),
            ("an outsider on the submission host", self.outsider, self.host),
            ("a colleague on an unstamped permit", self.colleague, self.own_permit),
            ("a filing left at a former company", self.applicant, self.former_permit),
            # The graph grant is applicant-wide, so without narrowing this is
            # every other company's people and organizations.
            ("an unrelated contributor", self.applicant, self.stranger),
            # Arches permits a resource's creator ahead of any grant, so on a
            # graph applicants are never granted, narrowing is all that denies.
            ("a site they created off any permit", self.applicant, self.own_site),
            ("no resource at all", self.applicant, None),
        ):
            with self.subTest(name):
                self.assertFalse(PermitAccess.can_view(user, resource and resource.pk))

    def test_require_raises_for_an_outsider(self):
        with self.assertRaises(PermissionDenied):
            PermitAccess.require_view(self.outsider, self.requirement.pk)
        PermitAccess.require_view(self.applicant, self.requirement.pk)
