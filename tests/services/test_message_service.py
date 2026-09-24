"""Message payload preparation and address options."""

from django.test import TestCase
from rest_framework.exceptions import PermissionDenied
from arches.app.models.models import ResourceInstance
from bcap.services.contributor.contributor_service import ContributorService
from bcap.services.message.message_context import MessageViewer
from bcap.services.message.message_service import MessageService, NoAuthorContributor
from bcap.util.aliases.bcap_message import BcapMessageAliases as A
from tests.builders import FixtureBuilder
from tests.controlled_list_fixtures import ControlledListFixtures
from tests.permit_fixtures import RequirementRow, build_permit, make_requirement
from tests.services.contributor_fixtures import (
    make_contributor,
    make_party,
    make_user,
)
from tests.services.message_fixtures import make_message


class BcapMessageAuthorTests(TestCase):
    def test_stamp_author_raises_when_the_user_has_no_contributor(self):
        with self.assertRaises(NoAuthorContributor):
            MessageService.stamp_author({}, MessageViewer(make_user("nobody")))


class BcapMessagePrepareTests(TestCase):
    """prepare_create_payload: author stamping, how a new thread decides it is internal,
    and how a reply takes its thread's fields."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = MessageService()
        builder = FixtureBuilder()

        cls.staff, cls.staff_contrib = make_party(
            builder, "prepstaff", "Sam", "Staff", internal=True
        )
        cls.applicant, cls.applicant_contrib = make_party(
            builder, "prepapp", "Amy", "Applicant"
        )
        cls.unlinked = make_contributor(builder, "Unlinked", "Uma")
        cls.third, cls.third_contrib = make_party(
            builder, "prepthird", "Tia", "Third", internal=True
        )
        cls.stranger = make_party(builder, "prepstranger", "Stu", "Stranger")[0]
        cls.branch = ContributorService().archaeology_branch_id()
        # Filed by the applicant under no company, so posting to it clears the
        # edit gate prepare_create_payload ends on.
        cls.permit = builder.make_resource("permit_application")
        ResourceInstance.objects.filter(pk=cls.permit.pk).update(
            principaluser=cls.applicant
        )
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
            subject="Root",
            root=cls.root,
        )
        cls.staff_root = make_message(
            builder,
            context=cls.permit,
            author=cls.staff_contrib,
            recipient=cls.applicant_contrib,
            subject="From staff",
        )
        cls.internal_root = make_message(
            builder,
            context=cls.permit,
            author=cls.staff_contrib,
            recipient=cls.third_contrib,
            is_internal=True,
            subject="Internal",
        )

    # A type the client might send that is not the thread's.
    OTHER_TYPE = [{"uri": "https://bcap.test/clm/other", "labels": []}]

    def _payload(
        self,
        *,
        is_internal=None,
        recipient=None,
        thread=None,
        subject=None,
        message_type=None,
        resolved_date=None,
    ):
        # Every real create carries the resource the message files against; the
        # edit gate reads it off the payload.
        content = {
            A.RESOURCE_CONTEXT: {"node_value": [{"resourceId": str(self.permit.pk)}]}
        }
        if is_internal is not None:
            content[A.IS_INTERNAL] = {"node_value": is_internal}
        if recipient is not None:
            content[A.RECIPIENT] = {"node_value": [{"resourceId": str(recipient)}]}
        if subject is not None:
            content[A.MESSAGE_SUBJECT] = {
                "node_value": {"en": {"value": subject, "direction": "ltr"}}
            }
        if message_type is not None:
            content[A.MESSAGE_TYPE] = {"node_value": message_type}
        if resolved_date is not None:
            content[A.THREAD_AUTHOR_RESOLVED_DATE] = {"node_value": resolved_date}
            content[A.THREAD_RECIPIENT_RESOLVED_DATE] = {"node_value": resolved_date}
        if thread is not None:
            content[A.THREAD] = {"node_value": [{"resourceId": str(thread.pk)}]}
        return {"aliased_data": {A.MESSAGE_CONTENT: {"aliased_data": content}}}

    def _content(self, data):
        return data["aliased_data"][A.MESSAGE_CONTENT]["aliased_data"]

    def _author_id(self, data):
        return self._content(data)[A.MESSAGE_AUTHOR]["node_value"][0]["resourceId"]

    def _recipient_id(self, data):
        return self._content(data)[A.RECIPIENT]["node_value"][0]["resourceId"]

    def _subject(self, data):
        return self._content(data)[A.MESSAGE_SUBJECT]["node_value"]["en"]["value"]

    def _message_type(self, data):
        return self._content(data)[A.MESSAGE_TYPE]["node_value"]

    def _is_internal(self, data):
        return self._content(data)[A.IS_INTERNAL]["node_value"]

    def _thread(self, data):
        return self._content(data)[A.THREAD]["node_value"][0]["resourceId"]

    def test_author_is_the_posting_user(self):
        data = self._payload()
        self.service.prepare_create_payload(data, self.applicant)
        self.assertEqual(self._author_id(data), str(self.applicant_contrib.pk))

    def test_staff_writing_to_staff_or_the_branch_starts_an_internal_thread(self):
        for recipient in (self.third_contrib.pk, self.branch):
            data = self._payload(recipient=recipient)
            self.service.prepare_create_payload(data, self.staff)
            self.assertIs(self._is_internal(data), True)

    def test_staff_writing_outside_the_branch_starts_a_shared_thread(self):
        for recipient in (self.applicant_contrib.pk, self.unlinked.pk):
            data = self._payload(recipient=recipient, is_internal=True)
            self.service.prepare_create_payload(data, self.staff)
            self.assertIs(self._is_internal(data), False)

    def test_an_applicant_never_starts_an_internal_thread(self):
        data = self._payload(recipient=self.staff_contrib.pk, is_internal=True)
        self.service.prepare_create_payload(data, self.applicant)
        self.assertIs(self._is_internal(data), False)

    def test_a_thread_with_no_recipient_is_shared(self):
        data = self._payload(is_internal=True)
        self.service.prepare_create_payload(data, self.staff)
        self.assertIs(self._is_internal(data), False)

    def test_a_create_cannot_set_the_threads_state(self):
        data = self._payload(resolved_date="2026-01-01T00:00:00Z")
        self._content(data).update(
            {
                A.THREAD_PARTICIPANTS: {
                    "node_value": [{"resourceId": str(self.applicant_contrib.pk)}]
                },
                A.THREAD_ANSWERED: {"node_value": True},
                A.THREAD_LAST_MESSAGE_DATE: {"node_value": "2026-01-01T00:00:00Z"},
            }
        )
        self.service.prepare_create_payload(data, self.applicant)
        for alias in (
            A.THREAD_AUTHOR_RESOLVED_DATE,
            A.THREAD_AUTHOR_RESOLVED_BY,
            A.THREAD_RECIPIENT_RESOLVED_DATE,
            A.THREAD_RECIPIENT_RESOLVED_BY,
            A.THREAD_PARTICIPANTS,
            A.THREAD_ANSWERED,
            A.THREAD_LAST_MESSAGE_DATE,
        ):
            self.assertIsNone(self._content(data)[alias]["node_value"])

    def test_a_reply_takes_the_threads_internal_flag(self):
        external = self._payload(thread=self.root, is_internal=True)
        self.service.prepare_create_payload(external, self.staff)
        self.assertIs(self._is_internal(external), False)

        internal = self._payload(thread=self.internal_root, is_internal=False)
        self.service.prepare_create_payload(internal, self.staff)
        self.assertIs(self._is_internal(internal), True)

    def test_a_reply_to_a_reply_is_threaded_onto_the_root(self):
        data = self._payload(thread=self.reply)
        self.service.prepare_create_payload(data, self.applicant)
        self.assertEqual(self._thread(data), str(self.root.pk))

    def test_a_reply_to_a_thread_the_poster_cannot_see_is_refused(self):
        with self.assertRaises(PermissionDenied):
            self.service.prepare_create_payload(
                self._payload(thread=self.internal_root), self.applicant
            )

    def test_reply_by_a_second_staffer_goes_to_the_applicant(self):
        # The staffer is on the staff side of the thread whoever started it, so
        # the client's recipient pick is replaced by the applicant.
        data = self._payload(recipient=self.unlinked.pk, thread=self.root)
        self.service.prepare_create_payload(data, self.third)
        self.assertEqual(self._author_id(data), str(self.third_contrib.pk))
        self.assertEqual(self._recipient_id(data), str(self.applicant_contrib.pk))

        data = self._payload(thread=self.staff_root)
        self.service.prepare_create_payload(data, self.third)
        self.assertEqual(self._recipient_id(data), str(self.applicant_contrib.pk))

    def test_reply_by_the_thread_starter_goes_to_the_other_party(self):
        data = self._payload(recipient=self.unlinked.pk, thread=self.root)
        self.service.prepare_create_payload(data, self.applicant)
        self.assertEqual(self._recipient_id(data), str(self.staff_contrib.pk))

    def test_reply_by_the_applicant_to_a_staff_thread_goes_to_staff(self):
        data = self._payload(thread=self.staff_root)
        self.service.prepare_create_payload(data, self.applicant)
        self.assertEqual(self._recipient_id(data), str(self.staff_contrib.pk))

    def test_reply_takes_the_threads_subject_and_type(self):
        data = self._payload(
            thread=self.root, subject="Something else", message_type=self.OTHER_TYPE
        )
        self.service.prepare_create_payload(data, self.applicant)
        self.assertEqual(self._subject(data), "Root")
        self.assertNotEqual(self._message_type(data), self.OTHER_TYPE)
        self.assertTrue(self._message_type(data))

    def test_new_thread_keeps_what_the_client_sent(self):
        data = self._payload(
            recipient=self.staff_contrib.pk,
            subject="Brand new",
            message_type=self.OTHER_TYPE,
        )
        self.service.prepare_create_payload(data, self.applicant)
        self.assertEqual(self._recipient_id(data), str(self.staff_contrib.pk))
        self.assertEqual(self._subject(data), "Brand new")
        self.assertEqual(self._message_type(data), self.OTHER_TYPE)

    def test_prepare_refuses_a_resource_the_poster_cannot_edit(self):
        with self.assertRaises(PermissionDenied):
            self.service.prepare_create_payload(self._payload(), self.stranger)


class BcapMessageAddressableTests(TestCase):
    """Who a message may be addressed to: the Archaeology Branch when nobody is
    assigned, and for staff whoever filed the permit too."""

    @classmethod
    def setUpTestData(cls):
        ControlledListFixtures.seed()
        cls.service = MessageService()
        builder = FixtureBuilder()

        cls.acme = make_contributor(builder, "Acme Corp")
        cls.applicant, cls.applicant_contrib = make_party(
            builder, "addrapp", "Amy", "Applicant", associated_organization=cls.acme
        )
        cls.staff, cls.staff_contrib = make_party(
            builder, "addrstaff", "Sam", "Staff", internal=True
        )
        cls.permit = build_permit(builder, "Addressed", organization=cls.acme)
        cls.requirement = make_requirement(builder, "Addressed req")
        cls.permit_with_req = build_permit(
            builder,
            "Addressed with req",
            [RequirementRow(cls.requirement)],
            organization=cls.acme,
        )
        ResourceInstance.objects.filter(
            pk__in=[cls.permit.pk, cls.permit_with_req.pk]
        ).update(principaluser=cls.applicant)
        cls.branch = ContributorService().archaeology_branch_id()

    def _ids(self, user, resource=None):
        resource = resource or self.permit
        return {c.id for c in self.service.recipient_options(str(resource.pk), user)}

    def test_staff_can_write_to_the_filer_and_the_branch(self):
        self.assertLessEqual(
            {str(self.applicant_contrib.pk), self.branch}, self._ids(self.staff)
        )

    def test_a_requirement_offers_its_permits_filer(self):
        self.assertIn(
            str(self.applicant_contrib.pk), self._ids(self.staff, self.requirement)
        )

    def test_applicants_get_the_branch_but_not_the_filer(self):
        ids = self._ids(self.applicant)
        self.assertIn(self.branch, ids)
        self.assertNotIn(str(self.applicant_contrib.pk), ids)

    def test_a_permit_with_no_filer_adds_nobody(self):
        ResourceInstance.objects.filter(pk=self.permit.pk).update(principaluser=None)
        self.assertEqual(self._ids(self.staff), {self.branch})

    def test_the_branch_and_staff_count_as_internal(self):
        contributors = ContributorService()
        self.assertTrue(contributors.contributor_is_internal(self.branch))
        self.assertTrue(
            contributors.contributor_is_internal(str(self.staff_contrib.pk))
        )
        self.assertFalse(contributors.contributor_is_internal(str(self.acme.pk)))
        self.assertFalse(
            contributors.contributor_is_internal(str(self.applicant_contrib.pk))
        )
