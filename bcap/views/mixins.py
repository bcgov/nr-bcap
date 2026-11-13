"""Reusable view mixins for BCAP."""

import uuid as _uuid


class SanitizeFeatureIdsMixin:
    """Replace non-UUID feature IDs in GeoJSON before returning to the client.

    WFS services (DataBC, ArcGIS, etc.) emit text feature IDs such as::

        WHSE_CADASTRE.PMBC_PARCEL_FABRIC_POLY_SVW.fid--370c99b_1a1acdb8d04_7e26

    Arches requires UUID feature IDs. Any non-conforming ``id`` value on a
    GeoJSON feature is replaced with a freshly generated UUID.

    Usage::

        class MyView(SanitizeFeatureIdsMixin, APIView):
            def post(self, request):
                result = some_service.query(...)
                self.sanitize_geojson_feature_ids(result)
                return Response(result)
    """

    @classmethod
    def sanitize_all_feature_ids(cls, data) -> None:
        """Recursively walk *data* (dict or list) and sanitize every GeoJSON
        feature ID found anywhere in the structure.

        Use this on ``request.data`` before persisting, so that non-UUID IDs
        from external WFS sources are replaced with valid UUIDs without having
        to know the exact path to each geometry node.
        """
        if isinstance(data, dict):
            geojson_type = data.get("type")
            if geojson_type in ("FeatureCollection", "Feature"):
                cls.sanitize_geojson_feature_ids(data)
            else:
                for value in data.values():
                    cls.sanitize_all_feature_ids(value)
        elif isinstance(data, list):
            for item in data:
                cls.sanitize_all_feature_ids(item)

    @staticmethod
    def sanitize_geojson_feature_ids(geojson: dict) -> dict:
        """Replace non-UUID ``id`` values in a single GeoJSON dict in-place.

        Handles ``FeatureCollection`` and bare ``Feature`` dicts.  The dict is
        mutated in place and also returned for convenience.
        """
        if not isinstance(geojson, dict):
            return geojson

        geojson_type = geojson.get("type")

        if geojson_type == "FeatureCollection":
            for feature in geojson.get("features") or []:
                SanitizeFeatureIdsMixin._sanitize_feature_id(feature)
        elif geojson_type == "Feature":
            SanitizeFeatureIdsMixin._sanitize_feature_id(geojson)

        return geojson

    @staticmethod
    def _sanitize_feature_id(feature: dict) -> None:
        fid = feature.get("id")
        if fid is None:
            return
        try:
            _uuid.UUID(str(fid))
        except ValueError:
            feature["id"] = str(_uuid.uuid4())
