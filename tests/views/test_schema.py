"""The drf-spectacular OpenAPI endpoints: the schema document plus the Swagger
UI and ReDoc viewers. SPECTACULAR_SETTINGS pins SERVE_URLCONF to
bcap.urls_api_documented, so the served schema documents only the bcap API
(the dashboard and user-profile endpoints), not all of Arches.

The endpoints sit behind IsAdminUser so these log in as the admin user."""

import yaml

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from arches.app.models.models import Node
from arches_querysets.models import ResourceTileTree

from bcap.schema import AliasedNodeDataSerializer
from bcap.serializers.graph_serializers import (
    GRAPH_SERIALIZERS,
    aliased_data_union_schema,
)
from bcap.util.bcap_aliases import GraphSlugs
from bcap.builders.process_requirement_builder import ProcessRequirementBuilder
from tests.views.helpers import AuthTestHelper
from tests.views.test_process_requirement_api import make_requirement


@override_settings(ROOT_URLCONF="tests.test_urls")
class SchemaEndpointTests(AuthTestHelper, TestCase):
    """The generated schema document is the contract the frontend's TypeScript
    types are built from, so these guard that it generates and covers the bcap
    endpoints."""

    _document = None

    def setUp(self):
        super().setUp()
        admin = get_user_model().objects.get(username="admin")
        self.idir_login_simulate(admin)

    def schema(self):
        if SchemaEndpointTests._document is None:
            resp = self.client.get(reverse("schema"))
            self.assertEqual(resp.status_code, 200)
            SchemaEndpointTests._document = yaml.safe_load(resp.content)
        return SchemaEndpointTests._document

    def test_schema_endpoint_returns_openapi_document(self):
        schema = self.schema()

        self.assertEqual(schema["openapi"].split(".")[0], "3")
        self.assertEqual(schema["info"]["title"], "BCAP API")

    def test_schema_documents_the_bcap_endpoints(self):
        paths = self.schema()["paths"]
        # SERVE_URLCONF limits the schema to the documented bcap routes.
        self.assertTrue(
            any(p.endswith("/api/dashboard/internal") for p in paths), paths
        )
        self.assertTrue(
            any(p.endswith("/api/dashboard/external") for p in paths), paths
        )
        self.assertTrue(any(p.endswith("/api/user/") for p in paths), paths)

    def test_dashboard_response_schema_matches_the_page_dataclass(self):
        schema = self.schema()

        dashboard = next(
            body
            for path, body in schema["paths"].items()
            if path.endswith("/api/dashboard/internal")
        )
        ref = dashboard["get"]["responses"]["200"]["content"]["application/json"][
            "schema"
        ]["$ref"]
        component = ref.rsplit("/", 1)[-1]
        page = schema["components"]["schemas"][component]
        # The InternalDashboardPage dataclass fields the frontend pages on.
        self.assertEqual(
            set(page["properties"]) & {"count", "page", "limit", "results"},
            {"count", "page", "limit", "results"},
        )

    def test_aliased_data_union_refs_all_resolve(self):
        """The draft blob's union names its components by string, so a rename in
        the serializers would leave dangling refs that only surface as untyped
        `unknown` in the generated client."""
        schema = self.schema()
        components = schema["components"]["schemas"]

        refs = [option["$ref"] for option in aliased_data_union_schema()["oneOf"]]

        self.assertEqual(len(refs), len(GRAPH_SERIALIZERS))
        for ref in refs:
            self.assertIn(ref.rsplit("/", 1)[-1], components, ref)

    def test_aliased_data_union_reaches_the_draft_routes(self):
        """The union is only worth keeping in step if the routes still carry it."""
        schema = self.schema()

        draft = next(
            body
            for path, body in schema["paths"].items()
            if path.endswith("/api/workflow_draft")
        )
        record = schema["components"]["schemas"]["DraftRecord"]

        self.assertIn("oneOf", record["properties"]["data"])
        self.assertIn("get", draft)


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


class NodeValueEnvelopeContractTests(TestCase):
    """NodeValueEnvelopeSerializer is a hand-kept mirror of the dict
    TileTree.get_value_with_context emits, so pin it: CI fails if the upstream
    Arches shape drifts. Reads always fetch as_representation=True, so this
    envelope is what the API actually returns."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        requirement = make_requirement(ProcessRequirementBuilder())
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

        self.assertEqual(set(pair), set(AliasedNodeDataSerializer().fields))
