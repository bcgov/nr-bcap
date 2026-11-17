"""WFS Intersects proxy: forwards browser requests to DataBC via the configured outbound proxy."""

import logging

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

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
    """POST a GeoJSON geometry; returns the WFS FeatureCollection of intersecting features."""

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
            logger.warning("WFS intersect: no usable geometry in request", exc_info=exc)
            raise ValidationError(
                {"geometry": "No usable geometry could be resolved from the request."}
            ) from exc
        except WfsError as exc:
            logger.error("WFS intersect: upstream query failed", exc_info=exc)
            raise ValidationError(
                {"detail": "The WFS query failed. Please try again later."}
            ) from exc

        return Response(result)
