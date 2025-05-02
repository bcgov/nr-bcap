from django.db import migrations
import os
from .util.migration_util import format_sql


class Migration(migrations.Migration):
    dependencies = [
        ("bcap", "0001b_update_map_filter_config"),
    ]

    forward_file = os.path.join(
        "sql", "v100", "v2025.05.02.0215__get_map_attribute_data.sql"
    )

    operations = [
        migrations.RunSQL(
            format_sql(forward_file),
            migrations.RunSQL.noop,
        ),
    ]
