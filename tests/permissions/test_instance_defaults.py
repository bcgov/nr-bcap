"""What PERMISSION_DEFAULTS buys a user who owns nothing.

Default deny grants nothing without an explicit row, so without these defaults a
user reads only the resources they created. The group ids in the setting are
read per database, which is the step these tests would catch going wrong.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from arches.app.models.models import GraphModel, Group, ResourceInstance
from arches.app.utils.permission_backend import user_can_read_resource

from bcap.permissions.groups import Groups
from bcap.util.bcap_aliases import GraphSlugs

GRANTED = GraphSlugs.PUBLICATION  # Archaeology Branch reaches every graph
OMITTED = GraphSlugs.ARCHAEOLOGICAL_SITE  # an applicant files no inventory
APPLICANT = GraphSlugs.PERMIT_APPLICATION  # granted to Submitter as a graph


class InstanceDefaultsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.graphs = {
            slug: GraphModel.objects.filter(
                slug=slug, source_identifier__isnull=True
            ).first()
            for slug in (GRANTED, OMITTED, APPLICANT)
        }
        cls.staff = User.objects.create_user("instance-defaults-staff")
        cls.applicant = User.objects.create_user("instance-defaults-applicant")
        for user, group_name in (
            (cls.staff, Groups.ARCHAEOLOGY_BRANCH),
            (cls.applicant, Groups.SUBMITTER),
        ):
            group = Group.objects.filter(name=group_name).first()
            if group:
                user.groups.add(group)

    def setUp(self):
        if not all(self.graphs.values()):
            self.skipTest("policy graphs are not loaded in the test database")

    def read(self, user, slug):
        resource = ResourceInstance.objects.create(graph=self.graphs[slug])
        return user_can_read_resource(user, str(resource.pk))

    def test_a_granted_graph_is_readable_without_owning_the_resource(self):
        self.assertTrue(self.read(self.staff, GRANTED))

    def test_a_graph_the_setting_omits_stays_denied(self):
        self.assertFalse(self.read(self.applicant, OMITTED))

    def test_an_applicant_does_not_reach_someone_elses_permit(self):
        """The graph grant is wide; the framework narrows it per instance."""
        self.assertFalse(self.read(self.applicant, APPLICANT))
