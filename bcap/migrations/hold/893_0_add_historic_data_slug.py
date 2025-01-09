from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("bcap", "665_5_reorder_map_layers"),
    ]

    sql = """
            update graphs set slug = 'heritage_site_historical_data' where name->>'en' = 'Heritage Site Historical Data';
    """

    reverse_sql = """
            update graphs set slug = null where name->>'en' = 'Heritage Site Historical Data';
    """

    operations = [
        migrations.RunSQL(
            sql,
            reverse_sql,
        ),
    ]
