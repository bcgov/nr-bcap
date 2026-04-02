from django.db import migrations


def forward(apps, schema_editor):
    pass


def backward(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("bcap", "855_add_qgis_views"),
    ]

    operations = [migrations.RunPython(forward, backward)]
