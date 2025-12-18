from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("bcap", "1200_add_translate_to_resource_type"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                DELETE FROM search_component
                WHERE componentname IN ('ids-filter', 'ids');

                INSERT INTO search_component (
                    searchcomponentid,
                    name,
                    icon,
                    modulename,
                    classname,
                    type,
                    componentpath,
                    componentname,
                    config
                ) VALUES (
                    'f0e0c7d8-a9b8-4567-cdef-123456789abc',
                    'Resource IDs Filter',
                    '',
                    'ids_filter.py',
                    'IdsFilter',
                    'filter',
                    '',
                    'ids',
                    '{}'::jsonb
                )
                ON CONFLICT (searchcomponentid) DO UPDATE SET
                    componentname = EXCLUDED.componentname,
                    modulename = EXCLUDED.modulename,
                    classname = EXCLUDED.classname;
            """,
            reverse_sql="""
                DELETE FROM search_component
                WHERE componentname = 'ids';
            """,
        ),
    ]
