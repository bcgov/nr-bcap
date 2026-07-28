-- GENERATED - edit rep_spec.py and re-run generate.py. Do not hand-edit.

CREATE OR REPLACE PROCEDURE repository.refresh_flat(concurrent boolean DEFAULT true)
LANGUAGE plpgsql AS $$
DECLARE
    mode text := CASE WHEN concurrent THEN 'CONCURRENTLY' ELSE '' END;
    mv   text;
BEGIN
    FOREACH mv IN ARRAY ARRAY[
        'repository.mv_resource_flat_v1'
    ]
    LOOP
        RAISE NOTICE 'refreshing %', mv;
        EXECUTE format('REFRESH MATERIALIZED VIEW %s %s', mode, mv);
        COMMIT;
    END LOOP;
END $$;
