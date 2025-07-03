from django.urls import include, path
from django.http import HttpResponse
import bcap.urls as bcap_urls  # Import your real urls


def protected_test_view(request):
    return HttpResponse("Protected test content")


urlpatterns = [
    # Add your test-specific route
    path("test/protected", protected_test_view),
    # Include the full app URL configuration
    *bcap_urls.urlpatterns,
]
