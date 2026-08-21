-- GENERATED - edit as_spec.py and re-run generate.py. Do not hand-edit.
-- Graph cef9c510-e3e6-4057-ac08-89ad926180b4
-- Requires 00_arches_util.sql (arches_util helpers) to be applied first.
--
-- Reads public.tiles DIRECTLY. The generated archaeological_site.* views are NOT used:
-- each LEFT JOINs edit_log twice with a text->uuid cast that no index can serve.
--
-- INVARIANTS (downstream depends on these - do not change silently):
--   * every key ALWAYS present; empty means null, never absent. No jsonb_strip_nulls.
--   * cardinality-n children are ALWAYS a jsonb array, [] when empty, never null.
--   * cardinality-1 branches are an object, or null when the tile does not exist.
--   * array order is tiles.sortorder, then tileid. Stable across refreshes.

SET client_min_messages = warning;   -- ST_MakeValid emits a NOTICE per repair
SET maintenance_work_mem = '512MB';
SET work_mem             = '128MB';

CREATE SCHEMA IF NOT EXISTS archaeological_site;

-- ---------------------------------------------------------------------
-- identification_and_registration  (cardinality 1)  children: site_alert, site_decision, site_names, authority
-- ---------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_identification_and_registration CASCADE;
CREATE MATERIALIZED VIEW archaeological_site.mv_identification_and_registration AS
WITH site_alert AS (
    SELECT DISTINCT ON (t.parenttileid) t.parenttileid AS parenttileid,
           jsonb_build_object(
            'alert_entry_date', to_date(NULLIF(t.tiledata ->> '387adf52-1979-11f0-8713-0242ac170008', ''), 'YYYY-MM-DD'),
            'alert_subject', arches_util.i18n_text(t.tiledata -> '3c5afaa2-197a-11f0-8f07-0242ac170008'),
            'alert_details', arches_util.i18n_text(t.tiledata -> '7219d578-197a-11f0-8f07-0242ac170008'),
            'alert_branch_contact', arches_util.resource_id(t.tiledata -> '8511d07c-197a-11f0-8f07-0242ac170008'),
            'alert_entered_by', arches_util.resource_id(t.tiledata -> 'ec331cd0-1979-11f0-93f5-0242ac170008')
        ) AS obj
    FROM public.tiles t
    WHERE t.nodegroupid = '00e2b556-1979-11f0-8713-0242ac170008'::uuid
    ORDER BY t.parenttileid, COALESCE(t.sortorder, 2147483647), t.tileid
),
site_decision AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'decision_registration_status', arches_util.reference_flat(t.tiledata -> '4abdfeea-8d15-4ea6-94bd-d2385d47a5ac'),
            'decision_date', to_date(NULLIF(t.tiledata ->> 'f80f0c00-1977-11f0-8713-0242ac170008', ''), 'YYYY-MM-DD'),
            'decision_made_by', arches_util.resource_id(t.tiledata -> 'f80f0d4a-1977-11f0-8713-0242ac170008'),
            'recommended_by', arches_util.resource_id(t.tiledata -> 'f80f0f34-1977-11f0-8713-0242ac170008'),
            'recommendation_date', to_date(NULLIF(t.tiledata ->> 'f80f106a-1977-11f0-8713-0242ac170008', ''), 'YYYY-MM-DD'),
            'decision_description', arches_util.i18n_text(t.tiledata -> 'f80f115a-1977-11f0-8713-0242ac170008'),
            'site_decision', arches_util.reference_flat(t.tiledata -> 'f80f08ae-1977-11f0-8713-0242ac170008')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = 'f80f08ae-1977-11f0-8713-0242ac170008'::uuid
    GROUP BY t.parenttileid
),
site_names AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'name', arches_util.i18n_text(t.tiledata -> 'd60b1fa6-35f4-11f0-afbc-0242ac170008'),
            'assigned_or_reported_by', arches_util.resource_id(t.tiledata -> 'd60b2244-35f4-11f0-afbc-0242ac170008'),
            'name_type', arches_util.reference_flat(t.tiledata -> 'd60b242e-35f4-11f0-afbc-0242ac170008'),
            'name_remarks', arches_util.i18n_text(t.tiledata -> 'd60b2514-35f4-11f0-afbc-0242ac170008'),
            'assigned_or_reported_date', to_date(NULLIF(t.tiledata ->> 'd60b25fa-35f4-11f0-afbc-0242ac170008', ''), 'YYYY-MM-DD')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = 'd60b1b28-35f4-11f0-afbc-0242ac170008'::uuid
    GROUP BY t.parenttileid
),
authority AS (
    SELECT t.parenttileid AS parenttileid,
           jsonb_agg(jsonb_build_object(
            'authority_start_date', to_date(NULLIF(t.tiledata ->> '85dcf57e-1978-11f0-8713-0242ac170008', ''), 'YYYY-MM-DD'),
            'authority_end_date', to_date(NULLIF(t.tiledata ->> 'b36abfee-1978-11f0-8713-0242ac170008', ''), 'YYYY-MM-DD'),
            'legislative_act', arches_util.resource_id(t.tiledata -> '034d2e02-13f2-11f0-9ff8-0242ac170007'),
            'authority_protection_type', arches_util.reference_flat(t.tiledata -> '85d39c80-b92d-449f-834d-5d9b2ab3d1e8'),
            'reference_number', t.tiledata ->> '034d31b8-13f2-11f0-9ff8-0242ac170007',
            'authority_description', arches_util.i18n_text(t.tiledata -> '034d2ef2-13f2-11f0-9ff8-0242ac170007')
        ) ORDER BY COALESCE(t.sortorder, 2147483647), t.tileid) AS arr
    FROM public.tiles t
    WHERE t.nodegroupid = '034d1fac-13f2-11f0-9ff8-0242ac170007'::uuid
    GROUP BY t.parenttileid
),
identification_and_registration AS (
    SELECT DISTINCT ON (t.resourceinstanceid) t.resourceinstanceid AS resourceinstanceid,
           jsonb_build_object(
            'borden_number', t.tiledata ->> '7e15332c-1c54-11f0-b5bf-0242ac170007',
            'parcel_owner_type', arches_util.i18n_text(t.tiledata -> 'b442cce2-62c8-11f0-a80e-76ff5c50888d'),
            'borden_number_issuance_date', to_date(NULLIF(t.tiledata ->> 'bce307f4-62c8-11f0-a80e-76ff5c50888d', ''), 'YYYY-MM-DD'),
            'register_type', arches_util.reference_flat(t.tiledata -> '2255168c-1c55-11f0-9b6d-0242ac170007'),
            'parent_site', arches_util.resource_id(t.tiledata -> '7158cc42-1c55-11f0-9b6d-0242ac170007'),
            'site_alert', site_alert.obj,
            'site_decision', COALESCE(site_decision.arr, '[]'::jsonb),
            'site_names', COALESCE(site_names.arr, '[]'::jsonb),
            'authority', COALESCE(authority.arr, '[]'::jsonb)
        ) AS obj
    FROM public.tiles t
    LEFT JOIN site_alert site_alert ON site_alert.parenttileid = t.tileid
    LEFT JOIN site_decision site_decision ON site_decision.parenttileid = t.tileid
    LEFT JOIN site_names site_names ON site_names.parenttileid = t.tileid
    LEFT JOIN authority authority ON authority.parenttileid = t.tileid
    WHERE t.nodegroupid = '034d1c32-13f2-11f0-9ff8-0242ac170007'::uuid
    ORDER BY t.resourceinstanceid, COALESCE(t.sortorder, 2147483647), t.tileid
)
SELECT resourceinstanceid, obj AS identification_and_registration FROM identification_and_registration;

CREATE UNIQUE INDEX mv_identification_and_registration_pk ON archaeological_site.mv_identification_and_registration (resourceinstanceid);
