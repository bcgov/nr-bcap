from __future__ import annotations

import os
import sys

from contextlib import suppress
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bcap.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

_DJANGO_AVAILABLE = False

with suppress(Exception):
    import django
    django.setup()
    _DJANGO_AVAILABLE = True

from models import (
    BOOLEAN_DATATYPES,
    DATE_DATATYPES,
    GEO_DATATYPES,
    NUMBER_DATATYPES,
    STRING_DATATYPES
)

if _DJANGO_AVAILABLE:
    from arches.app.models.models import (
        CardModel,
        CardXNodeXWidget,
        DDataType,
        GraphModel,
        Node,
        TileModel,
    )
    from arches.app.models.system_settings import settings


def get_inventory() -> list[dict[str, Any]]:
    if not _DJANGO_AVAILABLE:
        return []

    searchable_datatypes = {
        dt.pk for dt in DDataType.objects.filter(issearchable=True)
    }

    searchable_nodes = (
        Node.objects.filter(
            datatype__in=searchable_datatypes,
            graph__is_active=True,
            graph__isresource=True,
            issearchable=True,
        )
        .exclude(graph__pk=settings.SYSTEM_SETTINGS_RESOURCE_MODEL_ID)
        .exclude(graph__source_identifier__isnull=False)
        .select_related("graph", "nodegroup")
    )

    widgets = {
        str(w.node_id): w.label
        for w in CardXNodeXWidget.objects.filter(node__in=searchable_nodes)
    }

    nodes_by_nodegroup = {}

    for node in searchable_nodes:
        ng = str(node.nodegroup_id)

        if ng not in nodes_by_nodegroup:
            nodes_by_nodegroup[ng] = []

        label = str(widgets.get(str(node.nodeid), node.name))

        nodes_by_nodegroup[ng].append({
            "datatype": str(node.datatype),
            "label": label,
            "node_id": str(node.nodeid),
        })

    cards = (
        CardModel.objects.filter(
            graph__is_active=True,
            graph__isresource=True,
            nodegroup_id__in=nodes_by_nodegroup.keys(),
        )
        .exclude(graph__pk=settings.SYSTEM_SETTINGS_RESOURCE_MODEL_ID)
        .exclude(graph__source_identifier__isnull=False)
        .select_related("graph", "nodegroup")
    )

    graphs = {
        str(g.graphid): {
            "name": str(g.name.get("en", g.name) if isinstance(g.name, dict) else (g.name or "")),
            "slug": str(g.slug) if g.slug else None,
        }
        for g in GraphModel.objects.filter(
            is_active=True,
            isresource=True,
        )
        .exclude(pk=settings.SYSTEM_SETTINGS_RESOURCE_MODEL_ID)
        .exclude(source_identifier__isnull=False)
    }

    inventory = []

    for card in cards:
        graph_id = str(card.graph_id)
        graph_info = graphs.get(graph_id)

        if not graph_info or not graph_info["slug"]:
            continue

        ng = str(card.nodegroup_id)
        card_nodes = nodes_by_nodegroup.get(ng, [])

        if not card_nodes:
            continue

        inventory.append({
            "card_name": str(card.name),
            "graph_id": graph_id,
            "graph_name": str(graph_info["name"]),
            "nodegroup_id": ng,
            "nodes": sorted(card_nodes, key=lambda n: n["label"].lower()),
            "slug": str(graph_info["slug"]),
        })

    inventory.sort(key=lambda c: (c["graph_name"].lower(), c["card_name"].lower()))

    return inventory


def get_sample_value(node_id: str, datatype: str) -> str | None:
    if not _DJANGO_AVAILABLE:
        return None

    if datatype in STRING_DATATYPES:
        return _sample_string(node_id)

    if datatype in NUMBER_DATATYPES:
        return _sample_number(node_id)

    if datatype in DATE_DATATYPES:
        return _sample_date(node_id)

    return None


def _sample_string(node_id: str) -> str | None:
    tile = (
        TileModel.objects.filter(
            **{f"data__{node_id}__isnull": False},
        )
        .exclude(**{f"data__{node_id}": ""})
        .exclude(**{f"data__{node_id}": None})
        .values_list("data", flat=True)
        .first()
    )

    if not tile:
        return None

    raw = tile.get(node_id)

    if not raw:
        return None

    if isinstance(raw, dict):
        val = raw.get("en", {})

        if isinstance(val, dict):
            val = val.get("value", "")

        if isinstance(val, str) and len(val) >= 2:
            return val[:3]

        return None

    if isinstance(raw, str) and len(raw) >= 2:
        return raw[:3]

    return None


def _sample_number(node_id: str) -> str | None:
    tile = (
        TileModel.objects.filter(
            **{f"data__{node_id}__isnull": False},
        )
        .exclude(**{f"data__{node_id}": None})
        .values_list("data", flat=True)
        .first()
    )

    if not tile:
        return None

    raw = tile.get(node_id)

    if raw is not None and raw != "":
        return str(raw)

    return None


def _sample_date(node_id: str) -> str | None:
    tile = (
        TileModel.objects.filter(
            **{f"data__{node_id}__isnull": False},
        )
        .exclude(**{f"data__{node_id}": ""})
        .exclude(**{f"data__{node_id}": None})
        .values_list("data", flat=True)
        .first()
    )

    if not tile:
        return None

    raw = tile.get(node_id)

    if not raw:
        return None

    if isinstance(raw, str):
        return raw[:10]

    return None


def get_testable_qualifiers(datatype: str) -> set[str]:
    base = {"null", "not_null"}

    if datatype in STRING_DATATYPES:
        return base | {"~", "!~", "eq", "!eq"}

    if datatype in NUMBER_DATATYPES:
        return base | {"eq", "gt", "lt", "gte", "lte"}

    if datatype in DATE_DATATYPES:
        return base | {"eq", "gt", "lt", "gte", "lte"}

    if datatype in BOOLEAN_DATATYPES:
        return base | {"t", "f"}

    if datatype in GEO_DATATYPES:
        return base | {"Point", "LineString", "Polygon"}

    return base
