"""BcapMessageService visibility: internal staff see every message on a
resource (internal-only included); an external applicant sees only those their
Contributor is party to, as author or recipient."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from bcap.builders.contributor_builder import ContributorSpec
from bcap.services.dashboard.contributor_service import ContributorService
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

    def test_internal_user_also_sees_internal_only_roots(self):
        # Internal users see every root; the internal-only ones are included, not
        # the only thing they see.
        ids = self._root_ids(self.staff)
        self.assertIn(str(self.internal_root.pk), ids)
        self.assertIn(str(self.internal_to_applicant.pk), ids)
        self.assertIn(str(self.public_root.pk), ids)

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

    def test_counts_only_unread_addressed_to_the_user_on_this_resource(self):
        self.assertEqual(
            self.service.unread_count_across([self.permit.pk], "reader"), 2
        )

    def test_unknown_username_counts_zero(self):
        self.assertEqual(
            self.service.unread_count_across([self.permit.pk], "nobody"), 0
        )

    def test_unread_count_across_rolls_up_every_context(self):
        # The two unread on the permit plus the one on the other resource are a
        # single rolled-up count, the shape the dashboard needs for a permit and
        # its related submission resources.
        self.assertEqual(
            self.service.unread_count_across(
                [self.permit.pk, self.other_permit.pk], "reader"
            ),
            3,
        )

    def test_unread_count_across_of_one_context_matches_unread_count(self):
        self.assertEqual(
            self.service.unread_count_across([self.permit.pk], "reader"), 2
        )

    def test_unread_count_across_empty_or_unknown_counts_zero(self):
        self.assertEqual(self.service.unread_count_across([], "reader"), 0)
        self.assertEqual(
            self.service.unread_count_across([self.permit.pk], "nobody"), 0
        )


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

    def test_external_poster_internal_flag_forced_off(self):
        data = self._payload(is_internal=True, recipient=self.staff_contrib)
        self.service.prepare_message(data, self.applicant)
        self.assertFalse(self.service._is_internal_payload(data))

    def test_internal_poster_keeps_the_internal_flag(self):
        data = self._payload(is_internal=True, recipient=self.staff_contrib)
        self.service.prepare_message(data, self.staff)
        self.assertTrue(self.service._is_internal_payload(data))

    def test_internal_message_to_external_recipient_is_rejected(self):
        data = self._payload(is_internal=True, recipient=self.applicant_contrib)
        with self.assertRaises(InternalMessageToExternal):
            self.service.prepare_message(data, self.staff)

    def test_internal_message_to_unlinked_recipient_is_rejected(self):
        # An unlinked Contributor is not staff, so it counts as external.
        data = self._payload(is_internal=True, recipient=self.unlinked)
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
        self.assertIsNone(contributors.contributor_username(str(self.unlinked.pk)))
