from django.db import migrations


class Migration(migrations.Migration):
    # CREATE INDEX CONCURRENTLY cannot run inside a transaction.
    atomic = False

    dependencies = [
        ("bcap", "1413_resourcedraft"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
                "edit_log_tileinstanceid_idx ON edit_log (tileinstanceid);"
            ),
            reverse_sql=(
                "DROP INDEX CONCURRENTLY IF EXISTS edit_log_tileinstanceid_idx;"
            ),
        ),
    ]
