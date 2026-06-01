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

from bcap.schema import NodeValueEnvelopeSerializer, NodeValueFieldExtension
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
    """The extension maps node value fields to the NodeValueEnvelope component.

    Driven directly to stay off the full-document path, which needs a seeded
    graph and an authenticated user."""

    def map_field(self, field):
        auto = AutoSchema()
        auto.registry = ComponentRegistry()
        # resolve_serializer reads self.view.request; a request-less view suffices.
        with patch.object(AutoSchema, "view", MagicMock(request=None)):
            schema = NodeValueFieldExtension(field).map_serializer_field(
                auto, "response"
            )
        return schema, auto.registry

    def component(self, registry, name="NodeValueEnvelope"):
        return next(c for c in registry._components.values() if c.name == name).schema

    def test_wrapped_node_value_fields_match_the_extension(self):
        # _wrap_serializer_field builds every node value field.
        wrapped = _wrap_serializer_field(serializers.CharField)()
        self.assertIsInstance(wrapped, NodeValueFieldExtension.target_class)

    def test_field_references_the_shared_envelope_component(self):
        schema, _ = self.map_field(_wrap_serializer_field(serializers.CharField)())
        self.assertEqual(schema, {"$ref": "#/components/schemas/NodeValueEnvelope"})

    def test_envelope_exposes_node_value_display_value_and_details(self):
        _, registry = self.map_field(_wrap_serializer_field(serializers.IntegerField)())
        self.assertEqual(
            set(self.component(registry)["properties"]),
            {"node_value", "display_value", "details"},
        )

    def test_display_value_and_details_are_read_only(self):
        _, registry = self.map_field(_wrap_serializer_field(serializers.CharField)())
        properties = self.component(registry)["properties"]
        self.assertTrue(properties["display_value"]["readOnly"])
        self.assertTrue(properties["details"]["readOnly"])


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
