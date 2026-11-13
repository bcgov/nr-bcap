"""WFS Intersects query service.

Queries a DataBC (or compatible) WFS endpoint for features that spatially
intersect a given geometry. The geometry can be supplied directly as a GeoJSON
dict or resolved from an Arches resource instance by node alias.
"""

import json
import logging

import urllib3
from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry

from arches.app.models import models as arches_models

logger = logging.getLogger(__name__)


class WfsError(Exception):
    """Raised when the WFS server returns an unexpected response."""


class MissingGeometryError(WfsError):
    """Raised when no geometry can be resolved for the query."""


class WfsIntersectService:
    """Query a WFS layer for features that intersect a geometry.

    Usage — from a raw GeoJSON geometry::

        result = WfsIntersectService.query(
            layer="WHSE_TANTALIS.TA_CROWN_TENURES_SVW",
            geometry=my_geojson_dict,
        )

    Usage — from an Arches resource instance::

        result = WfsIntersectService.query(
            layer="WHSE_TANTALIS.TA_CROWN_TENURES_SVW",
            resource_id="<uuid>",
            node_alias="site_boundary",
        )

    ``geometry`` may be a GeoJSON FeatureCollection, Feature, or bare Geometry
    object.  When a FeatureCollection is provided its member geometries are
    unioned before the WFS filter is built.

    Returns the parsed GeoJSON FeatureCollection dict returned by the server.
    """

    WFS_ENDPOINT = "https://openmaps.gov.bc.ca/geo/pub/wfs"

    @classmethod
    def _get_http(cls):
        proxy = getattr(settings, "TILESERVER_OUTBOUND_PROXY", None)
        if proxy:
            return urllib3.ProxyManager(proxy)
        return urllib3.PoolManager()

    @classmethod
    def _geometry_from_resource(cls, resource_id, node_alias):
        """Return the raw tile-data GeoJSON dict for *node_alias* on *resource_id*."""
        node = arches_models.Node.objects.filter(alias=node_alias).first()
        if not node:
            raise MissingGeometryError(f"No node found with alias '{node_alias}'")
        tile = arches_models.TileModel.objects.filter(
            resourceinstance_id=resource_id,
            nodegroup_id=node.nodegroup_id,
        ).first()
        if not tile:
            raise MissingGeometryError(
                f"No tile found for resource {resource_id} with node '{node_alias}'"
            )
        value = tile.data.get(str(node.nodeid))
        if not value:
            raise MissingGeometryError(
                f"Node '{node_alias}' on resource {resource_id} has no geometry value"
            )
        return value

    @staticmethod
    def _to_geos(geojson):
        """Convert a GeoJSON FeatureCollection, Feature, or bare Geometry to GEOS.

        For a FeatureCollection the member geometries are unioned so the filter
        covers the full extent of the resource boundary.
        """
        geojson_type = geojson.get("type") if isinstance(geojson, dict) else None

        if geojson_type == "FeatureCollection":
            features = geojson.get("features") or []
            geoms = [
                GEOSGeometry(json.dumps(f["geometry"]), srid=4326)
                for f in features
                if f.get("geometry")
            ]
            if not geoms:
                raise MissingGeometryError("FeatureCollection contains no geometries")
            result = geoms[0]
            for g in geoms[1:]:
                result = result.union(g)
            return result

        if geojson_type == "Feature":
            inner = geojson.get("geometry")
            if not inner:
                raise MissingGeometryError("Feature has no geometry")
            return GEOSGeometry(json.dumps(inner), srid=4326)

        # Bare geometry object
        return GEOSGeometry(json.dumps(geojson), srid=4326)

    @staticmethod
    def _ring_poslist(ring):
        """Render a GEOS LinearRing as a GML 3 posList string (lon lat ...)."""
        return " ".join(f"{x} {y}" for x, y in ring.coords)

    @classmethod
    def _polygon_rings_gml3(cls, poly):
        """Render the ring content of a GEOS Polygon as GML 3.1.1 (no wrapper tag)."""
        parts = [
            f"<gml:exterior><gml:LinearRing><gml:posList>"
            f"{cls._ring_poslist(poly.exterior_ring)}"
            f"</gml:posList></gml:LinearRing></gml:exterior>"
        ]
        for i in range(poly.num_interior_rings):
            parts.append(
                f"<gml:interior><gml:LinearRing><gml:posList>"
                f"{cls._ring_poslist(poly[i + 1])}"
                f"</gml:posList></gml:LinearRing></gml:interior>"
            )
        return "".join(parts)

    @classmethod
    def _to_gml3(cls, geos_geom):
        """Render a GEOS geometry as a GML 3.1.1 fragment for use in a WFS filter.

        DataBC's GeoServer WFS 1.1.0 uses EPSG:4326 with lon/lat axis order
        (matching its CQL BBOX behaviour — non-strict EPSG axis order).
        GML 3 syntax (gml:exterior / gml:posList) is required; WFS 1.1.0 does
        not reliably accept GML 2 (gml:outerBoundaryIs / gml:coordinates).
        """
        geom_type = geos_geom.geom_type

        if geom_type == "Polygon":
            return (
                f'<gml:Polygon srsName="EPSG:4326">'
                f"{cls._polygon_rings_gml3(geos_geom)}"
                f"</gml:Polygon>"
            )

        if geom_type == "MultiPolygon":
            members = "".join(
                f"<gml:polygonMember>"
                f"<gml:Polygon>{cls._polygon_rings_gml3(geos_geom[i])}</gml:Polygon>"
                f"</gml:polygonMember>"
                for i in range(len(geos_geom))
            )
            return f'<gml:MultiPolygon srsName="EPSG:4326">{members}</gml:MultiPolygon>'

        # For non-polygon types fall back to the convex hull polygon.
        return cls._to_gml3(geos_geom.convex_hull)

    @staticmethod
    def _build_filter_xml(geos_geom, geometry_property, layer):
        """Return a WFS 1.1.0 GetFeature POST body with an OGC Intersects filter."""
        gml = WfsIntersectService._to_gml3(geos_geom)
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<wfs:GetFeature service="WFS" version="1.1.0"\n'
            '  xmlns:wfs="http://www.opengis.net/wfs"\n'
            '  xmlns:ogc="http://www.opengis.net/ogc"\n'
            '  xmlns:gml="http://www.opengis.net/gml"\n'
            '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
            '  xsi:schemaLocation="http://www.opengis.net/wfs'
            ' http://schemas.opengis.net/wfs/1.1.0/wfs.xsd"\n'
            '  outputFormat="application/json">\n'
            f'  <wfs:Query typeName="pub:{layer}" srsName="EPSG:4326">\n'
            "    <ogc:Filter>\n"
            "      <ogc:Intersects>\n"
            f"        <ogc:PropertyName>{geometry_property}</ogc:PropertyName>\n"
            f"        {gml}\n"
            "      </ogc:Intersects>\n"
            "    </ogc:Filter>\n"
            "  </wfs:Query>\n"
            "</wfs:GetFeature>"
        )

    @classmethod
    def query(
        cls,
        layer,
        resource_id=None,
        node_alias=None,
        geometry=None,
        geometry_property="geometry",
    ):
        """Query *layer* for features that intersect the given geometry.

        Args:
            layer: WFS type name, e.g. ``"WHSE_TANTALIS.TA_CROWN_TENURES_SVW"``.
            resource_id: Arches resource instance UUID.  Requires *node_alias*.
            node_alias: Alias of the geometry node on the resource.
            geometry: GeoJSON dict (FeatureCollection, Feature, or bare Geometry).
            geometry_property: WFS geometry property name (default ``"geometry"``).

        Returns:
            Parsed GeoJSON FeatureCollection dict from the WFS server.

        Raises:
            ValueError: if *resource_id* is given without *node_alias*.
            MissingGeometryError: if no usable geometry can be resolved.
            WfsError: if the WFS server returns a non-200 response.
        """
        if resource_id is not None:
            if node_alias is None:
                raise ValueError("node_alias is required when resource_id is provided")
            geojson = cls._geometry_from_resource(resource_id, node_alias)
        elif geometry is not None:
            geojson = geometry
        else:
            raise MissingGeometryError(
                "Provide either resource_id + node_alias or a geometry dict"
            )

        geos_geom = cls._to_geos(geojson)
        body = cls._build_filter_xml(geos_geom, geometry_property, layer)

        logger.debug(
            "WFS Intersects query: layer=%s endpoint=%s", layer, cls.WFS_ENDPOINT
        )

        http = cls._get_http()
        response = http.request(
            "POST",
            cls.WFS_ENDPOINT,
            body=body.encode("utf-8"),
            headers={
                "Content-Type": "application/xml",
                "Accept": "application/json",
            },
        )

        if response.status != 200:
            snippet = response.data[:200].decode("utf-8", errors="replace")
            raise WfsError(
                f"WFS request for layer '{layer}' failed with HTTP {response.status}: {snippet}"
            )

        return json.loads(response.data.decode("utf-8"))
