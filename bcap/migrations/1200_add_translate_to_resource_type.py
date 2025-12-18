from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("bcap", "1100_show_etl_plugin_by_default"),
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
                    'b2c3d4e5-f6a7-8901-bcde-f12345678901',
                    'Translate to Resource Type',
                    'fa fa-exchange',
                    'translate_to_resource_type_filter.py',
                    'TranslateToResourceTypeFilter',
                    'popup',
                    'views/components/search/translate-to-resource-type-filter',
                    'translate-to-resource-type-filter',
                    '{}'::jsonb
                )
                ON CONFLICT (searchcomponentid) DO NOTHING;
            """,
            reverse_sql="""
                DELETE FROM search_component
                WHERE componentname = 'translate-to-resource-type-filter';
            """,
        ),
    ]
