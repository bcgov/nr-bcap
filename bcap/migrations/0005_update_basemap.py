from django.db import migrations
from django.db.migrations.operations.special import RunPython
from arches.app.models.models import MapSource, MapLayer, Widget, ReportTemplate


def update_basemap(apps, schema_editor):
    MapLayer.objects.filter(name="streets").delete()
    MapSource.objects.filter(name="mapbox-streets").delete()
    widget = Widget.objects.filter(name="map-widget").first()
    widget.defaultconfig["basemap"] = "British Columbia Roads"
    widget.save()
    report_template = ReportTemplate.objects.filter(componentname="map-report").first()
    report_template.defaultconfig["basemap"] = "British Columbia Roads"
    report_template.save()


class Migration(migrations.Migration):

    dependencies = [
        ("bcap", "0004_load_common_map_layers"),
    ]

    operations = [RunPython(update_basemap, RunPython.noop)]
