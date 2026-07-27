"""BcapMessageService visibility: internal staff see every message on a
resource (internal-only included); an external applicant sees only those their
Contributor is party to, as author or recipient."""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from bcap.builders.contributor_builder import ContributorSpec
from bcap.services.contributor_service import ContributorService
from bcap.services.message.bcap_message_service import (
    BcapMessageService,
    InternalMessageToExternal,
    NoAuthorContributor,
)
from bcap.util.aliases.bcap_message import BcapMessageAliases as A
from bcap.util.controlled_list import reference_value
from tests.builders import FixtureBuilder
from tests.controlled_list_fixtures import ControlledListFixtures


def make_user(username, internal=False):
    user = get_user_model().objects.create_user(username=username, password="pass")
    if internal:
        user.groups.add(Group.objects.get(name="Resource Editor"))
    return user


def _datetime(day):
    """Widen a bare day to midnight UTC, since the message date nodes are
    datetime-with-timezone. An explicit offset (not a Z) keeps the day from
    shifting under a non-UTC local zone."""
    if day is None:
        return None
    return f"{day} 00:00:00+00:00"


def make_message(
    builder,
    *,
    context,
    author=None,
    recipient=None,
    is_internal=False,
    subject="",
    read_date=None,
    created=None,
    root=None,
):
    """A bcap_message on a parent resource, optionally a reply within a thread."""
    message = builder.new_resource("bcap_message")
    builder.append_blank_tile_for_group(
        message,
        A.MESSAGE_CONTENT,  # the main nodegroup is named after its content node
        {
            A.MESSAGE_SUBJECT: builder.localized(subject),
            A.MESSAGE_CONTENT: builder.localized(subject),
            A.MESSAGE_AUTHOR: author,
            A.RECIPIENT: recipient,
            A.RESOURCE_CONTEXT: context,
            A.IS_INTERNAL: is_internal,
            A.MESSAGE_READ_DATE: _datetime(read_date),
            A.MESSAGE_CREATION_DATE: _datetime(created),
        },
    )
    if root is not None:
        builder.append_blank_tile_for_group(
            message, A.RELATED_SOURCE_MESSAGE, {A.RELATED_SOURCE_MESSAGE: root}
        )
    message.save(**builder.save_kwargs)
    builder.claim(message)
    return message


class BcapMessageVisibilityTests(TestCase):
    """fetch_roots / fetch_thread gate message visibility by the viewer's role."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = BcapMessageService()
        builder = FixtureBuilder()
        contributor_type = reference_value("contributor", "contributor_type")

        # A ministry staffer and two external applicants, each backed by a
        # Contributor the messages address (party membership is looked up by the
        # Contributor's bcap_username).
        cls.staff = make_user("staff", internal=True)
        cls.applicant = make_user("applicant")
        cls.outsider = make_user("outsider")

        staff_contrib = builder.make_contributor(
            ContributorSpec(contributor_type, "Sam", "Staff", bcap_username="staff")
        )
        applicant_contrib = builder.make_contributor(
            ContributorSpec(
                contributor_type, "Amy", "Applicant", bcap_username="applicant"
            )
        )
        cls.staff_contrib = staff_contrib
        cls.applicant_contrib = applicant_contrib

        # The parent resource the thread hangs off, plus an unrelated one to
        # prove the resource filter.
        cls.permit = builder.make_resource("permit_application")
        cls.other_permit = builder.make_resource("permit_application")
        cls.permit_id = str(cls.permit.pk)

        # A public thread the applicant started, with a staff reply.
        cls.public_root = make_message(
            builder,
            context=cls.permit,
            author=applicant_contrib,
            recipient=staff_contrib,
            subject="Public question",
        )
        cls.public_reply = make_message(
            builder,
            context=cls.permit,
            author=staff_contrib,
            recipient=applicant_contrib,
            subject="Public answer",
            root=cls.public_root,
        )
        # An internal-only note between staff; the applicant is not party to it.
        cls.internal_root = make_message(
            builder,
            context=cls.permit,
            author=staff_contrib,
            recipient=staff_contrib,
            is_internal=True,
            subject="Internal note",
        )
        # An internal-only note addressed TO the applicant: the party filter alone
        # would surface it, so the is_internal exclusion is what must hide it.
        cls.internal_to_applicant = make_message(
            builder,
            context=cls.permit,
            author=staff_contrib,
            recipient=applicant_contrib,
            is_internal=True,
            subject="Internal, about the applicant",
        )
        # A root on a different resource, which must never leak into this one.
        cls.elsewhere = make_message(
            builder,
            context=cls.other_permit,
            author=applicant_contrib,
            recipient=staff_contrib,
            subject="Different permit",
        )

    def _root_ids(self, user):
        roots = self.service.root_queryset(self.permit_id, user)
        return {str(m.pk) for m in roots}

    def _thread_ids(self, root, user):
        messages = self.service.thread_queryset(str(root.pk), user)
        return [str(m.pk) for m in messages]

    def test_roots_exclude_replies_and_other_resources(self):
        # Roots are thread-starters (no related_source_message) on this resource
        # only; the reply and the other permit's message are excluded.
        ids = self._root_ids(self.staff)
        self.assertEqual(
            ids,
            {
                str(self.public_root.pk),
                str(self.internal_root.pk),
                str(self.internal_to_applicant.pk),
            },
        )
        self.assertNotIn(str(self.public_reply.pk), ids)
        self.assertNotIn(str(self.elsewhere.pk), ids)

    def test_external_user_sees_only_roots_they_are_party_to(self):
        # The applicant sees only the public root: not the staff-only note (not
        # party), and not the internal note addressed to them (party, but
        # is_internal keeps it internal-only).
        self.assertEqual(self._root_ids(self.applicant), {str(self.public_root.pk)})

    def test_external_party_still_cannot_open_an_internal_thread(self):
        # The applicant is the recipient of this internal note, yet the
        # is_internal exclusion still blocks the whole thread from them.
        self.assertEqual(
            self._thread_ids(self.internal_to_applicant, self.applicant), []
        )
        self.assertEqual(
            self._thread_ids(self.internal_to_applicant, self.staff),
            [str(self.internal_to_applicant.pk)],
        )

    def test_is_unread_only_for_messages_addressed_to_the_viewer(self):
        # A message is unread to a viewer only when addressed to them and not yet
        # read; a message they authored is never unread to them.
        applicant_view = {
            str(m.pk): m.is_unread
            for m in self.service.thread_queryset(
                str(self.public_root.pk), self.applicant
            )
        }
        # The applicant authored the root (not unread) and is the reply's recipient.
        self.assertFalse(applicant_view[str(self.public_root.pk)])
        self.assertTrue(applicant_view[str(self.public_reply.pk)])

        staff_view = {
            str(m.pk): m.is_unread
            for m in self.service.thread_queryset(str(self.public_root.pk), self.staff)
        }
        # Mirror image: staff is the root's recipient, and authored the reply.
        self.assertTrue(staff_view[str(self.public_root.pk)])
        self.assertFalse(staff_view[str(self.public_reply.pk)])

    def test_external_user_party_to_nothing_sees_no_roots(self):
        self.assertEqual(self._root_ids(self.outsider), set())

    def test_thread_returns_root_and_replies_oldest_first(self):
        ids = self._thread_ids(self.public_root, self.staff)
        self.assertEqual(ids, [str(self.public_root.pk), str(self.public_reply.pk)])

    def test_external_party_sees_full_public_thread(self):
        # The applicant is author of the root and recipient of the reply.
        ids = self._thread_ids(self.public_root, self.applicant)
        self.assertEqual(ids, [str(self.public_root.pk), str(self.public_reply.pk)])

    def test_external_non_party_sees_nothing_of_internal_thread(self):
        self.assertEqual(self._thread_ids(self.internal_root, self.applicant), [])

    def test_internal_user_sees_internal_thread(self):
        ids = self._thread_ids(self.internal_root, self.staff)
        self.assertEqual(ids, [str(self.internal_root.pk)])


class BcapMessageUnreadCountTests(TestCase):
    """unread_count: messages on a resource addressed to a username, still unread."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = BcapMessageService()
        builder = FixtureBuilder()
        contributor_type = reference_value("contributor", "contributor_type")

        cls.applicant = make_user("reader")
        applicant_contrib = builder.make_contributor(
            ContributorSpec(
                contributor_type, "Amy", "Applicant", bcap_username="reader"
            )
        )
        staff_contrib = builder.make_contributor(
            ContributorSpec(contributor_type, "Sam", "Staff", bcap_username="staff2")
        )
        cls.permit = builder.make_resource("permit_application")
        cls.other_permit = builder.make_resource("permit_application")

        # Two unread messages to the applicant, one already read, one addressed
        # to staff, and one on a different resource.
        make_message(
            builder, context=cls.permit, recipient=applicant_contrib, subject="a"
        )
        make_message(
            builder, context=cls.permit, recipient=applicant_contrib, subject="b"
        )
        make_message(
            builder,
            context=cls.permit,
            recipient=applicant_contrib,
            read_date="2026-02-01",
            subject="read",
        )
        make_message(
            builder, context=cls.permit, recipient=staff_contrib, subject="staff"
        )
        make_message(
            builder,
            context=cls.other_permit,
            recipient=applicant_contrib,
            subject="elsewhere",
        )

    def test_unread_count_across(self):
        count = self.service.unread_count_across
        # Only unread messages addressed to the user on the given resources: two
        # on the permit, and rolled up with the other resource makes three (the
        # shape the dashboard needs for a permit and its related submissions).
        self.assertEqual(count([self.permit.pk], "reader"), 2)
        self.assertEqual(count([self.permit.pk, self.other_permit.pk], "reader"), 3)
        # No resources or an unknown user counts zero.
        self.assertEqual(count([], "reader"), 0)
        self.assertEqual(count([self.permit.pk], "nobody"), 0)


class BcapMessageThreadUnreadCountTests(TestCase):
    """root_queryset annotates each thread root with the viewer's unread count
    for the whole thread: a reply's unread rolls up to its root, while read
    messages and messages addressed to another viewer do not count."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = BcapMessageService()
        builder = FixtureBuilder()
        contributor_type = reference_value("contributor", "contributor_type")

        cls.staff = make_user("threadstaff", internal=True)
        cls.applicant = make_user("threadapp")
        staff_contrib = builder.make_contributor(
            ContributorSpec(
                contributor_type, "Sam", "Staff", bcap_username="threadstaff"
            )
        )
        applicant_contrib = builder.make_contributor(
            ContributorSpec(contributor_type, "Amy", "App", bcap_username="threadapp")
        )
        cls.permit = builder.make_resource("permit_application")
        cls.permit_id = str(cls.permit.pk)

        # Thread A: root and reply both unread to the applicant -> the root
        # carries the whole thread's unread count of 2 for the applicant.
        cls.thread_a = make_message(
            builder, context=cls.permit, recipient=applicant_contrib, subject="a-root"
        )
        make_message(
            builder,
            context=cls.permit,
            recipient=applicant_contrib,
            subject="a-reply",
            root=cls.thread_a,
        )
        # Thread B: root read by the applicant, reply unread to staff. The
        # applicant has 0 unread here; staff has 1.
        cls.thread_b = make_message(
            builder,
            context=cls.permit,
            recipient=applicant_contrib,
            read_date="2026-02-01",
            subject="b-root",
        )
        make_message(
            builder,
            context=cls.permit,
            recipient=staff_contrib,
            subject="b-reply",
            root=cls.thread_b,
        )

    def _unread_by_root(self, user):
        roots = self.service.root_queryset(self.permit_id, user)
        return {str(root.pk): root.unread_count for root in roots}

    def test_reply_unread_rolls_up_to_root(self):
        counts = self._unread_by_root(self.applicant)
        self.assertEqual(counts[str(self.thread_a.pk)], 2)
        # Read root and a reply addressed to someone else both count zero.
        self.assertEqual(counts[str(self.thread_b.pk)], 0)

    def test_unread_count_is_per_viewer(self):
        counts = self._unread_by_root(self.staff)
        # Staff is party to none of thread A, but the reply in thread B is to them.
        self.assertEqual(counts[str(self.thread_a.pk)], 0)
        self.assertEqual(counts[str(self.thread_b.pk)], 1)


class BcapMessageArchiveTests(TestCase):
    """Archiving is personal: an archived_by tile on the thread root marks the
    thread archived for one viewer only, so one party archiving never hides it
    from another; it is root-scoped, so archiving from a reply archives the
    thread; and root_queryset splits each viewer's active vs archived threads."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = BcapMessageService()
        builder = FixtureBuilder()
        contributor_type = reference_value("contributor", "contributor_type")

        # A staffer and an applicant, both party to the thread (author of one
        # message, recipient of another) so each can see it and archive it.
        cls.staff = make_user("archstaff", internal=True)
        cls.applicant = make_user("archapp")
        staff_contrib = builder.make_contributor(
            ContributorSpec(contributor_type, "Sam", "Staff", bcap_username="archstaff")
        )
        applicant_contrib = builder.make_contributor(
            ContributorSpec(contributor_type, "Amy", "App", bcap_username="archapp")
        )
        cls.permit = builder.make_resource("permit_application")
        cls.permit_id = str(cls.permit.pk)

        # One thread (root + reply) and a second standalone thread on the same
        # resource, to prove the archived filter selects between them.
        cls.root = make_message(
            builder,
            context=cls.permit,
            author=applicant_contrib,
            recipient=staff_contrib,
            subject="Root",
        )
        cls.reply = make_message(
            builder,
            context=cls.permit,
            author=staff_contrib,
            recipient=applicant_contrib,
            subject="Reply",
            root=cls.root,
        )
        cls.other_root = make_message(
            builder,
            context=cls.permit,
            author=applicant_contrib,
            recipient=staff_contrib,
            subject="Other",
        )

    def _root_ids(self, user, archived):
        roots = self.service.root_queryset(self.permit_id, user, archived=archived)
        return {str(m.pk) for m in roots}

    def test_archive_is_per_viewer(self):
        # Staff archives the thread; it moves to staff's archived list but the
        # applicant's view is untouched, the leak the single-flag design had.
        self.service.set_archived_state(self.root.pk, {"archived": True}, "archstaff")

        self.assertEqual(self._root_ids(self.staff, False), {str(self.other_root.pk)})
        self.assertEqual(self._root_ids(self.staff, True), {str(self.root.pk)})

        self.assertEqual(
            self._root_ids(self.applicant, False),
            {str(self.root.pk), str(self.other_root.pk)},
        )
        self.assertEqual(self._root_ids(self.applicant, True), set())

    def test_archiving_from_a_reply_archives_the_thread(self):
        # The action can come from any message; it lands on the root, which is
        # what the listing filters on.
        self.service.set_archived_state(self.reply.pk, {"archived": True}, "archstaff")
        self.assertEqual(self._root_ids(self.staff, True), {str(self.root.pk)})
        self.assertNotIn(str(self.root.pk), self._root_ids(self.staff, False))

    def test_unarchive_restores_the_thread(self):
        self.service.set_archived_state(self.root.pk, {"archived": True}, "archstaff")
        self.service.set_archived_state(self.root.pk, {"archived": False}, "archstaff")
        self.assertIn(str(self.root.pk), self._root_ids(self.staff, False))
        self.assertEqual(self._root_ids(self.staff, True), set())

    def test_new_message_unarchives_the_thread_for_all(self):
        # Both parties file the thread away; a new message must resurface it for
        # everyone, not just the poster. Passing a reply id also proves it lands
        # on the root the listing filters on.
        self.service.set_archived_state(self.root.pk, {"archived": True}, "archstaff")
        self.service.set_archived_state(self.root.pk, {"archived": True}, "archapp")
        self.assertEqual(self._root_ids(self.staff, True), {str(self.root.pk)})
        self.assertEqual(self._root_ids(self.applicant, True), {str(self.root.pk)})

        self.service.unarchive_thread_for_all(self.reply.pk)

        self.assertEqual(self._root_ids(self.staff, True), set())
        self.assertEqual(self._root_ids(self.applicant, True), set())
        self.assertIn(str(self.root.pk), self._root_ids(self.staff, False))
        self.assertIn(str(self.root.pk), self._root_ids(self.applicant, False))

    def test_archiving_twice_is_idempotent(self):
        # A second archive must not add a duplicate tile; unarchiving once still
        # fully clears it.
        self.service.set_archived_state(self.root.pk, {"archived": True}, "archstaff")
        self.service.set_archived_state(self.root.pk, {"archived": True}, "archstaff")
        self.service.set_archived_state(self.root.pk, {"archived": False}, "archstaff")
        self.assertEqual(self._root_ids(self.staff, True), set())

    def test_archive_is_a_noop_for_a_user_without_a_contributor(self):
        # Internal so the party-visibility gate does not also hide the threads;
        # this isolates the archive path for a user with no Contributor to key on.
        stranger = make_user("archstranger", internal=True)
        self.service.set_archived_state(
            self.root.pk, {"archived": True}, "archstranger"
        )
        # Nothing archived, and their views degrade to all-active / none-archived.
        self.assertEqual(
            self._root_ids(stranger, False),
            {str(self.root.pk), str(self.other_root.pk)},
        )
        self.assertEqual(self._root_ids(stranger, True), set())

    def test_read_setter_noops_without_its_node(self):
        # A body carrying no read date (e.g. an archive-only PATCH) leaves the
        # read state untouched, so read and archive share one endpoint safely.
        self.assertIsNone(self.service.set_read_state(self.root.pk, {}))


class BcapMessagePartyAndPayloadTests(TestCase):
    """The party filter and the create-payload resource_context reader."""

    def _payload(self, node_value):
        return {
            "aliased_data": {
                A.MESSAGE_CONTENT: {
                    "aliased_data": {
                        A.RESOURCE_CONTEXT: {"node_value": node_value},
                    }
                }
            }
        }

    def test_resource_context_id_reads_the_target_from_a_payload(self):
        # The canonical write form: node_value is a one-element resource-instance
        # list, matching what the API reads back.
        resource_id = "11111111-1111-1111-1111-111111111111"
        payload = self._payload([{"resourceId": resource_id}])
        self.assertEqual(BcapMessageService.resource_context_id(payload), resource_id)

    def test_resource_context_id_reads_a_bare_object_node_value(self):
        # The pre-list write form (a bare object) is still accepted.
        resource_id = "22222222-2222-2222-2222-222222222222"
        payload = self._payload({"resourceId": resource_id})
        self.assertEqual(BcapMessageService.resource_context_id(payload), resource_id)

    def test_resource_context_id_is_none_when_absent(self):
        self.assertIsNone(BcapMessageService.resource_context_id({}))

    def test_set_author_raises_when_the_user_has_no_contributor(self):
        # A message must have a resolvable author, so an unmapped username is
        # rejected rather than leaving the author blank.
        with self.assertRaises(NoAuthorContributor):
            BcapMessageService.set_author(self._payload([]), "nobody")


class BcapMessagePrepareTests(TestCase):
    """prepare_message: author stamping, the external internal-flag override, and
    the internal-to-external recipient guard."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = BcapMessageService()
        builder = FixtureBuilder()
        contributor_type = reference_value("contributor", "contributor_type")

        cls.staff = make_user("prepstaff", internal=True)
        cls.applicant = make_user("prepapp")
        cls.staff_contrib = builder.make_contributor(
            ContributorSpec(contributor_type, "Sam", "Staff", bcap_username="prepstaff")
        )
        cls.applicant_contrib = builder.make_contributor(
            ContributorSpec(
                contributor_type, "Amy", "Applicant", bcap_username="prepapp"
            )
        )
        cls.unlinked = builder.make_contributor(
            ContributorSpec(contributor_type, "Uma", "Unlinked")
        )

    def _payload(self, *, is_internal=None, recipient=None):
        content = {}
        if is_internal is not None:
            content[A.IS_INTERNAL] = {"node_value": is_internal}
        if recipient is not None:
            content[A.RECIPIENT] = {"node_value": [{"resourceId": str(recipient.pk)}]}
        return {"aliased_data": {A.MESSAGE_CONTENT: {"aliased_data": content}}}

    def _content(self, data):
        return data["aliased_data"][A.MESSAGE_CONTENT]["aliased_data"]

    def _author_id(self, data):
        return self._content(data)[A.MESSAGE_AUTHOR]["node_value"][0]["resourceId"]

    def test_author_is_the_posting_user(self):
        data = self._payload()
        self.service.prepare_message(data, self.applicant)
        self.assertEqual(self._author_id(data), str(self.applicant_contrib.pk))

    def test_internal_flag_honored_only_for_internal_posters(self):
        # An external poster's internal flag is forced off; an internal poster's
        # is kept.
        external = self._payload(is_internal=True, recipient=self.staff_contrib)
        self.service.prepare_message(external, self.applicant)
        self.assertFalse(self.service._is_internal_payload(external))

        internal = self._payload(is_internal=True, recipient=self.staff_contrib)
        self.service.prepare_message(internal, self.staff)
        self.assertTrue(self.service._is_internal_payload(internal))

    def test_internal_message_to_a_non_staff_recipient_is_rejected(self):
        # An external applicant, and an unlinked Contributor (not staff either),
        # both count as external and are rejected.
        for recipient in (self.applicant_contrib, self.unlinked):
            data = self._payload(is_internal=True, recipient=recipient)
            with self.assertRaises(InternalMessageToExternal):
                self.service.prepare_message(data, self.staff)

    def test_internal_message_without_a_recipient_is_allowed(self):
        data = self._payload(is_internal=True)
        self.service.prepare_message(data, self.staff)  # no raise

    def test_prepare_message_requires_the_poster_to_have_a_contributor(self):
        stranger = make_user("prepstranger")
        with self.assertRaises(NoAuthorContributor):
            self.service.prepare_message(self._payload(), stranger)

    def test_contributor_username_reads_the_link(self):
        contributors = ContributorService()
        self.assertEqual(
            contributors.contributor_username(str(self.staff_contrib.pk)), "prepstaff"
        )


class BcapMessageThreadDateTests(TestCase):
    """root_queryset annotates each root with its thread's latest message date,
    rolled up from the root and its replies, independent of the viewer."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = BcapMessageService()
        builder = FixtureBuilder()
        contributor_type = reference_value("contributor", "contributor_type")

        cls.staff = make_user("datestaff", internal=True)
        recipient = builder.make_contributor(
            ContributorSpec(contributor_type, "Amy", "App", bcap_username="datestaff")
        )
        cls.permit = builder.make_resource("permit_application")
        cls.permit_id = str(cls.permit.pk)

        # A thread whose reply is newer than its root, so the reply's date wins.
        cls.thread = make_message(
            builder,
            context=cls.permit,
            recipient=recipient,
            subject="root",
            created="2026-01-01",
        )
        make_message(
            builder,
            context=cls.permit,
            recipient=recipient,
            subject="reply",
            created="2026-01-05",
            root=cls.thread,
        )
        # A lone root carries its own date.
        cls.lone = make_message(
            builder,
            context=cls.permit,
            recipient=recipient,
            subject="lone",
            created="2026-02-01",
        )

    def test_last_message_date_is_the_threads_latest(self):
        dates = {
            str(root.pk): root.last_message_date
            for root in self.service.root_queryset(self.permit_id, self.staff)
        }
        # A datetime, formatted client-side. The reply is newer than its root, so
        # the reply's date is the one that rolls up.
        self.assertEqual(dates[str(self.thread.pk)].date().isoformat(), "2026-01-05")
        self.assertEqual(dates[str(self.lone.pk)].date().isoformat(), "2026-02-01")


class BcapMessageModuleUnreadTests(TestCase):
    """unread_by_module maps each of a submission's process_module tiles to the
    viewer's unread count on the resource that module's messages file against."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = BcapMessageService()
        builder = FixtureBuilder()
        contributor_type = reference_value("contributor", "contributor_type")

        cls.reader = make_user("modreader")
        recipient = builder.make_contributor(
            ContributorSpec(contributor_type, "Amy", "App", bcap_username="modreader")
        )
        # Two resources a module's messages could file against: one with two
        # unread messages to the reader, one with none.
        cls.hosted = builder.make_resource("permit_application")
        cls.empty = builder.make_resource("permit_application")
        make_message(builder, context=cls.hosted, recipient=recipient, subject="1")
        make_message(builder, context=cls.hosted, recipient=recipient, subject="2")

    def test_unread_by_module_counts_per_module_context(self):
        # Stub the module-to-context mapping so the count roll-up is what's under
        # test; each ModuleUnread carries its module tile id and the context's
        # unread count (zero when the context has none).
        contexts = {
            "module-hosted": str(self.hosted.pk),
            "module-empty": str(self.empty.pk),
        }
        with patch(
            "bcap.services.message.bcap_message_service.ProcessRequirementService"
        ) as service:
            service.return_value.module_message_contexts.return_value = contexts
            rows = self.service.unread_by_module("permit-x", "modreader")

        self.assertEqual(
            {row.module_id: row.unread_count for row in rows},
            {"module-hosted": 2, "module-empty": 0},
        )
