"""Unit tests for ProcessRequirementService -- the HTTP-agnostic mutations and
the response shape. Saves use force_admin so no request/session is needed."""

from datetime import date

from django.test import TestCase

from bcap.services.exceptions import StaleReference
from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)
from bcap.services.process_requirement.process_requirement_types import SubRequirement
from bcap.util.dashboard.resource_builder import ResourceBuilder
from bcap.util.sentinels import UNCHANGED

# PATCH-like save (diff-only), admin user, no ES indexing.
SAVE = {"force_admin": True, "partial": True, "index": False}


def make_requirement(builder, subs=()):
    """A process requirement due 2026-02-01 with the given sub-requirements,
    each a (name, satisfied, sort_order) tuple."""
    return builder.make_process_requirement(
        {
            "id": "REQ-1",
            "name": "Review",
            "due": "2026-02-01",
            "notes": "",
            "satisfied": False,
            "sub_requirements": [
                {
                    "name": name,
                    "description": "",
                    "sub_satisfied": satisfied,
                    "sort_order": sort_order,
                }
                for name, satisfied, sort_order in subs
            ],
        }
    )


class ProcessRequirementServiceTestCase(TestCase):
    def setUp(self):
        self.builder = ResourceBuilder()
        self.service = ProcessRequirementService()

    def reload(self, requirement):
        """Re-read the requirement from the DB as a tile tree."""
        return self.service.get_queryset().get(pk=requirement.pk)


class SetRequirementProcessDatesTests(ProcessRequirementServiceTestCase):
    def setUp(self):
        super().setUp()
        self.requirement = make_requirement(self.builder)

    def test_sets_provided_dates_and_leaves_others_unchanged(self):
        resource = self.reload(self.requirement)
        self.service.set_requirement_process_dates(
            resource,
            start_date=date(2026, 1, 1),
            due_date=UNCHANGED,
            completion_date=date(2026, 3, 1),
        )
        resource.save(**SAVE)

        out = self.service.to_output(self.reload(self.requirement))
        self.assertEqual(str(out.start_date), "2026-01-01")
        self.assertEqual(str(out.completion_date), "2026-03-01")
        self.assertEqual(str(out.due_date), "2026-02-01")  # untouched

    def test_none_clears_a_date(self):
        resource = self.reload(self.requirement)
        self.service.set_requirement_process_dates(
            resource, start_date=UNCHANGED, due_date=None, completion_date=UNCHANGED
        )
        resource.save(**SAVE)

        out = self.service.to_output(self.reload(self.requirement))
        self.assertIsNone(out.due_date)

    def test_nothing_provided_leaves_dates_unchanged(self):
        resource = self.reload(self.requirement)
        self.service.set_requirement_process_dates(
            resource,
            start_date=UNCHANGED,
            due_date=UNCHANGED,
            completion_date=UNCHANGED,
        )
        resource.save(**SAVE)

        out = self.service.to_output(self.reload(self.requirement))
        self.assertEqual(str(out.due_date), "2026-02-01")


class EditSubRequirementsTests(ProcessRequirementServiceTestCase):
    def setUp(self):
        super().setUp()
        self.requirement = make_requirement(
            self.builder, subs=[("Sub-1", False, 1), ("Sub-2", False, 2)]
        )
        ordered = sorted(
            self.service.to_output(self.reload(self.requirement)).sub_requirements,
            key=lambda s: s.sort_order,
        )
        self.sub1, self.sub2 = (s.id for s in ordered)

    def output_by_id(self):
        out = self.service.to_output(self.reload(self.requirement))
        return {s.id: s for s in out.sub_requirements}

    def test_edits_matched_sub_and_leaves_others(self):
        resource = self.reload(self.requirement)
        self.service.edit_sub_requirements(
            resource,
            [SubRequirement(id=self.sub1, satisfied=True, assessment_notes="done")],
        )
        resource.save(**SAVE)

        subs = self.output_by_id()
        self.assertTrue(subs[self.sub1].satisfied)
        self.assertEqual(subs[self.sub1].assessment_notes, "done")
        self.assertFalse(subs[self.sub2].satisfied)  # untouched

    def test_omitted_sort_order_leaves_existing_unchanged(self):
        resource = self.reload(self.requirement)
        # Reversed in the payload but no explicit sort_order -> orders untouched.
        self.service.edit_sub_requirements(
            resource, [SubRequirement(id=self.sub2), SubRequirement(id=self.sub1)]
        )
        resource.save(**SAVE)

        subs = self.output_by_id()
        self.assertEqual(subs[self.sub1].sort_order, 1)
        self.assertEqual(subs[self.sub2].sort_order, 2)

    def test_add_without_sort_order_raises(self):
        resource = self.reload(self.requirement)
        with self.assertRaises(ValueError):
            self.service.edit_sub_requirements(resource, [SubRequirement(name="Sub-3")])

    def test_explicit_sort_order_is_honored(self):
        resource = self.reload(self.requirement)
        self.service.edit_sub_requirements(
            resource,
            [
                SubRequirement(id=self.sub1, sort_order=10),
                SubRequirement(id=self.sub2, sort_order=5),
            ],
        )
        resource.save(**SAVE)

        subs = self.output_by_id()
        self.assertEqual(subs[self.sub1].sort_order, 10)
        self.assertEqual(subs[self.sub2].sort_order, 5)
        # to_output sorts by sort_order, so sub2 (5) precedes sub1 (10).
        out = self.service.to_output(self.reload(self.requirement))
        self.assertEqual([s.id for s in out.sub_requirements], [self.sub2, self.sub1])

    def test_add_without_name_raises(self):
        resource = self.reload(self.requirement)
        with self.assertRaises(ValueError):
            self.service.edit_sub_requirements(
                resource, [SubRequirement(satisfied=True)]
            )

    def test_unknown_sub_id_raises(self):
        resource = self.reload(self.requirement)
        with self.assertRaises(StaleReference):
            self.service.edit_sub_requirements(
                resource,
                [SubRequirement(id="00000000-0000-0000-0000-000000000000")],
            )

    def test_sub_without_id_is_added(self):
        resource = self.reload(self.requirement)
        self.service.edit_sub_requirements(
            resource,
            [
                SubRequirement(
                    name="Sub-3", satisfied=True, assessment_notes="new", sort_order=3
                )
            ],
        )
        resource.save(**SAVE)

        out = self.service.to_output(self.reload(self.requirement))
        self.assertEqual(len(out.sub_requirements), 3)  # the original two plus one
        added = out.sub_requirements[-1]
        self.assertNotIn(added.id, (self.sub1, self.sub2))
        self.assertEqual(added.name, "Sub-3")
        self.assertTrue(added.satisfied)
        self.assertEqual(added.assessment_notes, "new")
        self.assertEqual(added.sort_order, 3)


class ToOutputTests(ProcessRequirementServiceTestCase):
    def test_returns_id_dates_and_sub_requirements(self):
        requirement = make_requirement(self.builder, subs=[("Sub-1", True, 1)])
        out = self.service.to_output(self.reload(requirement))

        self.assertEqual(out.id, str(requirement.pk))
        self.assertEqual(str(out.due_date), "2026-02-01")
        self.assertEqual(len(out.sub_requirements), 1)
        self.assertTrue(out.sub_requirements[0].satisfied)
        self.assertEqual(out.sub_requirements[0].sort_order, 1)
