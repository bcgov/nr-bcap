from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("bcap", "0005_update_basemap"),
    ]

    operations = [
        migrations.RunSQL(
            "alter table files alter column path type varchar(255);",
            "alter table files alter column path type varchar(100);",
        ),
    ]
