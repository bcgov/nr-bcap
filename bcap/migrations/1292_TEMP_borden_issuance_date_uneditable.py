# TEMP: remove this migration once the resource_models JSON is regenerated.
# The `uneditable: true` change has been applied directly to
# bcap/pkg/graphs/resource_models/Archaeological Site.json, so any fresh
# package load already carries it. This migration only exists to update
# environments where the graph was loaded before that JSON change.
from arches.app.models.models import CardXNodeXWidget
from arches.app.models.graph import Graph
from django.db import migrations


ARCH_SITE_GRAPH = "cef9c510-e3e6-4057-ac08-89ad926180b4"
CARD_X_NODE_X_WIDGET_ID = "86aa4b00-f92f-487b-81ea-74694f6db441"


def set_uneditable(value, notes):
    cxnxw = CardXNodeXWidget.objects.get(pk=CARD_X_NODE_X_WIDGET_ID)
    cxnxw.config["uneditable"] = value
    cxnxw.save()

    graph = Graph.objects.get(graphid=ARCH_SITE_GRAPH, source_identifier_id=None)
    graph.update_published_graphs(notes=notes)


def forwards(apps, schema_editor):
    set_uneditable(True, notes="set borden_number_issuance_date uneditable=true")


def backwards(apps, schema_editor):
    set_uneditable(False, notes="revert borden_number_issuance_date uneditable=false")


class Migration(migrations.Migration):
    dependencies = [
        ("bcap", "1291_add_internal_plugin"),
    ]
    operations = [migrations.RunPython(forwards, backwards)]
