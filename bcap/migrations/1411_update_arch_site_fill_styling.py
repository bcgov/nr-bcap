import os

from django.conf import settings
from django.db import migrations
from arches.app.models.models import MapMarker

from bcap.migrations.util.migration_util import format_sql

PATTERN_MARKERS = {
    "pattern-crosshatch-red": settings.STATIC_URL + "img/patterns/crosshatch-red.png",
    "pattern-vertical-red": settings.STATIC_URL + "img/patterns/vertical-red.png",
    "pattern-horizontal-red": settings.STATIC_URL + "img/patterns/horizontal-red.png",
}


def add_pattern_markers(apps, schema_editor):
    for name, url in PATTERN_MARKERS.items():
        MapMarker.objects.update_or_create(name=name, defaults={"url": url})


def remove_pattern_markers(apps, schema_editor):
    MapMarker.objects.filter(name__in=PATTERN_MARKERS).delete()


class Migration(migrations.Migration):

    dependencies = [("bcap", "855_add_qgis_views")]

    forward_file = os.path.join(
        "sql", "v100", "v2026.05.11__get_map_attribute_data.sql"
    )

    operations = [
        migrations.RunSQL(
            format_sql(forward_file),
            migrations.RunSQL.noop,
        ),
        migrations.RunPython(add_pattern_markers, remove_pattern_markers),
    ]
