from arches.app.models import models
from arches.app.datatypes.datatypes import DataTypeFactory
from django.contrib.gis.geos import Point
from arches.app.utils import geo_utils
import json
from bcap.util.bcap_aliases import (
    BCAPSiteAliases as site_aliases,
    GraphSlugs as slugs,
)
from django.conf import settings
from bcap.models.borden_number import BordenNumberCounter

import urllib3


# @todo - How do we handle multiple geometries?
class BordenNumberApi:
    _datatype_factory = None
    _url = "https://openmaps.gov.bc.ca/geo/pub/WHSE_ARCHAEOLOGY.RAAD_BORDENGRID/ows?service=WFS&request=GetFeature&outputFormat=json&version=2.3.0&typeNames=WHSE_ARCHAEOLOGY.RAAD_BORDENGRID&cql_filter=DWITHIN(GEOMETRY,POINT(%s%%20%s),1,meters)"

    geom_node = None

    def __init__(self):
        super().__init__()

    def _initialize_models(self):
        if not self.geom_node:
            self._datatype_factory = DataTypeFactory()
            graph = models.GraphModel.objects.filter(slug=slugs.HERITAGE_SITE).first()
            self.geom_node = models.Node.objects.filter(
                alias=site_aliases.SITE_BOUNDARY, graph=graph
            ).first()

    def _get_borden_grid(self, resourceinstanceid):
        tile = models.TileModel.objects.filter(
            resourceinstance_id=resourceinstanceid,
            nodegroup_id=self.geom_node.nodegroup_id,
        ).first()
        # print("Got tile: %s" % tile)
        datatype = self._datatype_factory.get_instance(self.geom_node.datatype)
        # geometry = datatype.get_display_value(tile, self.node)
        # print("Tile data: %s" % tile.data)
        geometry = tile.data[str(self.geom_node.nodeid)]
        return self._get_borden_grid_for_geometry(geometry)

    def _get_borden_grid_for_geometry(self, geometry):

        # print('Geometry: %s %s' % (geometry, type(geometry)))
        utils = geo_utils.GeoUtils()
        centroid = utils.get_centroid(geometry)
        # print('Centroid: %s %s' % (centroid, type(centroid)))

        pnt = Point(centroid["coordinates"][0], centroid["coordinates"][1], srid=4326)
        desired_srid = 3005
        pnt.transform(desired_srid)
        # print("Translated: %s" % pnt.ewkt)
        # print("Points: %s, %s" % (pnt.x, pnt.y))

        url = BordenNumberApi._url % (pnt.x, pnt.y)
        # print(url)
        if (
            hasattr(settings, "TILESERVER_OUTBOUND_PROXY")
            and settings.TILESERVER_OUTBOUND_PROXY
        ):
            req = urllib3.ProxyManager(settings.TILESERVER_OUTBOUND_PROXY)
        else:
            req = urllib3.PoolManager()

        response = req.request("GET", url)
        body = json.loads(response.data.decode())
        borden_grid = body["features"][0]["properties"]["BORDGRID"]

        return borden_grid

    def get_next_borden_number(self, resourceinstanceid=None, geometry=None):
        self._initialize_models()
        if resourceinstanceid:
            borden_grid = self._get_borden_grid(resourceinstanceid)
        elif geometry:
            borden_grid = self._get_borden_grid_for_geometry(geometry)
        else:
            raise Exception("Must provide either resourceinstanceid or geometry")

        return BordenNumberCounter.peek_next_borden_number(borden_grid)

    @classmethod
    def reserve_borden_number(cls, borden_grid):
        BordenNumberCounter.allocate_next_borden_number(borden_grid)
