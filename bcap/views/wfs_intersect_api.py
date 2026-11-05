"""WFS Intersects view: proxy a DataBC (or compatible) WFS Intersects query
so the browser does not have to reach the external service directly and the
request travels through the application's outbound proxy when configured."""

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from bcap.permissions.route_guards import SubmitterOrInternal
from bcap.services.wfs.wfs_intersect_service import (
    MissingGeometryError,
    WfsError,
    WfsIntersectService,
)

_request_schema = inline_serializer(
    "WfsIntersectRequest",
    fields={
        "geometry": serializers.JSONField(
            help_text="GeoJSON FeatureCollection, Feature, or bare Geometry."
        ),
        "layer": serializers.CharField(
            help_text="WFS type name, e.g. 'WHSE_TANTALIS.TA_CROWN_TENURES_SVW'."
        ),
        "geometry_property": serializers.CharField(
            default="geometry",
            required=False,
            help_text="Geometry property name on the WFS layer (default: 'geometry').",
        ),
    },
)


@extend_schema(tags=["External: wfs"], request=_request_schema)
class WfsIntersectView(APIView):
    """POST a GeoJSON geometry and receive the WFS features that intersect it.

    The request is forwarded to the configured DataBC WFS endpoint via the
    application's outbound proxy (``TILESERVER_OUTBOUND_PROXY``) when set.
    Returns the raw GeoJSON FeatureCollection from the WFS server.
    """

    permission_classes = [SubmitterOrInternal]

    def post(self, request):
        geometry = request.data.get("geometry")
        layer = request.data.get("layer")
        geometry_property = request.data.get("geometry_property", "geometry")

        errors = {}
        if not geometry:
            errors["geometry"] = "Required."
        if not layer:
            errors["layer"] = "Required."
        if errors:
            raise ValidationError(errors)

        # Empty FeatureCollection — nothing to query, return early.
        if (
            isinstance(geometry, dict)
            and geometry.get("type") == "FeatureCollection"
            and not geometry.get("features")
        ):
            return Response({"type": "FeatureCollection", "features": []})

        try:
            result = WfsIntersectService.query(
                layer=layer,
                geometry=geometry,
                geometry_property=geometry_property,
            )
        except MissingGeometryError as exc:
            raise ValidationError({"geometry": str(exc)}) from exc
        except WfsError as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        return Response(result)
