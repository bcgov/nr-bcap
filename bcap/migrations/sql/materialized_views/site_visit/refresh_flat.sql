-- GENERATED - edit sv_spec.py and re-run generate.py. Do not hand-edit.

CREATE OR REPLACE PROCEDURE site_visit.refresh_flat(concurrent boolean DEFAULT true)
LANGUAGE plpgsql AS $$
DECLARE
    mode text := CASE WHEN concurrent THEN 'CONCURRENTLY' ELSE '' END;
    mv   text;
BEGIN
    FOREACH mv IN ARRAY ARRAY[
        'site_visit.mv_resource_flat_v1',
        'site_visit.mv_site_visit_location_flat_v1'
    ]
    LOOP
        RAISE NOTICE 'refreshing %', mv;
        EXECUTE format('REFRESH MATERIALIZED VIEW %s %s', mode, mv);
        COMMIT;
    END LOOP;
END $$;
