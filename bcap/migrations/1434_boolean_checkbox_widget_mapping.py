from django.db import migrations

from arches_vue_components.models import WidgetMapping

KO_COMPONENT = "views/components/widgets/checkbox-boolean-widget"
VUE_COMPONENT = (
    "bcgov_arches_common/widgets/BooleanCheckboxWidget/BooleanCheckboxWidget.vue"
)


def point_mapping_at_vue_widget(apps, schema_editor):
    WidgetMapping.objects.filter(widget__name="checkbox-boolean-widget").update(
        component=VUE_COMPONENT
    )


def point_mapping_at_knockout_widget(apps, schema_editor):
    WidgetMapping.objects.filter(widget__name="checkbox-boolean-widget").update(
        component=KO_COMPONENT
    )


class Migration(migrations.Migration):
    """arches_vue_components 0002 mapped every widget it did not recognize to that
    widget's Knockout component, so GenericWidget tried to import a .vue file that
    does not exist and rendered a "Cannot find module" error instead of the field.
    """

    dependencies = [
        ("bcap", "1433_create_databc_views"),
        ("arches_vue_components", "0002_populate_widget_mappings"),
    ]

    operations = [
        migrations.RunPython(
            point_mapping_at_vue_widget, point_mapping_at_knockout_widget
        ),
    ]
