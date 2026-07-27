-- GENERATED - edit per_spec.py and re-run generate.py. Do not hand-edit.
-- Refresh order: geometry first (branches embed GeoJSON), then branches, then final.

CREATE OR REPLACE PROCEDURE hca_permit.refresh_resource(concurrent boolean DEFAULT true)
LANGUAGE plpgsql AS $$
DECLARE
    mode text := CASE WHEN concurrent THEN 'CONCURRENTLY' ELSE '' END;
    mv   text;
BEGIN
    FOREACH mv IN ARRAY ARRAY[
        'hca_permit.mv_permit_identification',
        'hca_permit.mv_resource_v1'
    ]
    LOOP
        RAISE NOTICE 'refreshing %', mv;
        EXECUTE format('REFRESH MATERIALIZED VIEW %s %s', mode, mv);
        COMMIT;
    END LOOP;
END $$;
