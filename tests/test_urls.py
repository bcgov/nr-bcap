from django.http import HttpResponse
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.urls import path, resolve, reverse

import bcap.urls as bcap_urls
from bcap.views.api import BCAPResourceDetailView

UUID = "12345678-1234-1234-1234-123456789abc"

# name, reverse kwargs, expected url
ROUTES = [
    (
        "bcap_tile_server",
        {"path": "layer/tiles/1/2/3.pbf"},
        "/bcap/bctileserver/layer/tiles/1/2/3.pbf",
    ),
    ("borden_number", {"resourceinstanceid": UUID}, f"/bcap/borden_number/{UUID}"),
    (
        "controlled_list_hierarchy",
        {"list_item_id": UUID},
        f"/bcap/api/hierarchy/{UUID}/",
    ),
    ("legislative_act", {"act_id": UUID}, f"/bcap/legislative_act/{UUID}"),
    ("files", {"fileid": UUID}, f"/bcap/files/{UUID}"),
    (
        "mvt",
        {"nodeid": UUID, "zoom": "10", "x": "512", "y": "256"},
        f"/bcap/mvt/{UUID}/10/512/256.pbf",
    ),
    (
        "api-related-site-resources",
        {"graph": "site_visit", "pk": UUID},
        f"/bcap/api/arch_site_related_resources/site_visit/{UUID}",
    ),
    (
        "api-related-sites-resources",
        {"graph": "site_visit"},
        "/bcap/api/arch_site_related_resources/site_visit",
    ),
    ("resource_report", {"resourceid": UUID}, f"/bcap/report/{UUID}"),
]


def protected_test_view(request):
    return HttpResponse("Protected test content")


urlpatterns = [
    path("test/protected", protected_test_view),
    *bcap_urls.urlpatterns,
]


class UrlRoundTripTests(SimpleTestCase):
    def test_routes_reverse_and_resolve(self):
        for name, kwargs, expected in ROUTES:
            with self.subTest(name):
                self.assertEqual(reverse(name, kwargs=kwargs), expected)
                resolver = resolve(expected)
                self.assertEqual(resolver.view_name, name)
                self.assertEqual(
                    {k: str(v) for k, v in resolver.kwargs.items()},
                    {k: str(v) for k, v in kwargs.items()},
                )

    def test_mvt_url_with_placeholders_resolves(self):
        resolver = resolve(f"/bcap/mvt/{UUID}/{{z}}/{{x}}/{{y}}.pbf")
        self.assertEqual(resolver.view_name, "mvt")
        self.assertEqual(resolver.kwargs["zoom"], "{z}")
        self.assertEqual(resolver.kwargs["x"], "{x}")
        self.assertEqual(resolver.kwargs["y"], "{y}")

    def test_api_resource_url_resolves_to_bcap_view(self):
        # arches_querysets also defines a resource-detail route at the same
        # path; the bcap entry must precede that include in urls.py or the
        # MVT-attribute injection silently stops working. Asserting the view
        # class (not just the URL name) is what catches that regression.
        url = reverse(
            "api-resource", kwargs={"graph": "archaeological_site", "pk": UUID}
        )
        self.assertEqual(url, f"/bcap/api/resource/archaeological_site/{UUID}")
        resolver = resolve(url)
        self.assertIs(resolver.func.view_class, BCAPResourceDetailView)
        self.assertEqual(resolver.kwargs["graph"], "archaeological_site")
        self.assertEqual(str(resolver.kwargs["pk"]), UUID)


class ArchesUrlsTemplateTests(SimpleTestCase):
    def test_arches_urls_template_renders(self):
        out = render_to_string("arches_urls.htm")
        assert "api_user_profile" in out
