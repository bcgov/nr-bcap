# This is used so we don't try to get the OpenAPI Spec of Arches serializers.
# The introspection will fail unless we override by hand-declaring their schema with @extend_schema(responses=...)
# So our views only consider bcap only for now.
# python manage.py spectacular --urlconf bcap.documented_api_urls --file schema.yml
from bcap.urls import documented_api_patterns as urlpatterns
