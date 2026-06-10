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
    AliasedNodeDataSerializer,
    AliasedNodeDataExtension,
    _sort_properties_in_place,
    strip_enum_length_constraints,
    type_base_serializer_fields,
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
        self.assertTrue(
            any(p.endswith("/api/dashboard/internal") for p in paths), paths
        )
        self.assertTrue(
            any(p.endswith("/api/dashboard/external") for p in paths), paths
        )
        self.assertTrue(any(p.endswith("/user_profile") for p in paths), paths)

    def test_dashboard_response_schema_matches_the_page_dataclass(self):
        schema = yaml.safe_load(self.client.get(reverse("schema")).content)

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

    def test_resource_draft_data_documented_as_a_freeform_object(self):
        schema = yaml.safe_load(self.client.get(reverse("schema")).content)

        draft = next(
            body
            for path, body in schema["paths"].items()
            if path.endswith("/resource_draft/{graph_slug}/{id}")
        )
        ref = draft["get"]["responses"]["200"]["content"]["application/json"][
            "schema"
        ]["$ref"]
        component = schema["components"]["schemas"][ref.rsplit("/", 1)[-1]]
        # The draft `data` blob is unvalidated, graph-agnostic form state, so it's
        # documented as an arbitrary JSON object -- clients type it as a record
        # rather than `unknown` (see ResourceDraftSerializer.FreeformJSONField).
        data = component["properties"]["data"]
        self.assertEqual(data.get("type"), "object")
        self.assertEqual(data.get("additionalProperties"), True)


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

    def test_component_name_defaults_without_a_datatype(self):
        extension = AliasedNodeDataExtension(self.wrapped())
        self.assertEqual(extension.get_name(), "AliasedNodeData")

    def test_component_name_specialized_per_datatype(self):
        extension = AliasedNodeDataExtension(self.wrapped(datatype="concept-list"))
        self.assertEqual(extension.get_name(), "ConceptListAliasedNodeData")

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

    def test_localized_string_node_value_modeled_as_i18n_object(self):
        # node_value is the {lang: {value, direction}} object the API emits, so a
        # value-length limit has a real string to bind to.
        schema, _ = self.map_field(
            self.wrapped(serializers.CharField, datatype="string")
        )
        value = schema["properties"]["node_value"]["properties"]["en"]
        self.assertEqual(value["properties"]["value"]["type"], "string")
        self.assertNotIn("maxLength", value["properties"]["value"])

    def test_localized_string_max_length_binds_to_inner_value(self):
        schema, _ = self.map_field(
            self.wrapped(serializers.CharField, datatype="string", max_length=125)
        )
        node_value = schema["properties"]["node_value"]
        self.assertEqual(
            node_value["properties"]["en"]["properties"]["value"]["maxLength"], 125
        )

    def test_non_localized_string_max_length_binds_to_scalar(self):
        schema, _ = self.map_field(
            self.wrapped(
                serializers.CharField, datatype="non-localized-string", max_length=50
            )
        )
        node_value = schema["properties"]["node_value"]
        self.assertEqual(node_value["type"], "string")
        self.assertEqual(node_value["maxLength"], 50)

    def test_concept_list_max_length_becomes_max_items(self):
        schema, _ = self.map_field(
            self.wrapped(serializers.JSONField, datatype="concept-list", max_length=3)
        )
        node_value = schema["properties"]["node_value"]
        self.assertEqual(node_value["type"], "array")
        self.assertEqual(node_value["maxItems"], 3)

    def test_number_min_max_bind_to_the_value(self):
        schema, _ = self.map_field(
            self.wrapped(
                serializers.FloatField,
                datatype="number",
                config={"min": "0", "max": "10"},
            )
        )
        node_value = schema["properties"]["node_value"]
        self.assertEqual(node_value["minimum"], 0)
        self.assertEqual(node_value["maximum"], 10)

    def test_number_bounds_get_their_own_component_name(self):
        extension = AliasedNodeDataExtension(
            self.wrapped(
                serializers.FloatField,
                datatype="number",
                config={"min": "0", "max": "10"},
            )
        )
        self.assertEqual(extension.get_name(), "NumberAliasedNodeDataMin0Max10")

    def test_required_list_node_requires_at_least_one_item(self):
        schema, _ = self.map_field(
            self.wrapped(serializers.JSONField, datatype="reference", required=True)
        )
        self.assertEqual(schema["properties"]["node_value"]["minItems"], 1)

    def test_optional_list_node_has_no_min_items(self):
        schema, _ = self.map_field(
            self.wrapped(serializers.JSONField, datatype="reference", required=False)
        )
        self.assertNotIn("minItems", schema["properties"]["node_value"])

    def test_required_list_node_gets_its_own_component_name(self):
        extension = AliasedNodeDataExtension(
            self.wrapped(serializers.JSONField, datatype="reference", required=True)
        )
        self.assertEqual(extension.get_name(), "ReferenceAliasedNodeDataRequired")

    def test_constrained_node_gets_its_own_component_name(self):
        # Distinct limits can't share a datatype's component; equal limits do.
        base = AliasedNodeDataExtension(self.wrapped(datatype="string"))
        constrained = AliasedNodeDataExtension(
            self.wrapped(datatype="string", max_length=125)
        )
        self.assertEqual(base.get_name(), "StringAliasedNodeData")
        self.assertEqual(constrained.get_name(), "StringAliasedNodeDataMax125")

    def test_node_value_shaped_for_every_resource_model_datatype(self):
        # One row per datatype used across the resource models: navigate from
        # node_value to a representative leaf and pin the schema the API emits.
        # Scalars (boolean/date/number) derive from the field's base type and are
        # covered above.
        uuid = {"type": "string", "format": "uuid"}
        cases = {
            "string": ("properties.en.properties.value", {"type": "string"}),
            "non-localized-string": ("", {"type": "string"}),
            "borden-number-datatype": ("", {"type": "string"}),
            "concept": ("", uuid),
            "concept-list": ("items", uuid),
            "reference": ("items.properties.labels", {"type": "array"}),
            "resource-instance": ("properties.resourceId", uuid),
            "resource-instance-list": ("items.properties.resourceId", uuid),
            "file-list": ("items.properties.node_id", uuid),
            "url": ("properties.url_label", {"type": "string"}),
            "geojson-feature-collection": ("properties.features", {"type": "array"}),
        }
        for datatype, (path, expected) in cases.items():
            with self.subTest(datatype=datatype):
                schema, _ = self.map_field(self.wrapped(datatype=datatype))
                leaf = schema["properties"]["node_value"]
                for key in filter(None, path.split(".")):
                    leaf = leaf[key]
                for key, value in expected.items():
                    self.assertEqual(leaf.get(key), value, leaf)


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


class EnumLengthConstraintHookTests(SimpleTestCase):
    """The hook drops redundant minLength/maxLength from enum schemas (DRF stamps
    `minLength: 1` on required CharField choices), which trips clients into
    invalid code, while leaving length on genuine (non-enum) strings intact."""

    def test_length_stripped_from_enum_but_kept_on_plain_string(self):
        result = {
            "choice": {"type": "string", "enum": ["A", "B"], "minLength": 1},
            "free": {"type": "string", "minLength": 1},
        }
        out = strip_enum_length_constraints(result, None, None, None)
        self.assertEqual(out["choice"], {"type": "string", "enum": ["A", "B"]})
        self.assertEqual(out["free"], {"type": "string", "minLength": 1})
