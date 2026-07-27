-- GENERATED - edit as_spec.py and re-run generate.py. Do not hand-edit.
-- Refresh order: geometry first (branches embed GeoJSON), then branches, then final.

CREATE OR REPLACE PROCEDURE archaeological_site.refresh_resource(concurrent boolean DEFAULT true)
LANGUAGE plpgsql AS $$
DECLARE
    mode text := CASE WHEN concurrent THEN 'CONCURRENTLY' ELSE '' END;
    mv   text;
BEGIN
    FOREACH mv IN ARRAY ARRAY[
        'archaeological_site.mv_geom_site_boundary',
        'archaeological_site.mv_geom_unprotected_areas',
        'archaeological_site.mv_site_boundary',
        'archaeological_site.mv_identification_and_registration',
        'archaeological_site.mv_site_location',
        'archaeological_site.mv_archaeological_data',
        'archaeological_site.mv_site_record_admin',
        'archaeological_site.mv_external_url',
        'archaeological_site.mv_ancestral_remains',
        'archaeological_site.mv_remarks_and_restricted_information',
        'archaeological_site.mv_related_documents',
        'archaeological_site.mv_resource_v1'
    ]
    LOOP
        RAISE NOTICE 'refreshing %', mv;
        EXECUTE format('REFRESH MATERIALIZED VIEW %s %s', mode, mv);
        COMMIT;
    END LOOP;
END $$;
