from django.db import migrations
from arches.app.models.models import SearchComponent


class Migration(migrations.Migration):
    dependencies = [
        ("bcap", "0001a_update_active_languages"),
    ]

    @staticmethod
    def update_map_filter(app, otherconfig):
        search_component = SearchComponent.objects.filter(
            componentname="map-filter"
        ).first()
        search_component.modulename = "bc_map_filter.py"
        search_component.classname = "BCMapFilter"

    operations = [
        migrations.RunPython(
            update_map_filter,
            migrations.RunPython.noop,
        ),
    ]
