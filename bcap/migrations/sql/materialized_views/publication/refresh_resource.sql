-- GENERATED - edit pub_spec.py and re-run generate.py. Do not hand-edit.
-- Refresh order: geometry first (branches embed GeoJSON), then branches, then final.

CREATE OR REPLACE PROCEDURE publication.refresh_resource(concurrent boolean DEFAULT true)
LANGUAGE plpgsql AS $$
DECLARE
    mode text := CASE WHEN concurrent THEN 'CONCURRENTLY' ELSE '' END;
    mv   text;
BEGIN
    FOREACH mv IN ARRAY ARRAY[
        'publication.mv_reference_link',
        'publication.mv_information_carrier',
        'publication.mv_copyright_type',
        'publication.mv_keyword',
        'publication.mv_authors',
        'publication.mv_publication_details',
        'publication.mv_resource_v1'
    ]
    LOOP
        RAISE NOTICE 'refreshing %', mv;
        EXECUTE format('REFRESH MATERIALIZED VIEW %s %s', mode, mv);
        COMMIT;
    END LOOP;
END $$;
