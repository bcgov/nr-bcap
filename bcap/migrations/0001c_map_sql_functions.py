import os

from django.db import migrations

from .util.migration_util import format_sql

# Consolidates the two pre-load_package SQL-function migrations:
#   0001c — get_map_attribute_data (latest version, formerly re-applied by 1411)
#   0001d — arches_get_node_value_sql (relational views for reference datatypes)


class Migration(migrations.Migration):

    replaces = [
        ("bcap", "0001c_create_map_attribute_data_function"),
        ("bcap", "0001d_fix_relational_views_for_reference_datatypes"),
    ]

    dependencies = [
        ("bcap", "0001_initial"),
    ]

    get_map_attribute_data_file = os.path.join(
        "sql", "v100", "v2026.05.11__get_map_attribute_data.sql"
    )
    arches_get_node_value_file = os.path.join(
        "sql", "v100", "v2025.09.09__arches_get_node_value_sql.sql"
    )

    operations = [
        migrations.RunSQL(
            format_sql(get_map_attribute_data_file),
            migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            format_sql(arches_get_node_value_file),
            migrations.RunSQL.noop,
        ),
    ]
