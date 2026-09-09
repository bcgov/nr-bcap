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

    def test_can_view(self):
        for expected, user, resource, why in (
            (True, self.applicant, self.permit, "their organization's permit"),
            (True, self.applicant, self.requirement, "a requirement on that permit"),
            (True, self.applicant, self.host, "the requirement's submission host"),
            (True, self.colleague, self.requirement, "a colleague in the same org"),
            (True, self.applicant, self.own_permit, "a permit they filed unstamped"),
            (True, self.applicant, self.acme, "a contributor on a permit they see"),
            (True, self.staff, self.other_permit, "internal staff reach anything"),
            (False, self.outsider, self.permit, "an outsider's permit"),
            (False, self.outsider, self.requirement, "an outsider's requirement"),
            (False, self.outsider, self.host, "an outsider's submission host"),
            (False, self.colleague, self.own_permit, "unstamped is the filer's alone"),
            (False, self.applicant, self.former_permit, "filed at a former company"),
            # The graph grant is applicant-wide, so without narrowing this is
            # every other company's people and organizations.
            (False, self.applicant, self.stranger, "an unrelated contributor"),
            # Arches permits a resource's creator ahead of any grant, so on a
            # graph applicants are never granted, narrowing is all that denies.
            (False, self.applicant, self.own_site, "what they created off a permit"),
            (False, self.applicant, None, "no resource at all"),
        ):
            with self.subTest(why):
                self.assertIs(
                    PermitAccess.can_view(user, resource and resource.pk), expected
                )

    def test_require_raises_for_an_outsider(self):
        with self.assertRaises(PermissionDenied):
            PermitAccess.require_view(self.outsider, self.requirement.pk)
        PermitAccess.require_view(self.applicant, self.requirement.pk)
