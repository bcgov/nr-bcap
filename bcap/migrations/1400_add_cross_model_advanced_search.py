from django.db import migrations


class Migration(migrations.Migration):

    atomic = False

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
        migrations.RunSQL(
            sql="""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tiles_tiledata_gin
                ON tiles USING gin (tiledata jsonb_path_ops);
            """,
            reverse_sql="""
                DROP INDEX CONCURRENTLY IF EXISTS idx_tiles_tiledata_gin;
            """,
        ),
        migrations.RunSQL(
            sql="""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_resource_instances_graph_resource
                ON resource_instances (graphid, resourceinstanceid);
            """,
            reverse_sql="""
                DROP INDEX CONCURRENTLY IF EXISTS idx_resource_instances_graph_resource;
            """,
        ),
        migrations.RunSQL(
            sql="""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tiles_nodegroup_resource
                ON tiles (nodegroupid, resourceinstanceid);
            """,
            reverse_sql="""
                DROP INDEX CONCURRENTLY IF EXISTS idx_tiles_nodegroup_resource;
            """,
        ),
        migrations.RunSQL(
            sql="""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tiles_data_gin_ops
                ON tiles USING gin (tiledata);
            """,
            reverse_sql="""
                DROP INDEX CONCURRENTLY IF EXISTS idx_tiles_data_gin_ops;
            """,
        ),
        migrations.RunSQL(
            sql="""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_rxr_forward_lookup
                ON resource_x_resource (resourceinstanceto_graphid, resourceinstanceidfrom)
                INCLUDE (resourceinstanceidto);
            """,
            reverse_sql="""
                DROP INDEX CONCURRENTLY IF EXISTS idx_rxr_forward_lookup;
            """,
        ),
        migrations.RunSQL(
            sql="""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_rxr_reverse_lookup
                ON resource_x_resource (resourceinstancefrom_graphid, resourceinstanceidto)
                INCLUDE (resourceinstanceidfrom);
            """,
            reverse_sql="""
                DROP INDEX CONCURRENTLY IF EXISTS idx_rxr_reverse_lookup;
            """,
        ),
        migrations.RunSQL(
            sql="""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_rxr_from_resource
                ON resource_x_resource (resourceinstanceidfrom)
                INCLUDE (resourceinstanceidto);
            """,
            reverse_sql="""
                DROP INDEX CONCURRENTLY IF EXISTS idx_rxr_from_resource;
            """,
        ),
        migrations.RunSQL(
            sql="""
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_rxr_to_resource
                ON resource_x_resource (resourceinstanceidto)
                INCLUDE (resourceinstanceidfrom);
            """,
            reverse_sql="""
                DROP INDEX CONCURRENTLY IF EXISTS idx_rxr_to_resource;
            """,
        ),
    ]
