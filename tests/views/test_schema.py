"""The drf-spectacular OpenAPI endpoints: the schema document plus the Swagger
UI and ReDoc viewers. SPECTACULAR_SETTINGS pins SERVE_URLCONF to
bcap.documented_api_urls, so the served schema documents only the bcap API
(the dashboard and user-profile endpoints), not all of Arches.

The endpoints sit behind IsAdminUser so these log in as the admin user."""

from unittest.mock import MagicMock, patch

import yaml

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.plumbing import ComponentRegistry
from rest_framework import serializers

from arches.app.models.models import Node
from arches_querysets.models import ResourceTileTree
from arches_querysets.rest_framework.serializers import _wrap_serializer_field

from bcap.schema import (
    NodeValueEnvelopeSerializer,
    NodeValueFieldExtension,
    _sort_properties_in_place,
)
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.dashboard.resource_builder import ResourceBuilder
from tests.views.helpers import AuthTestHelper
from tests.views.test_process_requirement_api import make_requirement


@override_settings(ROOT_URLCONF="tests.test_urls")
class SchemaEndpointTests(AuthTestHelper, TestCase):
    """The generated schema document is the contract the frontend's TypeScript
    types are built from, so these guard that it generates and covers the bcap
    endpoints."""

    def setUp(self):
        super().setUp()
        admin = get_user_model().objects.get(username="admin")
        self.idir_login_simulate(admin)

    def test_schema_endpoint_returns_openapi_document(self):
        resp = self.client.get(reverse("schema"))

        self.assertEqual(resp.status_code, 200)
        schema = yaml.safe_load(resp.content)
        self.assertEqual(schema["openapi"].split(".")[0], "3")
        self.assertEqual(schema["info"]["title"], "BCAP API")

    def test_schema_documents_the_bcap_endpoints(self):
        schema = yaml.safe_load(self.client.get(reverse("schema")).content)

        paths = schema["paths"]
        # SERVE_URLCONF limits the schema to the documented bcap routes.
        self.assertTrue(any(p.endswith("/api/dashboard") for p in paths), paths)
        self.assertTrue(any(p.endswith("/user_profile") for p in paths), paths)

    def test_dashboard_response_schema_matches_the_page_dataclass(self):
        schema = yaml.safe_load(self.client.get(reverse("schema")).content)

        dashboard = next(
            body
            for path, body in schema["paths"].items()
            if path.endswith("/api/dashboard")
        )
        ref = dashboard["get"]["responses"]["200"]["content"]["application/json"][
            "schema"
        ]["$ref"]
        component = ref.rsplit("/", 1)[-1]
        page = schema["components"]["schemas"][component]
        # The DashboardPage dataclass fields the frontend pages on.
        self.assertEqual(
            set(page["properties"]) & {"count", "page", "limit", "results"},
            {"count", "page", "limit", "results"},
        )


@override_settings(ROOT_URLCONF="tests.test_urls")
class SchemaViewerTests(AuthTestHelper, TestCase):
    """The Swagger UI and ReDoc viewer pages render."""

    def setUp(self):
        super().setUp()
        admin = get_user_model().objects.get(username="admin")
        self.idir_login_simulate(admin)

    def test_swagger_ui_renders(self):
        resp = self.client.get(reverse("swagger-ui"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", resp["Content-Type"])

    def test_redoc_renders(self):
        resp = self.client.get(reverse("redoc"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", resp["Content-Type"])


class NodeValueFieldExtensionTests(SimpleTestCase):
    """The extension types the {node_value, display_value, details} envelope per
    Arches datatype. Driven directly to stay off the full-document path, which
    needs a seeded graph and an authenticated user."""

    def map_field(self, field):
        auto = AutoSchema()
        auto.registry = ComponentRegistry()
        # resolve_serializer reads self.view.request; a request-less view suffices.
        with patch.object(AutoSchema, "view", MagicMock(request=None)):
            schema = NodeValueFieldExtension(field).map_serializer_field(
                auto, "response"
            )
        return schema, auto.registry

    def wrapped(self, drf_field=serializers.CharField, datatype=None):
        # _wrap_serializer_field builds every node value field; style.datatype is
        # what arches_querysets stamps on, and what the extension reads.
        field = _wrap_serializer_field(drf_field)()
        if datatype is not None:
            field.style = {"datatype": datatype}
        return field

    def test_wrapped_node_value_fields_match_the_extension(self):
        self.assertIsInstance(self.wrapped(), NodeValueFieldExtension.target_class)

    def test_envelope_exposes_node_value_display_value_and_details(self):
        schema, _ = self.map_field(self.wrapped(serializers.IntegerField))
        self.assertEqual(
            set(schema["properties"]), {"node_value", "display_value", "details"}
        )

    def test_display_value_and_details_are_read_only(self):
        schema, _ = self.map_field(self.wrapped())
        properties = schema["properties"]
        self.assertTrue(properties["display_value"]["readOnly"])
        self.assertTrue(properties["details"]["readOnly"])

    def test_node_value_typed_from_the_underlying_field(self):
        # An integer-backed node documents node_value as an integer, not opaque JSON.
        schema, _ = self.map_field(self.wrapped(serializers.IntegerField))
        self.assertEqual(schema["properties"]["node_value"]["type"], "integer")

    def test_component_name_defaults_without_a_datatype(self):
        extension = NodeValueFieldExtension(self.wrapped())
        self.assertEqual(extension.get_name(), "NodeValueEnvelope")

    def test_component_name_specialized_per_datatype(self):
        extension = NodeValueFieldExtension(self.wrapped(datatype="concept-list"))
        self.assertEqual(extension.get_name(), "ConceptListNodeValueEnvelope")

    def test_concept_details_typed_as_value_objects(self):
        schema, _ = self.map_field(
            self.wrapped(serializers.UUIDField, datatype="concept")
        )
        ref = schema["properties"]["details"]["items"]["$ref"]
        self.assertTrue(ref.endswith("/ConceptValueDetail"), ref)

    def test_resource_instance_details_typed(self):
        schema, _ = self.map_field(
            self.wrapped(serializers.JSONField, datatype="resource-instance")
        )
        ref = schema["properties"]["details"]["items"]["$ref"]
        self.assertTrue(ref.endswith("/ResourceInstanceDetail"), ref)

    def test_scalar_details_stay_generic(self):
        schema, _ = self.map_field(
            self.wrapped(serializers.CharField, datatype="string")
        )
        items = schema["properties"]["details"]["items"]
        self.assertEqual(items, {"type": "object", "additionalProperties": {}})


class NodeValueEnvelopeContractTests(TestCase):
    """NodeValueEnvelopeSerializer is a hand-kept mirror of the dict
    TileTree.get_value_with_context emits, so pin it: CI fails if the upstream
    Arches shape drifts. Reads always fetch as_representation=True, so this
    envelope is what the API actually returns."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        requirement = make_requirement(ResourceBuilder())
        cls.resource = ResourceTileTree.get_tiles(
            GraphSlugs.PROCESS_REQUIREMENT,
            resource_ids=[requirement.pk],
        ).get()

    def test_envelope_keys_match_get_value_with_context(self):
        # A seeded tile has correctly-shaped (localized) node data.
        tile = self.resource.aliased_data.requirement_identification
        node = Node.objects.get(
            graph__slug=GraphSlugs.PROCESS_REQUIREMENT,
            alias="requirement_name",
            source_identifier=None,
        )
        pair = tile.get_value_with_context(node, node_value=tile.data[str(node.pk)])

        self.assertEqual(set(pair), set(NodeValueEnvelopeSerializer().fields))


class SchemaPropertySortingTests(SimpleTestCase):
    """Arches node-derived properties order by (Node.sortorder, alias); maps with
    any non-alias key (hand-written serializers) keep their declared order."""

    ORDER = {"a_node": 1, "b_node": 0, "c_node": 0}  # b, c tie at 0

    def test_node_derived_map_sorted_by_sortorder_then_alias(self):
        schema = {"properties": {"a_node": {}, "c_node": {}, "b_node": {}}}
        _sort_properties_in_place(schema, self.ORDER)
        self.assertEqual(list(schema["properties"]), ["b_node", "c_node", "a_node"])

    def test_map_with_a_non_alias_key_keeps_declared_order(self):
        schema = {"properties": {"id": {}, "c_node": {}, "b_node": {}}}
        _sort_properties_in_place(schema, self.ORDER)
        self.assertEqual(list(schema["properties"]), ["id", "c_node", "b_node"])
