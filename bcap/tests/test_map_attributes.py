import uuid

from django.test import TestCase

from arches.app.models.models import (
    GraphModel,
    Node,
    ResourceInstance,
    ResourceInstanceLifecycleState,
    TileModel,
)
from bcap.util.map_attributes import GRAPH_CONFIG, inject_map_attributes
from bcap.util.mvt_tiler import MVTTiler

SLUG = "archaeological_site"
NODEID, ALIAS, FIELDS = GRAPH_CONFIG[SLUG]


def _response_with(features):
    # Mirrors the arches_querysets detail-response shape that MapLibre
    # consumes: each feature's `properties` drive layer styling, so the
    # injector targets exactly this nesting (nodegroup alias -> node alias
    # -> node_value -> features).
    return {
        "aliased_data": {
            ALIAS: {"aliased_data": {ALIAS: {"node_value": {"features": features}}}}
        }
    }


def _features_of(response):
    return response["aliased_data"][ALIAS]["aliased_data"][ALIAS]["node_value"][
        "features"
    ]


class TestInjectMapAttributes(TestCase):
    def test_unknown_slug_is_noop(self):
        response = _response_with([{"properties": {"id": 1}}])
        inject_map_attributes(response, str(uuid.uuid4()), "not_a_slug")
        self.assertEqual(_features_of(response)[0]["properties"], {"id": 1})

    def test_attrs_injected_for_real_resource(self):
        graph = GraphModel.objects.get(slug=SLUG)
        borden = Node.objects.get(graph=graph, alias="borden_number")
        resource = ResourceInstance.objects.create(
            graph=graph,
            resource_instance_lifecycle_state=(
                ResourceInstanceLifecycleState.objects.first()
            ),
        )
        TileModel.objects.create(
            resourceinstance=resource,
            nodegroup_id=borden.nodegroup_id,
            data={str(borden.nodeid): "EeRm-123"},
        )

        response = _response_with([{}, {"properties": {"id": 2}}])
        inject_map_attributes(response, str(resource.resourceinstanceid), SLUG)

        feats = _features_of(response)
        self.assertEqual(feats[0]["properties"]["borden_number"], "EeRm-123")
        self.assertEqual(feats[1]["properties"]["borden_number"], "EeRm-123")
        self.assertEqual(feats[1]["properties"]["id"], 2)


class TestMVTTilerQueryConfig(TestCase):
    def test_derives_from_graph_config(self):
        self.assertEqual(
            MVTTiler.get_query_config(),
            {nodeid: fields for nodeid, _, fields in GRAPH_CONFIG.values()},
        )
