from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("bcap", "1300_add_resource_ids_filter"),
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
                )
                VALUES (
                    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
                    'Cross-Model Advanced Search',
                    'fa fa-search-plus',
                    'cross_model_advanced_search.py',
                    'CrossModelAdvancedSearch',
                    'cross-model-advanced-search-type',
                    'views/components/search/cross-model-advanced-search',
                    'cross-model-advanced-search',
                    '{"layoutType": "tabbed"}'::jsonb
                )
                ON CONFLICT (searchcomponentid) DO NOTHING;

                UPDATE search_component
                SET config = jsonb_set(
                    config,
                    '{linkedSearchFilters}',
                    config->'linkedSearchFilters' || '[{
                        "componentname": "cross-model-advanced-search",
                        "layoutSortorder": 3,
                        "searchcomponentid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
                    }]'::jsonb
                )
                WHERE componentname = 'standard-search-view'
                AND NOT EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements(config->'linkedSearchFilters') AS elem
                    WHERE elem->>'componentname' = 'cross-model-advanced-search'
                );
            """,
            reverse_sql="""
                UPDATE search_component
                SET config = jsonb_set(
                    config,
                    '{linkedSearchFilters}',
                    (
                        SELECT jsonb_agg(elem)
                        FROM jsonb_array_elements(config->'linkedSearchFilters') AS elem
                        WHERE elem->>'componentname' != 'cross-model-advanced-search'
                    )
                )
                WHERE componentname = 'standard-search-view';

                DELETE FROM search_component
                WHERE componentname = 'cross-model-advanced-search';
            """,
        ),
    ]
