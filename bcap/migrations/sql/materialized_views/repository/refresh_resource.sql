-- GENERATED - edit rep_spec.py and re-run generate.py. Do not hand-edit.
-- Refresh order: geometry first (branches embed GeoJSON), then branches, then final.

CREATE OR REPLACE PROCEDURE repository.refresh_resource(concurrent boolean DEFAULT true)
LANGUAGE plpgsql AS $$
DECLARE
    mode text := CASE WHEN concurrent THEN 'CONCURRENTLY' ELSE '' END;
    mv   text;
BEGIN
    FOREACH mv IN ARRAY ARRAY[
        'repository.mv_geom_physical_location',
        'repository.mv_contact_information',
        'repository.mv_repository_notes',
        'repository.mv_repository_identifier',
        'repository.mv_resource_v1'
    ]
    LOOP
        RAISE NOTICE 'refreshing %', mv;
        EXECUTE format('REFRESH MATERIALIZED VIEW %s %s', mode, mv);
        COMMIT;
    END LOOP;
END $$;
