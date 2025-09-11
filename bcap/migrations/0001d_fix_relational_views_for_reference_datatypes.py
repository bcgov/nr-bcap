from django.db import migrations
import os
from .util.migration_util import format_sql


class Migration(migrations.Migration):
    dependencies = [
        ("bcap", "0001c_create_map_attribute_data_function"),
    ]

    forward_file = os.path.join(
        "sql", "v100", "v2025.09.09__arches_get_node_value_sql.sql"
    )

    operations = [
        migrations.RunSQL(
            format_sql(forward_file),
            migrations.RunSQL.noop,
        ),
    ]
