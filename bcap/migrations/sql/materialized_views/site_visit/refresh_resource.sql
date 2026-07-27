-- GENERATED - edit sv_spec.py and re-run generate.py. Do not hand-edit.
-- Refresh order: geometry first (branches embed GeoJSON), then branches, then final.

CREATE OR REPLACE PROCEDURE site_visit.refresh_resource(concurrent boolean DEFAULT true)
LANGUAGE plpgsql AS $$
DECLARE
    mode text := CASE WHEN concurrent THEN 'CONCURRENTLY' ELSE '' END;
    mv   text;
BEGIN
    FOREACH mv IN ARRAY ARRAY[
        'site_visit.mv_geom_site_visit_location',
        'site_visit.mv_site_visit_location',
        'site_visit.mv_identification',
        'site_visit.mv_site_visit_details',
        'site_visit.mv_archaeological_data',
        'site_visit.mv_remarks_and_recommendations',
        'site_visit.mv_ancestral_remains',
        'site_visit.mv_related_documents',
        'site_visit.mv_resource_v1'
    ]
    LOOP
        RAISE NOTICE 'refreshing %', mv;
        EXECUTE format('REFRESH MATERIALIZED VIEW %s %s', mode, mv);
        COMMIT;
    END LOOP;
END $$;
