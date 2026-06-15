"""Urlconf documented by drf_spectacular -- the public OpenAPI surface.

Scaffolded once by the ``bootstrap_api`` management command and never
overwritten: this file is yours to edit. Add any hand-written endpoints
that belong in the published spec here, alongside the generated include.

The codegen pipeline generates the spec from this urlconf:

    python manage.py spectacular --urlconf bcap.urls_api_documented --file schema.yml
"""

from django.urls import include, path

urlpatterns = [
    path("", include("bcap.urls_api_generated")),
]
