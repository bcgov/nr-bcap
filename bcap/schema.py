"""bcap re-exports of the arches_zod_validation OpenAPI schema helpers, kept as a
stable import path for the documented API views. The node-value builders (the
date override included) now live upstream in arches_zod_validation.schema."""

from arches_zod_validation.schema import (
    ArchesTileAutoSchema,
    AliasedNodeDataSerializer,
    resource_aliased_data_component,
    sort_generated_schema_properties,
)


def normalize_cookie_auth_name(result, generator, request, public):
    """Normalize cookieAuth to the production cookie name.

    SESSION_COOKIE_NAME is "bcap" + APP_SUFFIX so local dev instances don't
    share session cookies (e.g. "bcap_dev"). The committed schema.yml should
    always record the production name "bcap", not whatever suffix the
    developer has in their .env.
    """
    schemes = result.get("components", {}).get("securitySchemes", {})
    if "cookieAuth" in schemes:
        schemes["cookieAuth"]["name"] = "bcap"
    return result


__all__ = [
    "ArchesTileAutoSchema",
    "AliasedNodeDataSerializer",
    "normalize_cookie_auth_name",
    "resource_aliased_data_component",
    "sort_generated_schema_properties",
]
