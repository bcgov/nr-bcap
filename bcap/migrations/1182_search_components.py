"""Consolidated bcap search components.

Registers the three bcap/arches search components and wires the two custom ones
into the standard-search-view, plus the cross-model advanced-search support
indexes. Search components have no JSON/XML loader and `search register` does a
non-idempotent plain create, so these stay as idempotent SQL (ON CONFLICT /
NOT EXISTS guards).
"""

from django.db import migrations


class Migration(migrations.Migration):

    replaces = [
        ("bcap", "1182a_add_translate_to_resource_type"),
        ("bcap", "1182b_add_resource_ids_filter"),
        ("bcap", "1182c_add_cross_model_advanced_search"),
    ]

    dependencies = [
        ("bcap", "1031_add_borden_number_counter_model"),
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
                WHERE componentname = 'standard-search-view'
                AND NOT EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements(config->'linkedSearchFilters') AS elem
                    WHERE elem->>'componentname' = 'translate-to-resource-type-filter'
                );
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
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS idx_tiles_tiledata_gin
                ON tiles USING gin (tiledata jsonb_path_ops);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS idx_tiles_tiledata_gin;
            """,
        ),
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS idx_resource_instances_graph_resource
                ON resource_instances (graphid, resourceinstanceid);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS idx_resource_instances_graph_resource;
            """,
        ),
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS idx_tiles_nodegroup_resource
                ON tiles (nodegroupid, resourceinstanceid);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS idx_tiles_nodegroup_resource;
            """,
        ),
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS idx_tiles_data_gin_ops
                ON tiles USING gin (tiledata);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS idx_tiles_data_gin_ops;
            """,
        ),
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS idx_rxr_forward_lookup
                ON resource_x_resource (resourceinstanceto_graphid, resourceinstanceidfrom)
                INCLUDE (resourceinstanceidto);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS idx_rxr_forward_lookup;
            """,
        ),
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS idx_rxr_reverse_lookup
                ON resource_x_resource (resourceinstancefrom_graphid, resourceinstanceidto)
                INCLUDE (resourceinstanceidfrom);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS idx_rxr_reverse_lookup;
            """,
        ),
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS idx_rxr_from_resource
                ON resource_x_resource (resourceinstanceidfrom)
                INCLUDE (resourceinstanceidto);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS idx_rxr_from_resource;
            """,
        ),
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS idx_rxr_to_resource
                ON resource_x_resource (resourceinstanceidto)
                INCLUDE (resourceinstanceidfrom);
            """,
            reverse_sql="""
                DROP INDEX IF EXISTS idx_rxr_to_resource;
            """,
        ),
    ]
