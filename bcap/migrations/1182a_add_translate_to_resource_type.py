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
                    'filter',
                    'views/components/search/translate-to-resource-type-filter',
                    'translate-to-resource-type-filter',
                    '{}'::jsonb
                )
                ON CONFLICT (searchcomponentid) DO NOTHING;

                UPDATE search_component
                SET config = jsonb_set(
                    config,
                    '{linkedSearchFilters}',
                    config->'linkedSearchFilters' || '[{
                        "componentname": "translate-to-resource-type-filter",
                        "searchcomponentid": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
                        "layoutSortorder": 15
                    }]'::jsonb
                )
                WHERE componentname = 'standard-search-view';
            """,
            reverse_sql="""
                UPDATE search_component
                SET config = jsonb_set(
                    config,
                    '{linkedSearchFilters}',
                    (
                        SELECT COALESCE(jsonb_agg(elem), '[]'::jsonb)
                        FROM jsonb_array_elements(config->'linkedSearchFilters') elem
                        WHERE elem->>'componentname' != 'translate-to-resource-type-filter'
                    )
                )
                WHERE componentname = 'standard-search-view';

                DELETE FROM search_component
                WHERE componentname = 'translate-to-resource-type-filter';
            """,
        ),
    ]
