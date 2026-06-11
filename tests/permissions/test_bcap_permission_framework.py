"""Unit tests for the default-deny permission framework, method by method:
reading the policy (_policy_group_ids), choosing which groups need an explicit
deny (_deny_groups), building one graph's (principal, perm) assignments
(_graph_assignments), the search-index values (get_index_values), and the
authoritative applier (apply_permission_defaults) -- contract and read effect.

    python manage.py test tests.permissions.test_bcap_permission_framework \\
        --settings="tests.test_settings" --keepdb
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase

from arches.app.models.models import Group
from arches.app.models.resource import Resource
from arches.app.utils.permission_backend import (
    assign_perm,
    get_groups_with_perms,
    get_resource_types_by_perm,
)

from bcap.permissions.bcap_arches_permission_framework import (
    MANAGED_GROUPS,
    NO_ACCESS,
    BcapArchesPermissionFramework,
)
from bcap.permissions.groups import Groups

PERMIT_APPLICATION_GRAPH = "5c900e2b-257c-4af3-b67f-b5caf3850f71"
ARCHAEOLOGICAL_SITE_GRAPH = "cef9c510-e3e6-4057-ac08-89ad926180b4"


class PolicyGroupIdsTests(TestCase):
    """_policy_group_ids returns the group ids a graph grants a verb. On
    permit_application, Archaeology Branch has full access while Resource
    Exporter is view-only -- so they diverge on "delete"."""

    @classmethod
    def setUpTestData(cls):
        for name in MANAGED_GROUPS:
            Group.objects.get_or_create(name=name)

    def _granted(self, verb):
        ids = BcapArchesPermissionFramework._policy_group_ids(
            PERMIT_APPLICATION_GRAPH, verb
        )
        names = dict(Group.objects.values_list("id", "name"))
        return {names[gid] for gid in ids}

    def test_view_includes_a_view_only_group(self):
        self.assertIn(Groups.RESOURCE_EXPORTER, self._granted("view"))

    def test_delete_excludes_view_only_groups(self):
        granted = self._granted("delete")
        self.assertIn(Groups.ARCHAEOLOGY_BRANCH, granted)
        self.assertNotIn(Groups.RESOURCE_EXPORTER, granted)

    def test_unknown_graph_grants_nobody(self):
        ids = BcapArchesPermissionFramework._policy_group_ids("not-a-graph", "view")
        self.assertEqual(ids, [])


class DenyGroupsTests(TestCase):
    """_deny_groups flags managed (or Guest) groups holding a broad nodegroup
    perm, which would otherwise let them read everything by fallback."""

    def setUp(self):
        self.read = Permission.objects.filter(codename="read_nodegroup").first()

    def _make(self, name, *, with_perm):
        group, _ = Group.objects.get_or_create(name=name)
        if with_perm:
            group.permissions.add(self.read)
        return group

    def _deny(self):
        return BcapArchesPermissionFramework._deny_groups(
            {g.name: g for g in Group.objects.all()}
        )

    def test_flags_guest_holding_the_broad_perm(self):
        self._make(Groups.GUEST, with_perm=True)
        self.assertIn(Groups.GUEST, self._deny())

    def test_skips_group_without_the_broad_perm(self):
        self._make(Groups.ARCHAEOLOGY_BRANCH, with_perm=False)
        self.assertNotIn(Groups.ARCHAEOLOGY_BRANCH, self._deny())

    def test_skips_unmanaged_group_even_with_the_perm(self):
        # Default-deny already covers it; denying breaks multi-role users.
        self._make("Some Other Group", with_perm=True)
        self.assertNotIn("Some Other Group", self._deny())


class GraphAssignmentsTests(TestCase):
    """_graph_assignments converts one graph's policy into (principal, perm)
    pairs: grant the allowed groups, deny the privileged ones it doesn't grant,
    and deny the anonymous public unless Guest itself is granted view."""

    @classmethod
    def setUpTestData(cls):
        for name in (Groups.ARCHAEOLOGY_BRANCH, Groups.GUEST):
            Group.objects.get_or_create(name=name)
        cls.groups = {g.name: g for g in Group.objects.all()}
        cls.anonymous = get_user_model().objects.create_user("anon_probe")

    def _assign(self, allow, deny_groups=None, anonymous=None):
        return BcapArchesPermissionFramework._graph_assignments(
            allow, self.groups, deny_groups or set(), anonymous
        )

    def test_grants_a_perm_per_verb(self):
        branch = self.groups[Groups.ARCHAEOLOGY_BRANCH]
        assignments = self._assign({Groups.ARCHAEOLOGY_BRANCH: ["view", "change"]})
        self.assertIn((branch, "read_nodegroup"), assignments)
        self.assertIn((branch, "write_nodegroup"), assignments)

    def test_denies_privileged_group_not_granted(self):
        guest = self.groups[Groups.GUEST]
        assignments = self._assign(
            {Groups.ARCHAEOLOGY_BRANCH: ["view"]},
            deny_groups={Groups.GUEST},
        )
        self.assertIn((guest, NO_ACCESS), assignments)

    def test_denies_anonymous_when_guest_lacks_view(self):
        assignments = self._assign(
            {Groups.ARCHAEOLOGY_BRANCH: ["view"]}, anonymous=self.anonymous
        )
        self.assertIn((self.anonymous, NO_ACCESS), assignments)

    def test_allows_anonymous_when_guest_granted_view(self):
        assignments = self._assign({Groups.GUEST: ["view"]}, anonymous=self.anonymous)
        self.assertNotIn((self.anonymous, NO_ACCESS), assignments)


class SearchIndexValuesTests(TestCase):
    """get_index_values folds the graph policy into the per-instance group
    lists so search visibility tracks it: view -> groups_read, change ->
    groups_edit."""

    @classmethod
    def setUpTestData(cls):
        for name in MANAGED_GROUPS:
            Group.objects.get_or_create(name=name)

    def _index(self):
        resource = Resource(graph_id=PERMIT_APPLICATION_GRAPH)
        return BcapArchesPermissionFramework().get_index_values(resource)

    def test_view_groups_indexed_as_readable(self):
        ids = dict(Group.objects.values_list("name", "id"))
        groups_read = self._index()["groups_read"]
        self.assertIn(ids[Groups.ARCHAEOLOGY_BRANCH], groups_read)
        self.assertIn(ids[Groups.RESOURCE_EXPORTER], groups_read)

    def test_view_only_group_not_indexed_as_editable(self):
        ids = dict(Group.objects.values_list("name", "id"))
        groups_edit = self._index()["groups_edit"]
        self.assertIn(ids[Groups.ARCHAEOLOGY_BRANCH], groups_edit)
        self.assertNotIn(ids[Groups.RESOURCE_EXPORTER], groups_edit)


class ApplyPermissionDefaultsTests(TestCase):
    """apply_permission_defaults writes the policy onto each graph's real
    nodegroups and returns the graphs it touched. The graph_ids arg scopes it
    to a subset."""

    @classmethod
    def setUpTestData(cls):
        for name in MANAGED_GROUPS:
            Group.objects.get_or_create(name=name)

    def test_applies_only_the_requested_graph(self):
        applied = BcapArchesPermissionFramework.apply_permission_defaults(
            graph_ids=[PERMIT_APPLICATION_GRAPH]
        )
        self.assertEqual(applied, [PERMIT_APPLICATION_GRAPH])

    def test_applies_nothing_for_an_unknown_graph(self):
        applied = BcapArchesPermissionFramework.apply_permission_defaults(
            graph_ids=["00000000-0000-0000-0000-000000000000"]
        )
        self.assertEqual(applied, [])

    def test_apply_reasserts_the_policy_over_a_non_default_state(self):
        nodegroup = BcapArchesPermissionFramework._graph_nodegroups(
            PERMIT_APPLICATION_GRAPH
        )[0]
        rogue = Group.objects.create(name="Rogue Group")
        branch = Group.objects.get(name=Groups.ARCHAEOLOGY_BRANCH)

        # Non-default starting state: a non-policy group holds a perm here.
        assign_perm("write_nodegroup", rogue, nodegroup)
        self.assertIn(rogue, get_groups_with_perms(nodegroup))

        BcapArchesPermissionFramework.apply_permission_defaults(
            graph_ids=[PERMIT_APPLICATION_GRAPH]
        )

        # Authoritative re-assert: stray group cleared, policy group granted.
        groups_now = get_groups_with_perms(nodegroup, attach_perms=True)
        self.assertNotIn(rogue, groups_now)
        self.assertIn("read_nodegroup", groups_now.get(branch, []))


class PermissionDefaultsEffectTests(TestCase):
    """End-to-end: after applying, the resolver reports the policy -- a granted
    group can read its graph; Guest (the public) can read nothing."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.users = {}
        for name in (Groups.ARCHAEOLOGY_BRANCH, Groups.GUEST):
            group, _ = Group.objects.get_or_create(name=name)
            user = User.objects.create_user(name.replace(" ", "_"))
            user.groups.add(group)
            cls.users[name] = user
        BcapArchesPermissionFramework.apply_permission_defaults()

    def _readable(self, user):
        return {
            str(graph_id)
            for graph_id in get_resource_types_by_perm(user, ["models.read_nodegroup"])
        }

    def test_granted_group_can_read_its_graph(self):
        readable = self._readable(self.users[Groups.ARCHAEOLOGY_BRANCH])
        self.assertIn(PERMIT_APPLICATION_GRAPH, readable)

    def test_guest_reads_nothing(self):
        readable = self._readable(self.users[Groups.GUEST])
        self.assertNotIn(ARCHAEOLOGICAL_SITE_GRAPH, readable)
        self.assertNotIn(PERMIT_APPLICATION_GRAPH, readable)
