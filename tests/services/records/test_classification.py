import uuid
from unittest import mock

from django.test import SimpleTestCase, TestCase

from arches.app.models.models import TileModel

from bcap.services.records.classification import ClassificationService, Sensitivity
from bcap.util import graph


def site_upload(
    graph_slug="archaeological_site", node_alias="related_site_documents", **overrides
):
    args = {"doc_type": "", "extension": ".pdf", "resource_id": "rid"}
    upload = ClassificationService.UPLOAD_NODES.get(graph_slug, {}).get(node_alias)
    return ClassificationService.classify(upload=upload, **{**args, **overrides})


def reference_value(*labels):
    """A controlled list node value with (language, label) pref labels."""
    item_id = str(uuid.uuid4())
    return [
        {
            "uri": f"https://example.org/{item_id}",
            "list_id": str(uuid.uuid4()),
            "labels": [
                {
                    "id": str(uuid.uuid4()),
                    "value": value,
                    "language_id": language,
                    "valuetype_id": "prefLabel",
                    "list_item_id": item_id,
                }
                for language, value in labels
            ],
        }
    ]


def with_document_types(**types):
    return mock.patch.object(ClassificationService, "DOCUMENT_TYPES", types)


class ClassificationTests(SimpleTestCase):
    def test_map_type_is_restricted_site_location(self):
        tags = site_upload(doc_type="Map, Detailed")
        self.assertEqual(tags.sensitivity_class, "site-location")
        self.assertEqual(tags.classification_status, "auto")

    def test_unlisted_type_fails_closed_for_review(self):
        tags = site_upload(doc_type="Some New Type")
        self.assertEqual(tags.sensitivity_class, "site-location")
        self.assertEqual(tags.classification_status, "needs-review")

    def test_a_general_rule_sends_to_general(self):
        with with_document_types(permit=Sensitivity.GENERAL):
            tags = site_upload(doc_type="Permit")
        self.assertEqual(tags.sensitivity_class, "general")
        self.assertEqual(tags.classification_status, "auto")

    def test_spatial_file_is_restricted_whatever_its_type(self):
        with with_document_types(permit=Sensitivity.GENERAL):
            tags = site_upload(doc_type="Permit", extension=".KMZ")
        self.assertEqual(tags.sensitivity_class, "site-location")

    def test_unknown_upload_node_is_unclassified_and_restricted(self):
        tags = site_upload(graph_slug="project_engagement", node_alias="documents")
        self.assertEqual(tags.sensitivity_class, "site-location")
        self.assertEqual(tags.classification_status, "unclassified")
        self.assertEqual(tags.orcs_classification, "")

    def test_contravention_upload_is_a_violation_case_file(self):
        tags = site_upload(node_alias="contravention_document")
        self.assertEqual(tags.orcs_classification, "11100-30")
        self.assertEqual(tags.retention_trigger, "appeals-exhausted")

    def test_restricted_section_is_restricted(self):
        tags = site_upload(node_alias="restricted_document")
        self.assertEqual(tags.sensitivity_class, "site-location")
        self.assertEqual(tags.classification_status, "auto")

    def test_tag_set_fits_s3_limit(self):
        tags = site_upload(doc_type="Map")
        self.assertLessEqual(len(tags.as_s3()), 10)


class UploadNodeLookupTests(TestCase):
    """Against the real graphs, so a renamed alias or moved node shows up here."""

    def lookup(self, graph_slug, upload_alias, type_alias, label):
        tile = TileModel(
            nodegroup_id=graph.nodegroup_id(graph_slug, upload_alias),
            data={
                graph.node_id(graph_slug, type_alias): reference_value(("en", label))
            },
        )
        return ClassificationService.node_and_document_type(tile, graph_slug)

    def test_every_upload_node_is_found_in_its_own_tile(self):
        for graph_slug, uploads in ClassificationService.UPLOAD_NODES.items():
            for alias in uploads:
                with self.subTest(graph=graph_slug, node=alias):
                    tile = TileModel(
                        nodegroup_id=graph.nodegroup_id(graph_slug, alias), data={}
                    )
                    found, _ = ClassificationService.node_and_document_type(
                        tile, graph_slug
                    )
                    self.assertEqual(found, alias)

    def test_site_image_type_is_read(self):
        self.assertEqual(
            self.lookup(
                "archaeological_site", "site_images", "image_type", "Photograph"
            ),
            ("site_images", "Photograph"),
        )

    def test_site_visit_document_type_is_read(self):
        self.assertEqual(
            self.lookup(
                "site_visit", "related_site_documents", "related_document_type", "Map"
            ),
            ("related_site_documents", "Map"),
        )
