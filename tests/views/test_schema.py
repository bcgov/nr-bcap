"""The drf-spectacular OpenAPI endpoints: the schema document plus the Swagger
UI and ReDoc viewers. SPECTACULAR_SETTINGS pins SERVE_URLCONF to
bcap.documented_api_urls, so the served schema documents only the bcap API
(the dashboard and user-profile endpoints), not all of Arches.

The endpoints sit behind IsAdminUser so these log in as the admin user."""

import yaml

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from tests.views.helpers import AuthTestHelper


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
