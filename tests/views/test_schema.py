"""The drf-spectacular OpenAPI endpoints: the schema document plus the Swagger
UI and ReDoc viewers. SPECTACULAR_SETTINGS pins SERVE_URLCONF to
bcap.urls_api_documented, so the served schema documents only the bcap API
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
    AliasedNodeDataSerializer,
    AliasedNodeDataExtension,
    _sort_properties_in_place,
    type_base_serializer_fields,
)
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
        self.assertTrue(any(p.endswith("/user_profile") for p in paths), paths)

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


class NodeValueFieldExtensionTests(SimpleTestCase):
    """The extension types the {node_value, display_value, details} envelope per
    Arches datatype. Driven directly to stay off the full-document path, which
    needs a seeded graph and an authenticated user."""

    def map_field(self, field):
        auto = AutoSchema()
        auto.registry = ComponentRegistry()
        # resolve_serializer reads self.view.request; a request-less view suffices.
        with patch.object(AutoSchema, "view", MagicMock(request=None)):
            schema = AliasedNodeDataExtension(field).map_serializer_field(
                auto, "response"
            )
        return schema, auto.registry

    def wrapped(
        self,
        drf_field=serializers.CharField,
        datatype=None,
        max_length=None,
        config=None,
        required=False,
    ):
        # _wrap_serializer_field builds every node value field; style.datatype is
        # what arches_querysets stamps on, and what the extension reads.
        # widget_config carries editor-set limits (maxLength, min/max; '' when unset);
        # field.required mirrors Node.isrequired.
        field = _wrap_serializer_field(drf_field)()
        field.required = required
        if datatype is not None:
            field.style = {"datatype": datatype}
            widget_config = dict(config or {})
            if max_length is not None:
                widget_config["maxLength"] = max_length
            if widget_config:
                field.style["widget_config"] = widget_config
        return field

    def test_wrapped_node_value_fields_match_the_extension(self):
        self.assertIsInstance(self.wrapped(), AliasedNodeDataExtension.target_class)

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

    def test_component_names(self):
        # Distinct limits can't share a datatype's component; equal limits do.
        for expected, kwargs in (
            ("AliasedNodeData", {}),
            ("ConceptListAliasedNodeData", {"datatype": "concept-list"}),
            ("StringAliasedNodeData", {"datatype": "string"}),
            ("StringAliasedNodeDataMax125", {"datatype": "string", "max_length": 125}),
            (
                "NumberAliasedNodeDataMin0Max10",
                {
                    "drf_field": serializers.FloatField,
                    "datatype": "number",
                    "config": {"min": "0", "max": "10"},
                },
            ),
            (
                "ReferenceAliasedNodeDataRequired",
                {
                    "drf_field": serializers.JSONField,
                    "datatype": "reference",
                    "required": True,
                },
            ),
        ):
            with self.subTest(expected):
                extension = AliasedNodeDataExtension(self.wrapped(**kwargs))
                self.assertEqual(extension.get_name(), expected)

    def test_details_typed_per_datatype(self):
        generic = {"type": "object", "additionalProperties": {}}
        for datatype, drf_field, expected in (
            ("concept", serializers.UUIDField, "ConceptValueDetail"),
            ("resource-instance", serializers.JSONField, "ResourceInstanceDetail"),
            ("string", serializers.CharField, generic),
        ):
            with self.subTest(datatype):
                schema, _ = self.map_field(self.wrapped(drf_field, datatype=datatype))
                items = schema["properties"]["details"]["items"]
                if isinstance(expected, str):
                    self.assertTrue(items["$ref"].endswith(f"/{expected}"), items)
                else:
                    self.assertEqual(items, expected)

    def assert_node_value(self, path, expected, **kwargs):
        """Navigate node_value down path and pin the keys expected names; a None
        expects the key to be absent."""
        schema, _ = self.map_field(self.wrapped(**kwargs))
        leaf = schema["properties"]["node_value"]
        for key in filter(None, path.split(".")):
            leaf = leaf[key]
        for key, value in expected.items():
            self.assertEqual(leaf.get(key), value, leaf)

    def test_node_value_constraints(self):
        # A localized node_value is the {lang: {value, direction}} object the API
        # emits, so a value-length limit has a real string to bind to.
        inner = "properties.en.properties.value"
        json_list = {"drf_field": serializers.JSONField, "datatype": "reference"}
        for name, path, expected, kwargs in (
            (
                "localized string is an i18n object",
                inner,
                {"type": "string", "maxLength": None},
                {"datatype": "string"},
            ),
            (
                "localized max binds to the inner value",
                inner,
                {"maxLength": 125},
                {"datatype": "string", "max_length": 125},
            ),
            (
                "non-localized max binds to the scalar",
                "",
                {"type": "string", "maxLength": 50},
                {"datatype": "non-localized-string", "max_length": 50},
            ),
            (
                "a list max becomes maxItems",
                "",
                {"type": "array", "maxItems": 3},
                {
                    "drf_field": serializers.JSONField,
                    "datatype": "concept-list",
                    "max_length": 3,
                },
            ),
            (
                "number bounds bind to the value",
                "",
                {"minimum": 0, "maximum": 10},
                {
                    "drf_field": serializers.FloatField,
                    "datatype": "number",
                    "config": {"min": "0", "max": "10"},
                },
            ),
            (
                "a required list wants at least one item",
                "",
                {"minItems": 1},
                {**json_list, "required": True},
            ),
            ("an optional list does not", "", {"minItems": None}, json_list),
        ):
            with self.subTest(name):
                self.assert_node_value(path, expected, **kwargs)

    def test_node_value_shaped_for_every_resource_model_datatype(self):
        # One row per datatype used across the resource models: navigate from
        # node_value to a representative leaf and pin the schema the API emits.
        # Scalars (boolean/number) derive from the field's base type and are
        # covered above; date is a pattern accepting a bare date or a space/T
        # datetime, so the generated Zod is a regex, not strict z.iso.datetime.
        uuid = {"type": "string", "format": "uuid"}
        cases = {
            "string": ("properties.en.properties.value", {"type": "string"}),
            "date": (
                "",
                {
                    "type": "string",
                    "pattern": (
                        r"^\d{4}-\d{2}-\d{2}"
                        r"([ T]\d{2}:\d{2}:\d{2}([+-]\d{2}:\d{2}|Z)?)?$"
                    ),
                },
            ),
            "non-localized-string": ("", {"type": "string"}),
            "borden-number-datatype": ("", {"type": "string"}),
            "concept": ("", uuid),
            "concept-list": ("items", uuid),
            "reference": ("items.properties.labels", {"type": "array"}),
            "resource-instance": ("items.properties.resourceId", uuid),
            "resource-instance-list": ("items.properties.resourceId", uuid),
            "file-list": ("items.properties.node_id", uuid),
            "url": ("properties.url_label", {"type": "string"}),
            "geojson-feature-collection": ("properties.features", {"type": "array"}),
        }
        for datatype, (path, expected) in cases.items():
            with self.subTest(datatype=datatype):
                self.assert_node_value(path, expected, datatype=datatype)


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


class BaseSerializerFieldTypingTests(SimpleTestCase):
    """The hook types the arches base-serializer fields the node-value extension
    can't reach (resource name/descriptors, tile provisionaledits), and only when
    they're untyped, so a node aliased "name" is left alone."""

    def run_hook(self, schemas):
        result = {"components": {"schemas": schemas}}
        return type_base_serializer_fields(result, None, None, None)["components"][
            "schemas"
        ]

    def test_provisionaledits_typed_as_a_per_user_edit_map(self):
        out = self.run_hook(
            {"X_Tile": {"properties": {"provisionaledits": {"nullable": True}}}}
        )
        edit = out["X_Tile"]["properties"]["provisionaledits"]
        self.assertEqual(edit["type"], "object")
        self.assertEqual(
            set(edit["additionalProperties"]["properties"]),
            {"value", "status", "action", "reviewer", "timestamp", "reviewtimestamp"},
        )

    def test_resource_name_and_descriptors_typed(self):
        out = self.run_hook(
            {
                "Resource": {
                    "properties": {
                        "name": {"readOnly": True, "nullable": True},
                        "descriptors": {"readOnly": True, "nullable": True},
                    }
                }
            }
        )
        properties = out["Resource"]["properties"]
        self.assertEqual(properties["name"]["type"], "string")
        descriptor = properties["descriptors"]["properties"]["en"]["properties"]
        self.assertEqual(set(descriptor), {"name", "description", "map_popup"})

    def test_typed_node_field_named_name_is_left_untouched(self):
        # A node aliased "name" is an allOf/$ref, not the untyped base field.
        node_name = {"allOf": [{"$ref": "#/components/schemas/StringAliasedNodeData"}]}
        out = self.run_hook({"Tile": {"properties": {"name": node_name}}})
        self.assertEqual(out["Tile"]["properties"]["name"], node_name)
