"""
DataBC materialized view generation configuration.

Human-edited. Run `manage.py generate_databc_views` after any change here
or after graph model changes in the database.

Schema for each entry:
  arches_slug   - graph slug as stored in GraphModel.slug
  flat_grains   - list of nodegroup aliases that get their own grain flat table.
                  Must be cardinality-n nodegroups that are top-level (or whose
                  parent is also a grain). Review and update when the graph changes.
  view_names    - optional dict mapping nodegroup alias -> stable wrapper view name.
                  Use this when a nodegroup was renamed in the DB but the DataBC
                  API view (vw_*.sql) still references the old flat view name.
                  The MV is named after the alias; the wrapper view uses view_names.
"""

GRAPHS = {
    "sv": {
        "arches_slug": "site_visit",
        "flat_grains": ["site_visit_location"],
        "view_names": {},
    },
    "as": {
        "arches_slug": "archaeological_site",
        # heritage_site_location is the current DB alias; the API wrapper view
        # must remain site_location_flat to match vw_archaeological_site.sql.
        "flat_grains": ["heritage_site_location", "bc_property_address"],
        "view_names": {
            "heritage_site_location": "site_location",
        },
        # latest_site_decision: the most recent site_decision tile by decision_date.
        # Exposed as a jsonb single-element array for consistent downstream access.
        "extra_flat_select": [
            ("latest_site_decision", "latest_sd.latest_site_decision"),
        ],
        "extra_flat_joins": [
            "LEFT JOIN LATERAL (\n"
            "    SELECT (\n"
            "        SELECT jsonb_build_array(elem)\n"
            "        FROM jsonb_array_elements(\n"
            "            arches_util.as_array(\n"
            "                r.identification_and_registration -> 'site_decision'\n"
            "            )\n"
            "        ) AS elem\n"
            "        ORDER BY (elem ->> 'decision_date')::date DESC NULLS LAST\n"
            "        LIMIT 1\n"
            "    ) AS latest_site_decision\n"
            ") latest_sd ON true",
        ],
    },
    "per": {
        "arches_slug": "hca_permit",
        "flat_grains": [],
        "view_names": {},
    },
    "pub": {
        "arches_slug": "publication",
        "flat_grains": [],
        "view_names": {},
    },
    "rep": {
        "arches_slug": "repository",
        "flat_grains": [],
        "view_names": {},
    },
}
