from django.db import migrations
from django_migrate_sql.config import SQLItem
from bcap.migrations.util.migration_util import format_sql

_APP = "bcap"

# ---------------------------------------------------------------------------
# site_visit dependency lists (used in multiple items)
# ---------------------------------------------------------------------------
_SV_BRANCHES = [
    ("bcap", "sv_mv_site_visit_location"),
    ("bcap", "sv_mv_identification"),
    ("bcap", "sv_mv_site_visit_details"),
    ("bcap", "sv_mv_archaeological_data"),
    ("bcap", "sv_mv_remarks_and_recommendations"),
    ("bcap", "sv_mv_ancestral_remains"),
    ("bcap", "sv_mv_related_documents"),
]
_SV_GEOMS = [
    ("bcap", "sv_mv_geom_site_visit_location"),
]
_SV_GRAIN_FLATS = [
    ("bcap", "sv_mv_site_visit_location_flat_v1"),
]

# ---------------------------------------------------------------------------
# archaeological_site dependency lists
# ---------------------------------------------------------------------------
_AS_BRANCHES = [
    ("bcap", "as_mv_site_boundary"),
    ("bcap", "as_mv_identification_and_registration"),
    ("bcap", "as_mv_site_location"),
    ("bcap", "as_mv_archaeological_data"),
    ("bcap", "as_mv_site_record_admin"),
    ("bcap", "as_mv_external_url"),
    ("bcap", "as_mv_ancestral_remains"),
    ("bcap", "as_mv_remarks_and_restricted_information"),
    ("bcap", "as_mv_related_documents"),
]
_AS_GEOMS = [
    ("bcap", "as_mv_geom_site_boundary"),
    ("bcap", "as_mv_geom_unprotected_areas"),
]
_AS_GRAIN_FLATS = [
    ("bcap", "as_mv_site_location_flat_v1"),
    ("bcap", "as_mv_bc_property_address_flat_v1"),
]

sql_items = [
    # -----------------------------------------------------------------------
    # Non-DataBC views / functions (unchanged)
    # -----------------------------------------------------------------------
    SQLItem(
        "bc_labelled_geojson_geometries",
        format_sql("sql/views/bc_labelled_geojson_geometries.sql"),
        reverse_sql="drop view bc_labelled_geojson_geometries;",
        replace=True,
    ),
    SQLItem(
        "bc_labelled_site_geometries",
        format_sql("sql/views/bc_labelled_site_geometries.sql"),
        reverse_sql="drop view bc_labelled_site_geometries;",
        replace=True,
    ),
    SQLItem(
        "bc_labelled_site_visit_geometries",
        format_sql("sql/views/bc_labelled_site_visit_geometries.sql"),
        reverse_sql="drop view bc_labelled_site_visit_geometries;",
        replace=True,
    ),
    SQLItem(
        "bc_labelled_sandcastle_geometries",
        format_sql("sql/views/bc_labelled_sandcastle_geometries.sql"),
        reverse_sql="drop view bc_labelled_sandcastle_geometries;",
        replace=True,
    ),
    SQLItem(
        "get_map_attribute_data",
        format_sql("sql/functions/get_map_attribute_data.sql"),
        reverse_sql="drop function get_map_attribute_data;",
        replace=True,
    ),
    # -----------------------------------------------------------------------
    # DataBC — shared arches_util schema (indexes + helper functions)
    # -----------------------------------------------------------------------
    SQLItem(
        "databc_arches_util",
        format_sql("sql/materialized_views/00_arches_util.sql"),
        reverse_sql=(
            "DROP SCHEMA IF EXISTS arches_util CASCADE;\n"
            "DROP INDEX IF EXISTS public.tiles_nodegroupid_idx;\n"
            "DROP INDEX IF EXISTS public.geojson_geometries_nodeid_idx;\n"
            "DROP INDEX IF EXISTS public.resource_instances_graphid_idx;"
        ),
    ),
    # -----------------------------------------------------------------------
    # DataBC — site_visit: branch materialized views
    # Each depends only on databc_arches_util.
    # -----------------------------------------------------------------------
    SQLItem(
        "sv_mv_site_visit_location",
        format_sql("sql/materialized_views/site_visit/mv_site_visit_location.sql"),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_site_visit_location CASCADE;",
        dependencies=[("bcap", "databc_arches_util")],
    ),
    SQLItem(
        "sv_mv_identification",
        format_sql("sql/materialized_views/site_visit/mv_identification.sql"),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_identification CASCADE;",
        dependencies=[("bcap", "databc_arches_util")],
    ),
    SQLItem(
        "sv_mv_site_visit_details",
        format_sql("sql/materialized_views/site_visit/mv_site_visit_details.sql"),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_site_visit_details CASCADE;",
        dependencies=[("bcap", "databc_arches_util")],
    ),
    SQLItem(
        "sv_mv_archaeological_data",
        format_sql("sql/materialized_views/site_visit/mv_archaeological_data.sql"),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_archaeological_data CASCADE;",
        dependencies=[("bcap", "databc_arches_util")],
    ),
    SQLItem(
        "sv_mv_remarks_and_recommendations",
        format_sql(
            "sql/materialized_views/site_visit/mv_remarks_and_recommendations.sql"
        ),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_remarks_and_recommendations CASCADE;",
        dependencies=[("bcap", "databc_arches_util")],
    ),
    SQLItem(
        "sv_mv_ancestral_remains",
        format_sql("sql/materialized_views/site_visit/mv_ancestral_remains.sql"),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_ancestral_remains CASCADE;",
        dependencies=[("bcap", "databc_arches_util")],
    ),
    SQLItem(
        "sv_mv_related_documents",
        format_sql("sql/materialized_views/site_visit/mv_related_documents.sql"),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_related_documents CASCADE;",
        dependencies=[("bcap", "databc_arches_util")],
    ),
    # DataBC — site_visit: geometry materialized view
    SQLItem(
        "sv_mv_geom_site_visit_location",
        format_sql("sql/materialized_views/site_visit/mv_geom_site_visit_location.sql"),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_geom_site_visit_location CASCADE;",
        dependencies=[("bcap", "databc_arches_util")],
    ),
    # DataBC — site_visit: final stack materialized view
    # Depends on every branch and every geometry matview.
    SQLItem(
        "sv_mv_resource_v1",
        format_sql("sql/materialized_views/site_visit/mv_resource_v1.sql"),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_resource_v1 CASCADE;",
        dependencies=_SV_BRANCHES + _SV_GEOMS,
    ),
    # DataBC — site_visit: stable wrapper view
    SQLItem(
        "sv_resource_view",
        format_sql("sql/materialized_views/site_visit/resource_view.sql"),
        reverse_sql="DROP VIEW IF EXISTS site_visit.resource;",
        replace=True,
        dependencies=[("bcap", "sv_mv_resource_v1")],
    ),
    # DataBC — site_visit: refresh procedure (stack)
    SQLItem(
        "sv_refresh_resource",
        format_sql("sql/materialized_views/site_visit/refresh_resource.sql"),
        reverse_sql="DROP PROCEDURE IF EXISTS site_visit.refresh_resource(boolean);",
        replace=True,
        dependencies=[("bcap", "sv_mv_resource_v1")],
    ),
    # DataBC — site_visit: flat materialized view
    SQLItem(
        "sv_mv_resource_flat_v1",
        format_sql("sql/materialized_views/site_visit/mv_resource_flat_v1.sql"),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_resource_flat_v1 CASCADE;",
        dependencies=[("bcap", "sv_mv_resource_v1")],
    ),
    # DataBC — site_visit: grain flat materialized view
    SQLItem(
        "sv_mv_site_visit_location_flat_v1",
        format_sql(
            "sql/materialized_views/site_visit/mv_site_visit_location_flat_v1.sql"
        ),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS site_visit.mv_site_visit_location_flat_v1 CASCADE;",
        dependencies=[("bcap", "sv_mv_resource_flat_v1")],
    ),
    # DataBC — site_visit: flat wrapper views
    SQLItem(
        "sv_flat_views",
        format_sql("sql/materialized_views/site_visit/flat_views.sql"),
        reverse_sql=(
            "DROP VIEW IF EXISTS site_visit.resource_flat;\n"
            "DROP VIEW IF EXISTS site_visit.site_visit_location_flat;"
        ),
        replace=True,
        dependencies=[("bcap", "sv_mv_resource_flat_v1")] + _SV_GRAIN_FLATS,
    ),
    # DataBC — site_visit: refresh procedure (flat)
    SQLItem(
        "sv_refresh_flat",
        format_sql("sql/materialized_views/site_visit/refresh_flat.sql"),
        reverse_sql="DROP PROCEDURE IF EXISTS site_visit.refresh_flat(boolean);",
        replace=True,
        dependencies=[("bcap", "sv_mv_resource_flat_v1")] + _SV_GRAIN_FLATS,
    ),
    # -----------------------------------------------------------------------
    # DataBC — archaeological_site: branch materialized views
    # -----------------------------------------------------------------------
    SQLItem(
        "as_mv_site_boundary",
        format_sql("sql/materialized_views/archaeological_site/mv_site_boundary.sql"),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_site_boundary CASCADE;",
        dependencies=[("bcap", "databc_arches_util")],
    ),
    SQLItem(
        "as_mv_identification_and_registration",
        format_sql(
            "sql/materialized_views/archaeological_site/mv_identification_and_registration.sql"
        ),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_identification_and_registration CASCADE;",
        dependencies=[("bcap", "databc_arches_util")],
    ),
    SQLItem(
        "as_mv_site_location",
        format_sql("sql/materialized_views/archaeological_site/mv_site_location.sql"),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_site_location CASCADE;",
        dependencies=[("bcap", "databc_arches_util")],
    ),
    SQLItem(
        "as_mv_archaeological_data",
        format_sql(
            "sql/materialized_views/archaeological_site/mv_archaeological_data.sql"
        ),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_archaeological_data CASCADE;",
        dependencies=[("bcap", "databc_arches_util")],
    ),
    SQLItem(
        "as_mv_site_record_admin",
        format_sql(
            "sql/materialized_views/archaeological_site/mv_site_record_admin.sql"
        ),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_site_record_admin CASCADE;",
        dependencies=[("bcap", "databc_arches_util")],
    ),
    SQLItem(
        "as_mv_external_url",
        format_sql("sql/materialized_views/archaeological_site/mv_external_url.sql"),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_external_url CASCADE;",
        dependencies=[("bcap", "databc_arches_util")],
    ),
    SQLItem(
        "as_mv_ancestral_remains",
        format_sql(
            "sql/materialized_views/archaeological_site/mv_ancestral_remains.sql"
        ),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_ancestral_remains CASCADE;",
        dependencies=[("bcap", "databc_arches_util")],
    ),
    SQLItem(
        "as_mv_remarks_and_restricted_information",
        format_sql(
            "sql/materialized_views/archaeological_site/mv_remarks_and_restricted_information.sql"
        ),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_remarks_and_restricted_information CASCADE;",
        dependencies=[("bcap", "databc_arches_util")],
    ),
    SQLItem(
        "as_mv_related_documents",
        format_sql(
            "sql/materialized_views/archaeological_site/mv_related_documents.sql"
        ),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_related_documents CASCADE;",
        dependencies=[("bcap", "databc_arches_util")],
    ),
    # DataBC — archaeological_site: geometry materialized views
    SQLItem(
        "as_mv_geom_site_boundary",
        format_sql(
            "sql/materialized_views/archaeological_site/mv_geom_site_boundary.sql"
        ),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_geom_site_boundary CASCADE;",
        dependencies=[("bcap", "databc_arches_util")],
    ),
    SQLItem(
        "as_mv_geom_unprotected_areas",
        format_sql(
            "sql/materialized_views/archaeological_site/mv_geom_unprotected_areas.sql"
        ),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_geom_unprotected_areas CASCADE;",
        dependencies=[("bcap", "databc_arches_util")],
    ),
    # DataBC — archaeological_site: final stack materialized view
    SQLItem(
        "as_mv_resource_v1",
        format_sql("sql/materialized_views/archaeological_site/mv_resource_v1.sql"),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_resource_v1 CASCADE;",
        dependencies=_AS_BRANCHES + _AS_GEOMS,
    ),
    # DataBC — archaeological_site: stable wrapper view
    SQLItem(
        "as_resource_view",
        format_sql("sql/materialized_views/archaeological_site/resource_view.sql"),
        reverse_sql="DROP VIEW IF EXISTS archaeological_site.resource;",
        replace=True,
        dependencies=[("bcap", "as_mv_resource_v1")],
    ),
    # DataBC — archaeological_site: refresh procedure (stack)
    SQLItem(
        "as_refresh_resource",
        format_sql("sql/materialized_views/archaeological_site/refresh_resource.sql"),
        reverse_sql="DROP PROCEDURE IF EXISTS archaeological_site.refresh_resource(boolean);",
        replace=True,
        dependencies=[("bcap", "as_mv_resource_v1")],
    ),
    # DataBC — archaeological_site: flat materialized view
    SQLItem(
        "as_mv_resource_flat_v1",
        format_sql(
            "sql/materialized_views/archaeological_site/mv_resource_flat_v1.sql"
        ),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_resource_flat_v1 CASCADE;",
        dependencies=[("bcap", "as_mv_resource_v1")],
    ),
    # DataBC — archaeological_site: grain flat materialized views
    SQLItem(
        "as_mv_site_location_flat_v1",
        format_sql(
            "sql/materialized_views/archaeological_site/mv_site_location_flat_v1.sql"
        ),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_site_location_flat_v1 CASCADE;",
        dependencies=[("bcap", "as_mv_resource_flat_v1")],
    ),
    SQLItem(
        "as_mv_bc_property_address_flat_v1",
        format_sql(
            "sql/materialized_views/archaeological_site/mv_bc_property_address_flat_v1.sql"
        ),
        reverse_sql="DROP MATERIALIZED VIEW IF EXISTS archaeological_site.mv_bc_property_address_flat_v1 CASCADE;",
        dependencies=[("bcap", "as_mv_resource_flat_v1")],
    ),
    # DataBC — archaeological_site: flat wrapper views
    SQLItem(
        "as_flat_views",
        format_sql("sql/materialized_views/archaeological_site/flat_views.sql"),
        reverse_sql=(
            "DROP VIEW IF EXISTS archaeological_site.resource_flat;\n"
            "DROP VIEW IF EXISTS archaeological_site.site_location_flat;\n"
            "DROP VIEW IF EXISTS archaeological_site.bc_property_address_flat;"
        ),
        replace=True,
        dependencies=[("bcap", "as_mv_resource_flat_v1")] + _AS_GRAIN_FLATS,
    ),
    # DataBC — archaeological_site: refresh procedure (flat)
    SQLItem(
        "as_refresh_flat",
        format_sql("sql/materialized_views/archaeological_site/refresh_flat.sql"),
        reverse_sql="DROP PROCEDURE IF EXISTS archaeological_site.refresh_flat(boolean);",
        replace=True,
        dependencies=[("bcap", "as_mv_resource_flat_v1")] + _AS_GRAIN_FLATS,
    ),
]
