"""
Migrations to override the default Arches behavior, that cannot be handled by package JSON.
"""

from django.conf import settings
from django.core.management import call_command
from django.db import migrations

from arches.app.models.models import (
    MapLayer,
    MapMarker,
    MapSource,
    Plugin,
    ReportTemplate,
    SearchComponent,
    Widget,
)
from bcgov_arches_common.util.pkg_util import (
    get_mapbox_spec_files as get_common_mapbox_spec_files,
    update_map_source_prefix,
)

PATTERN_MARKERS = {
    "pattern-crosshatch-red": settings.STATIC_URL + "img/patterns/crosshatch-red.png",
    "pattern-vertical-red": settings.STATIC_URL + "img/patterns/vertical-red.png",
    "pattern-horizontal-red": settings.STATIC_URL + "img/patterns/horizontal-red.png",
}

reset_layer_sql = """
    update map_layers a set addtomap = addtomap_updated
        from (select maplayerid, name, case when name ~ '^Parks' or name = 'British Columbia Roads' then true else false end addtomap_updated, addtomap
        from map_layers) b
        where a.maplayerid = b.maplayerid;
        """


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


def reload_map_layers(apps, schema_editor):
    for layer_spec in get_common_mapbox_spec_files():
        call_command(
            "packages",
            operation="delete_mapbox_layer",
            layer_name=layer_spec["name"],
        )
        call_command(
            "packages",
            operation="add_mapbox_layer",
            layer_name=layer_spec["name"],
            mapbox_json_path=layer_spec["path"],
        )


def update_prefixes(apps, schema_editor):
    update_map_source_prefix("bcap")


def update_basemap(apps, schema_editor):
    MapLayer.objects.filter(name="streets").delete()
    MapSource.objects.filter(name="mapbox-streets").delete()
    widget = Widget.objects.filter(name="map-widget").first()
    widget.defaultconfig["basemap"] = "British Columbia Roads"
    widget.save()
    report_template = ReportTemplate.objects.filter(
        componentname="map-report"
    ).first()
    report_template.defaultconfig["basemap"] = "British Columbia Roads"
    report_template.save()


def show_etl_plugin_by_default(apps, schema_editor):
    plugin = Plugin.objects.filter(slug="bulk-data-manager").first()
    plugin.config.raw_value["show"] = True
    plugin.save()


def hide_etl_plugin_by_default(apps, schema_editor):
    plugin = Plugin.objects.filter(slug="bulk-data-manager").first()
    plugin.config.raw_value["show"] = False
    plugin.save()


def add_pattern_markers(apps, schema_editor):
    for name, url in PATTERN_MARKERS.items():
        MapMarker.objects.update_or_create(name=name, defaults={"url": url})


def remove_pattern_markers(apps, schema_editor):
    MapMarker.objects.filter(name__in=PATTERN_MARKERS).delete()


class Migration(migrations.Migration):

    replaces = [
        ("bcap", "0001a_update_active_languages"),
        ("bcap", "0001b_update_map_filter_config"),
        ("bcap", "0004_load_common_map_layers"),
        ("bcap", "0005_update_basemap"),
        ("bcap", "0619_alter_file_path_length"),
        ("bcap", "1032_update_map_filter_config"),
        ("bcap", "1100_show_etl_plugin_by_default"),
        ("bcap", "1411_update_arch_site_fill_styling"),
        ("bcap", "1412_load_industry_sector_skos"),
    ]

    dependencies = [
        ("bcap", "855_add_qgis_views"),
    ]

    operations = [
        migrations.RunSQL(
            "update languages set isdefault = code = 'en';",
            migrations.RunSQL.noop,
        ),
        migrations.RunPython(update_map_filter_config, revert_map_filter_config),
        migrations.RunPython(reload_map_layers, migrations.RunPython.noop),
        migrations.RunSQL(reset_layer_sql, migrations.RunSQL.noop),
        migrations.RunPython(update_prefixes, migrations.RunPython.noop),
        migrations.RunPython(update_basemap, migrations.RunPython.noop),
        migrations.RunSQL(
            "alter table files alter column path type varchar(255);",
            "alter table files alter column path type varchar(100);",
        ),
        migrations.RunPython(show_etl_plugin_by_default, hide_etl_plugin_by_default),
        migrations.RunPython(add_pattern_markers, remove_pattern_markers),
    ]
