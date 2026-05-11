import json
import os

from django.db import migrations
from arches.app.models.models import Node
from bcap.migrations.util.migration_util import format_sql

ARCH_SITE_GEOM_NODE = "b18223c2-13ef-11f0-8695-0242ac170007"
SOURCE_NAME = f"resources-{ARCH_SITE_GEOM_NODE}"

# Note this takes out line + halo + hover + cluster + click + count stylings
# that you'd typically see when you toggle advanced settings on.
FILL_ID = f"resources-fill-{ARCH_SITE_GEOM_NODE}"
OUTLINE_ID = f"resources-poly-outline-{ARCH_SITE_GEOM_NODE}"
PATTERN_ID = f"site-polygon-pattern-fill-{ARCH_SITE_GEOM_NODE}"
LABELS_ID = "site-polygon-borden-labels"

# fmt: off
STATUS_FILL_COLOR = [
    "match",
    ["coalesce", ["get", "registration_status"], ""],
    "Registered",           "rgba(255,0,0,0.7)",
    "Registry Candidate",   "rgba(255,0,0,0.7)",
    "Decision Pending",     "rgba(255,0,0,0.7)",
    "Federal Jurisdiction", "rgba(255,0,0,0.3)",
    "Legacy",               "rgba(0,0,0,0)",
    "Recorded/Unprotected", "rgba(0,0,0,0)",
    "Cancelled Record",     "rgba(0,0,0,0)",
    "rgba(255,0,0,0.7)",
]

STATUS_LINE_COLOR = [
    "match",
    ["coalesce", ["get", "registration_status"], ""],
    "Registered",           "rgba(255,0,0,1)",
    "Registry Candidate",   "rgba(255,0,0,1)",
    "Decision Pending",     "rgba(255,0,0,1)",
    "Federal Jurisdiction", "rgba(255,0,0,0.7)",
    "Legacy",               "rgba(255,0,0,1)",
    "Recorded/Unprotected", "rgba(255,0,0,1)",
    "Cancelled Record",     "rgba(255,0,0,1)",
    "rgba(255,0,0,1)",
]
# fmt: on


def update_arch_site_styling(apps, schema_editor):
    node = Node.objects.get(nodeid=ARCH_SITE_GEOM_NODE)

    defs = json.loads(node.config.get("advancedStyle") or "[]")

    by_id = {ld["id"]: ld for ld in defs}

    if FILL_ID not in by_id:
        layer = {
            "id": FILL_ID,
            "type": "fill",
            "source": SOURCE_NAME,
            "source-layer": ARCH_SITE_GEOM_NODE,
            "layout": {"visibility": "visible"},
            "paint": {
                "fill-color": node.config.get("fillColor", "rgba(255,122,0,0.73)")
            },
        }
        defs.append(layer)
        by_id[FILL_ID] = layer
    by_id[FILL_ID]["paint"]["fill-color"] = STATUS_FILL_COLOR

    if OUTLINE_ID not in by_id:
        layer = {
            "id": OUTLINE_ID,
            "type": "line",
            "source": SOURCE_NAME,
            "source-layer": ARCH_SITE_GEOM_NODE,
            "layout": {"visibility": "visible"},
            "paint": {
                "line-color": node.config.get("outlineColor", "rgba(255,122,0,0.3)")
            },
        }
        defs.append(layer)
        by_id[OUTLINE_ID] = layer
    by_id[OUTLINE_ID]["paint"]["line-color"] = STATUS_LINE_COLOR

    source = by_id[FILL_ID]["source"]
    source_layer = by_id[FILL_ID].get("source-layer", ARCH_SITE_GEOM_NODE)

    if PATTERN_ID not in by_id:
        defs.append(
            {
                "id": PATTERN_ID,
                "type": "fill",
                "source": source,
                "source-layer": source_layer,
                "layout": {"visibility": "visible"},
                "filter": [
                    "in",
                    ["get", "registration_status"],
                    ["literal", ["Legacy", "Recorded/Unprotected", "Cancelled Record"]],
                ],
                "paint": {
                    "fill-pattern": [
                        "match",
                        ["get", "registration_status"],
                        "Legacy",
                        "pattern-crosshatch",
                        "Recorded/Unprotected",
                        "pattern-vertical",
                        "Cancelled Record",
                        "pattern-horizontal",
                        "pattern-horizontal",
                    ],
                },
            }
        )

    if LABELS_ID not in by_id:
        defs.append(
            {
                "id": LABELS_ID,
                "type": "symbol",
                "source": source,
                "source-layer": source_layer,
                "layout": {
                    "visibility": "visible",
                    "text-field": ["coalesce", ["get", "borden_number"], ""],
                    "text-size": 12,
                    "text-font": ["Open Sans Bold", "Arial Unicode MS Bold"],
                    "text-allow-overlap": False,
                    "text-ignore-placement": False,
                },
                "paint": {
                    "text-color": "#333333",
                    "text-halo-color": "rgba(255,255,255,0.9)",
                    "text-halo-width": 1.5,
                },
            }
        )

    node.config["advancedStyling"] = True
    # Required so editor shows nice json
    node.config["advancedStyle"] = json.dumps(defs, indent=2)
    node.save()


def revert_arch_site_styling(apps, schema_editor):
    node = Node.objects.get(nodeid=ARCH_SITE_GEOM_NODE)
    node.config["advancedStyling"] = False
    node.config["advancedStyle"] = ""
    node.save()


class Migration(migrations.Migration):

    dependencies = [("bcap", "1291_add_internal_plugin")]

    forward_file = os.path.join(
        "sql", "v100", "v2026.05.11__get_map_attribute_data.sql"
    )

    operations = [
        migrations.RunSQL(
            format_sql(forward_file),
            migrations.RunSQL.noop,
        ),
        migrations.RunPython(update_arch_site_styling, revert_arch_site_styling),
    ]
