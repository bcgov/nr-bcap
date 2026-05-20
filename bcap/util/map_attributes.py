"""Used by MVT Tiler for Search and Edit Views to return properties.
Used by single resource view for SimpleMapView under details.
"""

from django.db import connection

# graph_slug -> (geom node uuid, geojson node alias, map attribute aliases)
# Note: underlying SQL needs to change for site_visit to work.
GRAPH_CONFIG = {
    "archaeological_site": (
        "b18223c2-13ef-11f0-8695-0242ac170007",
        "site_boundary",
        ["authorities", "borden_number", "registration_status"],
    ),
    "site_visit": (
        "cf40edc0-13f0-11f0-9404-0242ac170007",
        "site_visit_location",
        [
            "site_visit_type",
            "first_date_of_site_visit",
            "last_date_of_site_visit",
            "is_site_visit_permitted",
        ],
    ),
}


def inject_map_attributes(response_data, resourceinstanceid, graph_slug):
    """Inject the configured attributes into each feature's properties of the
    graph's GeoJSON node so the map can drive styling without a second fetch.
    No-op if the slug isn't configured or the resource has no geometry row."""
    if not (entry := GRAPH_CONFIG.get(graph_slug)):
        return
    nodeid, alias, fields = entry
    sql = """
        SELECT key, value
        FROM jsonb_each_text(get_map_attribute_data(%s, %s))
        WHERE key = ANY(%s)
    """
    with connection.cursor() as cur:
        cur.execute(sql, [resourceinstanceid, nodeid, fields])
        attrs = dict(cur.fetchall())
    if not attrs:
        return
    node = response_data["aliased_data"][alias]["aliased_data"][alias]
    for f in node["node_value"]["features"]:
        f.setdefault("properties", {}).update(attrs)
