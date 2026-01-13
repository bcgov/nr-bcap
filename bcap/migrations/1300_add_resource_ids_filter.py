from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("bcap", "1200_add_translate_to_resource_type"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
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
                    'f1856bfb-c3c4-4d67-8f23-0aa3eef3a160',
                    'ResourceIds Filter',
                    '',
                    'ids.py',
                    'ResourceIdsFilter',
                    'ids-filter-type',
                    NULL,
                    'ids',
                    '{}'::jsonb
                )
                ON CONFLICT (searchcomponentid) DO NOTHING;
            """,
            reverse_sql="""
                DELETE FROM search_component
                WHERE componentname = 'ids';
            """,
        ),
    ]
