from django.db import migrations
from django.db.migrations.operations.special import RunPython
from arches.app.models.models import SearchComponent


def update_map_filter_config(apps, schema_editor):
    map_filter_component = SearchComponent.objects.filter(
        type="map-filter-type"
    ).first()
    map_filter_component.classname = "BCMapFilter"
    map_filter_component.modulename = "bc_map_filter.py"
    map_filter_component.save()


def revert_map_filter_config(apps, schema_editor):
    map_filter_component = SearchComponent.objects.filter(
        type="map-filter-type"
    ).first()
    map_filter_component.classname = "MapFilter"
    map_filter_component.modulename = "map_filter.py"
    map_filter_component.save()


class Migration(migrations.Migration):

    dependencies = [
        ("bcap", "0619_alter_file_path_length"),
    ]

    operations = [RunPython(update_map_filter_config, revert_map_filter_config)]
