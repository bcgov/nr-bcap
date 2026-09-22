"""Thread visibility, resolution, archives, dates and unresolved counts."""

from unittest.mock import patch
from django.test import TestCase
from rest_framework.exceptions import PermissionDenied
from arches.app.models.models import ResourceInstance
from bcap.services.contributor.contributor_service import ContributorService
from bcap.services.message.message_context import MessageViewer
from bcap.services.message.thread_service import ThreadService
from tests.builders import FixtureBuilder
from tests.controlled_list_fixtures import ControlledListFixtures
from tests.permit_fixtures import RequirementRow, build_permit, make_requirement
from tests.services.contributor_fixtures import (
    ACTIVE,
    make_contributor,
    make_party,
    make_user,
)
from tests.services.message_fixtures import make_message, resolution


class BcapMessageVisibilityTests(TestCase):
    """Message visibility by the viewer's role, for both the thread listing and
    one thread's messages. Visibility is decided on the thread root."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = ThreadService()
        builder = FixtureBuilder()

        # A ministry staffer and two external applicants in the same company,
        # each backed by a Contributor the messages address.
        cls.acme = make_contributor(builder, "Acme Corp")
        cls.staff, staff_contrib = make_party(
            builder, "staff", "Sam", "Staff", internal=True
        )
        cls.applicant, applicant_contrib = make_party(
            builder, "applicant", "Amy", "Applicant", associated_organization=cls.acme
        )
        # In the company, so the permit is readable and the party filter is what
        # decides which of its messages they see.
        cls.outsider = make_party(
            builder, "outsider", "Otto", "Outsider", associated_organization=cls.acme
        )[0]
        cls.staff_contrib = staff_contrib
        cls.applicant_contrib = applicant_contrib
        cls.branch_id = ContributorService().archaeology_branch_id()

        cls.permit = build_permit(builder, "Threaded App", organization=cls.acme)
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
        # A reply flagged internal inside the public thread, as older data has
        # it: the thread decides, so the applicant still sees it.
        cls.stray_internal_reply = make_message(
            builder,
            context=cls.permit,
            author=staff_contrib,
            recipient=applicant_contrib,
            is_internal=True,
            subject="Flagged reply",
            root=cls.public_root,
        )
        # An internal thread between staff; the applicant is not party to it.
        cls.internal_root = make_message(
            builder,
            context=cls.permit,
            author=staff_contrib,
            recipient=staff_contrib,
            is_internal=True,
            subject="Internal note",
        )
        # An internal thread addressed TO the applicant: the party filter alone
        # would surface it, so the thread's internal flag is what must hide it.
        cls.internal_to_applicant = make_message(
            builder,
            context=cls.permit,
            author=staff_contrib,
            recipient=applicant_contrib,
            is_internal=True,
            subject="Internal, about the applicant",
        )
        # Staff writing to the applicant's company as a group.
        cls.to_company = make_message(
            builder,
            context=cls.permit,
            author=staff_contrib,
            recipient=cls.acme,
            subject="To the company",
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
        roots = self.service.thread_roots_query(self.permit_id, user)
        return {str(m.pk) for m in roots}

    def _thread_ids(self, root, user):
        messages = self.service.thread_messages_query(str(root.pk), user)
        return [str(m.pk) for m in messages]

    def test_being_party_is_not_enough_off_their_own_permits(self):
        # The applicant authored this one, but it files against a permit neither
        # they nor their company filed, so the base query drops it.
        visible = {
            str(m.pk) for m in self.service.base_query(MessageViewer(self.applicant))
        }
        self.assertNotIn(str(self.elsewhere.pk), visible)
        self.assertIn(str(self.public_root.pk), visible)

    def test_roots_exclude_replies_and_other_resources(self):
        ids = self._root_ids(self.staff)
        self.assertEqual(
            ids,
            {
                str(self.public_root.pk),
                str(self.internal_root.pk),
                str(self.internal_to_applicant.pk),
                str(self.to_company.pk),
            },
        )
        self.assertNotIn(str(self.public_reply.pk), ids)
        self.assertNotIn(str(self.elsewhere.pk), ids)

    def test_external_user_sees_external_roots_they_or_their_company_are_party_to(
        self,
    ):
        self.assertEqual(
            self._root_ids(self.applicant),
            {str(self.public_root.pk), str(self.to_company.pk)},
        )

    def test_a_thread_to_the_company_reaches_every_member(self):
        # The outsider is party to nothing personally, but is in the company.
        self.assertEqual(self._root_ids(self.outsider), {str(self.to_company.pk)})

    def test_external_party_still_cannot_open_an_internal_thread(self):
        self.assertEqual(
            self._thread_ids(self.internal_to_applicant, self.applicant), []
        )
        self.assertEqual(
            self._thread_ids(self.internal_to_applicant, self.staff),
            [str(self.internal_to_applicant.pk)],
        )

    def test_a_reply_is_visible_with_its_thread_whatever_its_own_flag(self):
        ids = self._thread_ids(self.public_root, self.applicant)
        self.assertIn(str(self.stray_internal_reply.pk), ids)

    def test_thread_returns_root_and_replies_oldest_first(self):
        ids = self._thread_ids(self.public_root, self.staff)
        self.assertEqual(
            ids,
            [
                str(self.public_root.pk),
                str(self.public_reply.pk),
                str(self.stray_internal_reply.pk),
            ],
        )

    def test_external_non_party_sees_nothing_of_internal_thread(self):
        self.assertEqual(self._thread_ids(self.internal_root, self.applicant), [])

    def test_internal_user_sees_internal_thread(self):
        ids = self._thread_ids(self.internal_root, self.staff)
        self.assertEqual(ids, [str(self.internal_root.pk)])

    def test_a_user_with_no_contributor_sees_nothing(self):
        stranger = make_user("visstranger")
        self.assertFalse(self.service.base_query(MessageViewer(stranger)).exists())

    def test_party_ids_span_self_company_and_branch_for_staff(self):
        self.assertEqual(
            MessageViewer(self.applicant).parties,
            {str(self.applicant_contrib.pk), str(self.acme.pk)},
        )
        self.assertEqual(
            MessageViewer(self.staff).parties,
            {str(self.staff_contrib.pk), self.branch_id},
        )

    def test_a_branch_membership_tile_does_not_make_an_applicant_staff(self):
        user, contrib = make_party(
            FixtureBuilder(),
            "visbranchmember",
            "Bea",
            "Member",
            associated_organization=ResourceInstance.objects.get(pk=self.branch_id),
            **ACTIVE,
        )
        self.assertEqual(MessageViewer(user).parties, {str(contrib.pk)})


class BcapMessageResolutionTests(TestCase):
    """Each side of a thread resolves for itself, on the root. Here the
    applicant started it, so they are the author side and staff the recipient
    side. Resolving from any message lands on the root and records who did it;
    a new message reopens the other side and leaves the poster's alone."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = ThreadService()
        builder = FixtureBuilder()

        cls.staff, cls.staff_contrib = make_party(
            builder, "resstaff", "Sam", "Staff", internal=True
        )
        cls.applicant, cls.applicant_contrib = make_party(
            builder, "resapp", "Amy", "Applicant"
        )
        cls.permit = builder.make_resource("permit_application")
        cls.root = make_message(
            builder,
            context=cls.permit,
            author=cls.applicant_contrib,
            recipient=cls.staff_contrib,
            subject="Root",
        )
        cls.reply = make_message(
            builder,
            context=cls.permit,
            author=cls.staff_contrib,
            recipient=cls.applicant_contrib,
            subject="Reply",
            root=cls.root,
        )

    def _resolve(self, user, message=None, resolved=True):
        self.service.set_viewer_resolution(
            (message or self.root).pk, {"resolved": resolved}, MessageViewer(user)
        )

    def test_each_party_resolves_only_their_own_side(self):
        for user, contrib, mine, other in (
            (self.staff, self.staff_contrib, "recipient", "author"),
            (self.applicant, self.applicant_contrib, "author", "recipient"),
        ):
            with self.subTest(side=mine):
                self._resolve(user)
                date, by = resolution(self.root, mine)
                self.assertIsNotNone(date)
                self.assertEqual(by, str(contrib.pk))
                self.assertEqual(resolution(self.root, other), (None, None))
                self._resolve(user, resolved=False)

    def test_resolving_from_a_reply_lands_on_the_root(self):
        self._resolve(self.staff, self.reply)
        self.assertIsNotNone(resolution(self.root, "recipient")[0])
        self.assertEqual(resolution(self.reply, "recipient"), (None, None))

    def test_reopening_clears_only_the_callers_side(self):
        self._resolve(self.staff)
        self._resolve(self.applicant)
        self._resolve(self.applicant, resolved=False)
        self.assertEqual(resolution(self.root, "author"), (None, None))
        self.assertIsNotNone(resolution(self.root, "recipient")[0])

    def test_a_body_without_the_flag_leaves_it_alone(self):
        self._resolve(self.staff)
        self.service.set_viewer_resolution(
            self.root.pk, {"archived": True}, MessageViewer(self.staff)
        )
        self.assertIsNotNone(resolution(self.root, "recipient")[0])

    def test_someone_on_neither_side_cannot_resolve(self):
        # A third staffer on a staff-to-staff thread is on neither side.
        builder = FixtureBuilder()
        oli = make_party(builder, "resoli", "Oli", "Other", internal=True)[1]
        pat = make_party(builder, "respat", "Pat", "Third", internal=True)[0]
        internal = make_message(
            builder,
            context=self.permit,
            author=self.staff_contrib,
            recipient=oli,
            is_internal=True,
            subject="Between two",
        )
        with self.assertRaises(PermissionDenied):
            self._resolve(pat, internal)

    def test_posting_reopens_the_other_side_and_leaves_the_posters(self):
        self._resolve(self.applicant)
        self._resolve(self.staff)
        self.service.after_post(self.reply.pk, self.staff)
        self.assertEqual(resolution(self.root, "author"), (None, None))
        self.assertEqual(
            resolution(self.root, "recipient")[1], str(self.staff_contrib.pk)
        )

    def test_staff_posting_leaves_their_side_open(self):
        self.service.after_post(self.reply.pk, self.staff)
        self.assertEqual(resolution(self.root, "recipient"), (None, None))

    def test_an_applicant_posting_resolves_their_side(self):
        self._resolve(self.staff)
        self.service.after_post(self.root.pk, self.applicant)
        self.assertEqual(
            resolution(self.root, "author")[1], str(self.applicant_contrib.pk)
        )
        self.assertEqual(resolution(self.root, "recipient"), (None, None))

    def test_reopening_an_open_side_writes_nothing(self):
        with patch("bcap.services.message.thread_service.Tile.save") as save:
            self._resolve(self.staff, resolved=False)
        save.assert_not_called()


class BcapMessageSideTests(TestCase):
    """Which side of a thread a viewer is on. When exactly one party is staff,
    all staff are that side and the other party's people the other; between
    staff it goes by the viewer's own parties, the author winning a tie."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = ThreadService()
        builder = FixtureBuilder()
        cls.acme = make_contributor(builder, "Acme Corp")
        cls.amy, cls.amy_contrib = make_party(
            builder, "sideamy", "Amy", "Applicant", associated_organization=cls.acme
        )
        cls.cal = make_party(
            builder, "sidecal", "Cal", "Colleague", associated_organization=cls.acme
        )[0]
        cls.sam, cls.sam_contrib = make_party(
            builder, "sidesam", "Sam", "Staff", internal=True
        )
        cls.oli, cls.oli_contrib = make_party(
            builder, "sideoli", "Oli", "Other", internal=True
        )
        cls.pat = make_party(builder, "sidepat", "Pat", "Third", internal=True)[0]
        cls.branch = ContributorService().archaeology_branch_id()

    def _side(self, user, author, recipient):
        return MessageViewer(user).side_of(str(author), str(recipient))

    def test_staff_to_a_company_splits_staff_from_its_members(self):
        for user in (self.sam, self.oli):
            self.assertEqual(
                self._side(user, self.sam_contrib.pk, self.acme.pk), "author"
            )
        for user in (self.amy, self.cal):
            self.assertEqual(
                self._side(user, self.sam_contrib.pk, self.acme.pk), "recipient"
            )

    def test_an_applicant_to_the_branch_puts_all_staff_on_the_recipient_side(self):
        self.assertEqual(
            self._side(self.amy, self.amy_contrib.pk, self.branch), "author"
        )
        self.assertEqual(
            self._side(self.oli, self.amy_contrib.pk, self.branch), "recipient"
        )

    def test_staff_to_staff_goes_by_the_viewers_own_parties(self):
        self.assertEqual(
            self._side(self.sam, self.sam_contrib.pk, self.oli_contrib.pk), "author"
        )
        self.assertEqual(
            self._side(self.oli, self.sam_contrib.pk, self.oli_contrib.pk),
            "recipient",
        )
        self.assertIsNone(
            self._side(self.pat, self.sam_contrib.pk, self.oli_contrib.pk)
        )

    def test_staff_to_the_branch_keeps_the_writer_on_the_author_side(self):
        self.assertEqual(
            self._side(self.sam, self.sam_contrib.pk, self.branch), "author"
        )
        self.assertEqual(
            self._side(self.oli, self.sam_contrib.pk, self.branch), "recipient"
        )


class BcapMessageUnresolvedCountTests(TestCase):
    """unresolved_counts_by_context counts, per resource, the viewer's visible,
    unarchived threads still open on their side. Each message is posted the way
    the create view does: it reopens the other side, and an applicant's own
    side resolves as they send while staff resolve by hand. Roots only, so a
    thread counts once."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = ThreadService()
        builder = FixtureBuilder()

        cls.acme = make_contributor(builder, "Acme Corp")
        cls.applicant, applicant_contrib = make_party(
            builder, "reader", "Amy", "Applicant", associated_organization=cls.acme
        )
        cls.colleague = make_party(
            builder, "colleague", "Cal", "Colleague", associated_organization=cls.acme
        )[0]
        cls.staff, staff_contrib = make_party(
            builder, "countstaff", "Sam", "Staff", internal=True
        )
        make_party(builder, "otherstaff", "Oli", "Other", internal=True)
        branch = ContributorService().archaeology_branch_id()
        cls.permit = build_permit(builder, "Counted App", organization=cls.acme)
        cls.other_permit = build_permit(builder, "Other App", organization=cls.acme)

        def post(user, author, recipient, subject, **kwargs):
            message = make_message(
                builder,
                context=kwargs.pop("context", cls.permit),
                author=author,
                recipient=recipient,
                subject=subject,
                **kwargs,
            )
            cls.service.after_post(message.pk, user)
            return message

        def from_staff(subject, recipient=applicant_contrib, **kwargs):
            return post(cls.staff, staff_contrib, recipient, subject, **kwargs)

        # Staff asked and resolved their side; the applicant's answer reopens it.
        cls.answered = from_staff("answered")
        cls.service.set_viewer_resolution(
            cls.answered.pk, {"resolved": True}, MessageViewer(cls.staff)
        )
        post(
            cls.applicant,
            applicant_contrib,
            staff_contrib,
            "answer",
            root=cls.answered,
        )
        # Staff asked, no answer yet: open for both sides until resolved.
        cls.asked = from_staff("asked")
        make_message(
            builder,
            context=cls.permit,
            author=staff_contrib,
            recipient=applicant_contrib,
            resolved_date="2026-02-01",
            subject="resolved",
        )
        from_staff("to the company", recipient=cls.acme)
        from_staff("internal", recipient=branch, is_internal=True)
        from_staff("elsewhere", context=cls.other_permit)
        # The applicant asked, no answer yet.
        cls.question = post(cls.applicant, applicant_contrib, staff_contrib, "question")

    def _count(self, username, *contexts):
        return self.service.unresolved_counts_by_context(
            [str(c.pk) for c in contexts], username
        )

    def test_an_applicant_counts_the_threads_they_have_not_answered(self):
        # Asked and to the company; what they wrote resolved as they sent it.
        self.assertEqual(
            self._count("reader", self.permit, self.other_permit),
            {str(self.permit.pk): 2, str(self.other_permit.pk): 1},
        )

    def test_a_company_member_counts_the_thread_to_the_company(self):
        self.assertEqual(
            self._count("colleague", self.permit), {str(self.permit.pk): 1}
        )

    def test_staff_count_their_open_threads_sent_ones_included(self):
        # Answered (reopened by the reply), asked, to the company, their own
        # internal note and the applicant's question.
        self.assertEqual(
            self._count("countstaff", self.permit), {str(self.permit.pk): 5}
        )

    def test_other_staff_count_the_internal_note_as_its_recipients(self):
        self.assertEqual(
            self._count("otherstaff", self.permit), {str(self.permit.pk): 5}
        )

    def test_resolving_clears_the_alert_for_that_side_only(self):
        for thread in (self.answered, self.asked):
            self.service.set_viewer_resolution(
                thread.pk, {"resolved": True}, MessageViewer(self.staff)
            )
        self.assertEqual(
            self._count("countstaff", self.permit), {str(self.permit.pk): 3}
        )
        self.assertEqual(self._count("reader", self.permit), {str(self.permit.pk): 2})

    def test_thread_roots_tell_each_viewer_their_side(self):
        def sides(user):
            return {
                str(root.pk): root.viewer_side
                for root in self.service.thread_roots_query(str(self.permit.pk), user)
            }

        staff, applicant = sides(self.staff), sides(self.applicant)
        self.assertEqual(staff[str(self.asked.pk)], "author")
        self.assertEqual(staff[str(self.question.pk)], "recipient")
        self.assertEqual(applicant[str(self.asked.pk)], "recipient")
        self.assertEqual(applicant[str(self.question.pk)], "author")

    def test_an_archived_thread_stops_counting_for_that_viewer_only(self):
        self.service.set_viewer_archived(
            self.asked.pk, {"archived": True}, MessageViewer(self.applicant)
        )
        self.assertEqual(self._count("reader", self.permit), {str(self.permit.pk): 1})
        self.assertEqual(
            self._count("countstaff", self.permit), {str(self.permit.pk): 5}
        )

    def test_no_contexts_or_an_unknown_user_counts_nothing(self):
        self.assertEqual(self._count("reader"), {})
        self.assertEqual(self._count("nobody", self.permit), {})


class BcapMessageArchiveTests(TestCase):
    """Archiving is personal: an archived_by tile on the thread root marks the
    thread archived for one viewer only, so one party archiving never hides it
    from another; it is root-scoped, so archiving from a reply archives the
    thread; and thread_roots_query splits each viewer's active vs archived threads."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = ThreadService()
        builder = FixtureBuilder()

        acme = make_contributor(builder, "Acme Corp")
        cls.staff, staff_contrib = make_party(
            builder, "archstaff", "Sam", "Staff", internal=True
        )
        cls.applicant, applicant_contrib = make_party(
            builder, "archapp", "Amy", "App", associated_organization=acme
        )
        cls.permit = build_permit(builder, "Archived App", organization=acme)
        cls.permit_id = str(cls.permit.pk)

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
        roots = self.service.thread_roots_query(self.permit_id, user, archived=archived)
        return {str(m.pk) for m in roots}

    def test_archive_is_per_viewer(self):
        self.service.set_viewer_archived(
            self.root.pk, {"archived": True}, MessageViewer(self.staff)
        )

        self.assertEqual(self._root_ids(self.staff, False), {str(self.other_root.pk)})
        self.assertEqual(self._root_ids(self.staff, True), {str(self.root.pk)})

        self.assertEqual(
            self._root_ids(self.applicant, False),
            {str(self.root.pk), str(self.other_root.pk)},
        )
        self.assertEqual(self._root_ids(self.applicant, True), set())

    def test_archiving_does_not_resolve_the_thread(self):
        self.service.update_thread_state(self.staff, self.root.pk, {"archived": True})
        for side in ("author", "recipient"):
            self.assertEqual(resolution(self.root, side), (None, None))

    def test_archiving_from_a_reply_archives_the_thread(self):
        self.service.set_viewer_archived(
            self.reply.pk, {"archived": True}, MessageViewer(self.staff)
        )
        self.assertEqual(self._root_ids(self.staff, True), {str(self.root.pk)})
        self.assertNotIn(str(self.root.pk), self._root_ids(self.staff, False))

    def test_unarchive_restores_the_thread(self):
        self.service.set_viewer_archived(
            self.root.pk, {"archived": True}, MessageViewer(self.staff)
        )
        self.service.set_viewer_archived(
            self.root.pk, {"archived": False}, MessageViewer(self.staff)
        )
        self.assertIn(str(self.root.pk), self._root_ids(self.staff, False))
        self.assertEqual(self._root_ids(self.staff, True), set())

    def test_new_message_unarchives_the_thread_for_all(self):
        self.service.set_viewer_archived(
            self.root.pk, {"archived": True}, MessageViewer(self.staff)
        )
        self.service.set_viewer_archived(
            self.root.pk, {"archived": True}, MessageViewer(self.applicant)
        )

        self.service.after_post(self.reply.pk, self.staff)

        self.assertEqual(self._root_ids(self.staff, True), set())
        self.assertEqual(self._root_ids(self.applicant, True), set())
        self.assertIn(str(self.root.pk), self._root_ids(self.staff, False))
        self.assertIn(str(self.root.pk), self._root_ids(self.applicant, False))

    def test_archiving_twice_is_idempotent(self):
        self.service.set_viewer_archived(
            self.root.pk, {"archived": True}, MessageViewer(self.staff)
        )
        self.service.set_viewer_archived(
            self.root.pk, {"archived": True}, MessageViewer(self.staff)
        )
        self.service.set_viewer_archived(
            self.root.pk, {"archived": False}, MessageViewer(self.staff)
        )
        self.assertEqual(self._root_ids(self.staff, True), set())

    def test_archive_is_a_noop_for_a_user_without_a_contributor(self):
        # Internal so the party-visibility gate does not also hide the threads.
        stranger = make_user("archstranger", internal=True)
        self.service.set_viewer_archived(
            self.root.pk, {"archived": True}, MessageViewer(stranger)
        )
        self.assertEqual(
            self._root_ids(stranger, False),
            {str(self.root.pk), str(self.other_root.pk)},
        )
        self.assertEqual(self._root_ids(stranger, True), set())


class BcapMessageThreadDateTests(TestCase):
    """thread_roots_query annotates each root with its thread's latest message date,
    rolled up from the root and its replies, independent of the viewer."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = ThreadService()
        builder = FixtureBuilder()

        cls.staff, recipient = make_party(
            builder, "datestaff", "Amy", "App", internal=True
        )
        cls.permit = builder.make_resource("permit_application")
        cls.permit_id = str(cls.permit.pk)

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
            for root in self.service.thread_roots_query(self.permit_id, self.staff)
        }
        self.assertEqual(dates[str(self.thread.pk)].date().isoformat(), "2026-01-05")
        self.assertEqual(dates[str(self.lone.pk)].date().isoformat(), "2026-02-01")


class BcapMessageModuleUnresolvedTests(TestCase):
    """unresolved_counts_by_module sums the viewer's unresolved threads over each
    module's requirements, the resources the requirement message dialogs file
    against."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = ThreadService()
        builder = FixtureBuilder()

        # Internal, so the submission gate lets the reader through to a permit
        # they did not file.
        cls.reader, recipient = make_party(
            builder, "modreader", "Amy", "App", internal=True
        )
        first = make_requirement(builder, "mod-first")
        second = make_requirement(builder, "mod-second")
        cls.submission = build_permit(
            builder,
            "Modules",
            [RequirementRow(first), RequirementRow(second, order=2)],
        )
        make_message(builder, context=first, recipient=recipient, subject="1")
        make_message(builder, context=first, recipient=recipient, subject="2")
        make_message(builder, context=second, recipient=recipient, subject="3")
        make_message(
            builder,
            context=second,
            recipient=recipient,
            resolved_date="2026-02-01",
            subject="done",
        )

    def test_unresolved_counts_by_module_sums_the_modules_requirements(self):
        rows = self.service.unresolved_counts_by_module(
            str(self.submission.pk), self.reader
        )
        self.assertEqual([row.unresolved_count for row in rows], [3])

    def test_unresolved_counts_by_module_denies_a_submission_the_caller_cannot_reach(
        self,
    ):
        with self.assertRaises(PermissionDenied):
            self.service.unresolved_counts_by_module(
                str(self.submission.pk), make_user("modoutsider")
            )
