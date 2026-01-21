create or replace view public.bc_labelled_site_geometries as
(
select re.name ->> 'en' resource_name, g.*
from geojson_geometries g
         join (select re2.*
               from resource_instances re2
                        join graphs g on re2.graphid = g.graphid and
                                         g.slug = 'archaeological_site') re
              on g.resourceinstanceid = re.resourceinstanceid);
