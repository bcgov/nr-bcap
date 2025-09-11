from django.db import migrations
from django.core.management import call_command
from bcgov_arches_common.migrations.operations.privileged_sql import RunPrivilegedSQL
from django.conf import settings
import os
from .util.migration_util import format_sql


class Migration(migrations.Migration):
    dependencies = [
        ("bcap", "0001d_fix_relational_views_for_reference_datatypes"),
    ]

    create_resource_proxy_views_sql = """
        select __arches_create_resource_model_views(graphid)
            from graphs
            where isresource = true
              and publicationid is not null
              and name->>'en' != 'Arches System Settings';
        """

    create_node_aliases_function_file = os.path.join(
        "sql", "2024", "2024-12-02___bc_create_node_aliases.sql"
    )
    sql_dir = os.path.join(os.path.dirname(__file__), "sql")

    create_node_aliases_sql = """ 
        call __bc_create_node_aliases('collection_event', 'fossil_collection_event');
        call __bc_create_node_aliases('fossil_sample');
        call __bc_create_node_aliases('fossil_type');
        call __bc_create_node_aliases('storage_location','fossil_storage_location');
        call __bc_create_node_aliases('publication');
        call __bc_create_node_aliases('contributor');
    """

    @staticmethod
    def load_package(app, someethingelse):
        call_command(
            "packages",
            operation="load_package",
            source=f"{settings.APP_ROOT}/pkg",
            yes=True,
        )

    @staticmethod
    def create_cache(app, somethingelse):
        call_command("createcachetable")

    operations = [
        migrations.RunPython(create_cache, migrations.RunPython.noop),
        migrations.RunPython(load_package, migrations.RunPython.noop),
        migrations.RunSQL(
            create_resource_proxy_views_sql,
            migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            format_sql(create_node_aliases_function_file),
            migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            create_node_aliases_sql,
            migrations.RunSQL.noop,
        ),
    ]
