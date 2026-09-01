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

GRANTED = GraphSlugs.PUBLICATION  # the setting gives Resource Editor view
OMITTED = GraphSlugs.ARCHAEOLOGICAL_SITE  # it does not


class InstanceDefaultsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.graphs = {
            slug: GraphModel.objects.filter(
                slug=slug, source_identifier__isnull=True
            ).first()
            for slug in (GRANTED, OMITTED)
        }
        cls.user = User.objects.create_user("instance-defaults-reader")
        editor = Group.objects.filter(name=Groups.RESOURCE_EDITOR).first()
        if editor:
            cls.user.groups.add(editor)

    def setUp(self):
        if not all(self.graphs.values()):
            self.skipTest("policy graphs are not loaded in the test database")

    def read(self, slug):
        resource = ResourceInstance.objects.create(graph=self.graphs[slug])
        return user_can_read_resource(self.user, str(resource.pk))

    def test_a_granted_graph_is_readable_without_owning_the_resource(self):
        self.assertTrue(self.read(GRANTED))

    def test_a_graph_the_setting_omits_stays_denied(self):
        self.assertFalse(self.read(OMITTED))
