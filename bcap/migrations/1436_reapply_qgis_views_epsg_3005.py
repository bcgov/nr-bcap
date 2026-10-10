"""Reapply the EPSG:3005 QGIS support views on existing databases.

Migration 855 had already run in deployed environments before its view SQL was
changed for #1739. Django does not rerun an applied migration when its source is
edited, so this forward migration carries the corrected definitions to upgrades.
"""

from django.db import migrations

DEPENDENCIES = [("bcap", "1435_permission_role_groups")]

VIEW_SQL = {
    "bc_labelled_site_visit_geometries": """DROP VIEW IF EXISTS public.bc_labelled_site_visit_geometries;
CREATE VIEW public.bc_labelled_site_visit_geometries as
(
select
    re.name ->> 'en'           as resource_name,
    g.id,
    g.tileid,
    g.resourceinstanceid,
    g.nodeid,
    g.featureid,
    ST_Transform(g.geom, 3005)::geometry(Geometry, 3005) as geom
from geojson_geometries g
         join (select re2.*
               from resource_instances re2
                        join graphs gr on re2.graphid = gr.graphid and
                                          gr.slug = 'site_visit') re
              on g.resourceinstanceid = re.resourceinstanceid);
""",
    "bc_labelled_geojson_geometries": """DROP VIEW IF EXISTS public.bc_labelled_geojson_geometries;
CREATE VIEW public.bc_labelled_geojson_geometries as
(
select
    re.name ->> 'en'           as resource_name,
    g.id,
    g.tileid,
    g.resourceinstanceid,
    g.nodeid,
    g.featureid,
    ST_Transform(g.geom, 3005)::geometry(Geometry, 3005) as geom
from geojson_geometries g
         join (select re2.*
               from resource_instances re2
                        join graphs gr on re2.graphid = gr.graphid and
                                          gr.slug in ('archaeological_site', 'site_visit', 'sandcastle')) re
              on g.resourceinstanceid = re.resourceinstanceid);
""",
    "bc_labelled_sandcastle_geometries": """DROP VIEW IF EXISTS public.bc_labelled_sandcastle_geometries;
CREATE VIEW public.bc_labelled_sandcastle_geometries as
(
select
    re.name ->> 'en'           as resource_name,
    g.id,
    g.tileid,
    g.resourceinstanceid,
    g.nodeid,
    g.featureid,
    ST_Transform(g.geom, 3005)::geometry(Geometry, 3005) as geom
from geojson_geometries g
         join (select re2.*
               from resource_instances re2
                        join graphs gr on re2.graphid = gr.graphid and
                                          gr.slug = 'sandcastle') re
              on g.resourceinstanceid = re.resourceinstanceid);
""",
    "bc_labelled_site_geometries": """DROP VIEW IF EXISTS public.bc_labelled_site_geometries;
CREATE VIEW public.bc_labelled_site_geometries as
(
select
    re.name ->> 'en'           as resource_name,
    g.id,
    g.tileid,
    g.resourceinstanceid,
    g.nodeid,
    g.featureid,
    ST_Transform(g.geom, 3005)::geometry(Geometry, 3005) as geom
from geojson_geometries g
         join (select re2.*
               from resource_instances re2
                        join graphs gr on re2.graphid = gr.graphid and
                                          gr.slug = 'archaeological_site') re
              on g.resourceinstanceid = re.resourceinstanceid);
""",
}

REVERSE_SQL = {
    "bc_labelled_site_visit_geometries": """DROP VIEW IF EXISTS public.bc_labelled_site_visit_geometries;
CREATE VIEW public.bc_labelled_site_visit_geometries as
(
select re.name ->> 'en' resource_name, g.*
from geojson_geometries g
         join (select re2.*
               from resource_instances re2
                        join graphs g on re2.graphid = g.graphid and
                                         g.slug = 'site_visit') re
              on g.resourceinstanceid = re.resourceinstanceid);
""",
    "bc_labelled_geojson_geometries": """DROP VIEW IF EXISTS public.bc_labelled_geojson_geometries;
CREATE VIEW public.bc_labelled_geojson_geometries as
(
select re.name ->> 'en' resource_name, g.*
from geojson_geometries g
         join (select re2.*
               from resource_instances re2
                        join graphs g on re2.graphid = g.graphid and
                                         g.slug in ('archaeological_site', 'site_visit', 'sandcastle')) re
              on g.resourceinstanceid = re.resourceinstanceid);
""",
    "bc_labelled_sandcastle_geometries": """DROP VIEW IF EXISTS public.bc_labelled_sandcastle_geometries;
CREATE VIEW public.bc_labelled_sandcastle_geometries as
(
select re.name ->> 'en' resource_name, g.*
from geojson_geometries g
         join (select re2.*
               from resource_instances re2
                        join graphs g on re2.graphid = g.graphid and
                                         g.slug = 'sandcastle') re
              on g.resourceinstanceid = re.resourceinstanceid);
""",
    "bc_labelled_site_geometries": """DROP VIEW IF EXISTS public.bc_labelled_site_geometries;
CREATE VIEW public.bc_labelled_site_geometries as
(
select re.name ->> 'en' resource_name, g.*
from geojson_geometries g
         join (select re2.*
               from resource_instances re2
                        join graphs g on re2.graphid = g.graphid and
                                         g.slug = 'archaeological_site') re
              on g.resourceinstanceid = re.resourceinstanceid);
""",
}


class Migration(migrations.Migration):
    dependencies = DEPENDENCIES
    operations = [
        migrations.RunSQL(VIEW_SQL[name], reverse_sql=REVERSE_SQL[name])
        for name in VIEW_SQL
    ]
