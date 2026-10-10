create or replace view public.bc_labelled_geojson_geometries as
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
