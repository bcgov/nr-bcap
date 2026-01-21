from django.db import migrations
from django_migrate_sql.config import SQLItem
from bcap.migrations.util.migration_util import format_sql


sql_items = [
    SQLItem(
        "bc_labelled_geojson_geometries",
        format_sql("sql/views/bc_labelled_geojson_geometries.sql", ),
        reverse_sql="drop view bc_labelled_geojson_geometries;",
        replace=True,
    ),
    SQLItem(
        "bc_labelled_site_geometries",
        format_sql("sql/views/bc_labelled_site_geometries.sql", ),
        reverse_sql="drop view bc_labelled_site_geometries;",
        replace=True,
    ),
    SQLItem(
        "bc_labelled_site_visit_geometries",
        format_sql("sql/views/bc_labelled_site_visit_geometries.sql", ),
        reverse_sql="drop view bc_labelled_site_visit_geometries;",
        replace=True,
    ),
    SQLItem(
        "bc_labelled_sandcastle_geometries",
        format_sql("sql/views/bc_labelled_sandcastle_geometries.sql", ),
        reverse_sql="drop view bc_labelled_sandcastle_geometries;",
        replace=True,
    ),
]
