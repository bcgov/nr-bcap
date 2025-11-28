from django.http import HttpResponse
from django.test import SimpleTestCase
from django.urls import path, resolve, reverse

import bcap.urls as bcap_urls


def protected_test_view(request):
    return HttpResponse("Protected test content")


urlpatterns = [
    path("test/protected", protected_test_view),
    *bcap_urls.urlpatterns,
]


class UrlPatternTests(SimpleTestCase):
    def test_bctileserver_url_resolves(self):
        url = reverse("bcap_tile_server", kwargs={"path": "some/tile/path"})
        resolver = resolve(url)
        assert resolver.view_name == "bcap_tile_server"

    def test_bctileserver_with_nested_path_resolves(self):
        url = reverse("bcap_tile_server", kwargs={"path": "layer/tiles/1/2/3.pbf"})
        resolver = resolve(url)
        assert resolver.view_name == "bcap_tile_server"
        assert resolver.kwargs["path"] == "layer/tiles/1/2/3.pbf"

    def test_borden_number_bare_resolves(self):
        url = reverse("borden_number_bare")
        resolver = resolve(url)
        assert resolver.view_name == "borden_number_bare"

    def test_borden_number_slash_resolves(self):
        url = reverse("borden_number_slash")
        resolver = resolve(url)
        assert resolver.view_name == "borden_number_slash"

    def test_borden_number_with_uuid_resolves(self):
        test_uuid = "12345678-1234-1234-1234-123456789abc"
        url = reverse("borden_number", kwargs={"resourceinstanceid": test_uuid})
        resolver = resolve(url)
        assert resolver.view_name == "borden_number"
        assert str(resolver.kwargs["resourceinstanceid"]) == test_uuid

    def test_controlled_list_hierarchy_url_resolves(self):
        test_uuid = "12345678-1234-1234-1234-123456789abc"
        url = reverse("controlled_list_hierarchy", kwargs={"list_item_id": test_uuid})
        resolver = resolve(url)
        assert resolver.view_name == "controlled_list_hierarchy"
        assert str(resolver.kwargs["list_item_id"]) == test_uuid

    def test_legislative_act_url_resolves(self):
        test_uuid = "12345678-1234-1234-1234-123456789abc"
        url = reverse("legislative_act", kwargs={"act_id": test_uuid})
        resolver = resolve(url)
        assert resolver.view_name == "legislative_act"
        assert str(resolver.kwargs["act_id"]) == test_uuid

    def test_localfiles_url_resolves(self):
        test_uuid = "12345678-1234-1234-1234-123456789abc"
        url = reverse("localfiles", kwargs={"fileid": test_uuid})
        resolver = resolve(url)
        assert resolver.view_name == "localfiles"
        assert str(resolver.kwargs["fileid"]) == test_uuid

    def test_mvt_url_resolves(self):
        test_nodeid = "12345678-1234-1234-1234-123456789abc"
        url = reverse(
            "mvt", kwargs={"nodeid": test_nodeid, "zoom": "10", "x": "512", "y": "256"}
        )
        resolver = resolve(url)
        assert resolver.view_name == "mvt"
        assert resolver.kwargs["nodeid"] == test_nodeid
        assert resolver.kwargs["zoom"] == "10"
        assert resolver.kwargs["x"] == "512"
        assert resolver.kwargs["y"] == "256"

    def test_mvt_url_with_placeholders_resolves(self):
        test_nodeid = "12345678-1234-1234-1234-123456789abc"
        url = f"/bcap/mvt/{test_nodeid}/{{z}}/{{x}}/{{y}}.pbf"
        resolver = resolve(url)
        assert resolver.view_name == "mvt"
        assert resolver.kwargs["nodeid"] == test_nodeid
        assert resolver.kwargs["zoom"] == "{z}"
        assert resolver.kwargs["x"] == "{x}"
        assert resolver.kwargs["y"] == "{y}"

    def test_mvt_url_with_zero_coordinates_resolves(self):
        test_nodeid = "12345678-1234-1234-1234-123456789abc"
        url = reverse(
            "mvt", kwargs={"nodeid": test_nodeid, "zoom": "0", "x": "0", "y": "0"}
        )
        resolver = resolve(url)
        assert resolver.view_name == "mvt"
        assert resolver.kwargs["zoom"] == "0"
        assert resolver.kwargs["x"] == "0"
        assert resolver.kwargs["y"] == "0"

    def test_related_site_resources_with_pk_resolves(self):
        test_uuid = "12345678-1234-1234-1234-123456789abc"
        url = reverse(
            "api-related-site-resources",
            kwargs={"graph": "site_visit", "pk": test_uuid},
        )
        resolver = resolve(url)
        assert resolver.view_name == "api-related-site-resources"
        assert resolver.kwargs["graph"] == "site_visit"
        assert str(resolver.kwargs["pk"]) == test_uuid

    def test_related_sites_resources_without_pk_resolves(self):
        url = reverse("api-related-sites-resources", kwargs={"graph": "site_visit"})
        resolver = resolve(url)
        assert resolver.view_name == "api-related-sites-resources"
        assert resolver.kwargs["graph"] == "site_visit"

    def test_related_sites_resources_with_different_graph_slug(self):
        url = reverse(
            "api-related-sites-resources", kwargs={"graph": "archaeological_site"}
        )
        resolver = resolve(url)
        assert resolver.view_name == "api-related-sites-resources"
        assert resolver.kwargs["graph"] == "archaeological_site"

    def test_resource_report_url_resolves(self):
        test_uuid = "12345678-1234-1234-1234-123456789abc"
        url = reverse("resource_report", kwargs={"resourceid": test_uuid})
        resolver = resolve(url)
        assert resolver.view_name == "resource_report"
        assert str(resolver.kwargs["resourceid"]) == test_uuid

    def test_user_profile_url_resolves(self):
        url = reverse("user_profile")
        resolver = resolve(url)
        assert resolver.view_name == "user_profile"


class UrlReverseTests(SimpleTestCase):
    def test_bctileserver_reverse(self):
        url = reverse("bcap_tile_server", kwargs={"path": "test/path"})
        assert url == "/bcap/bctileserver/test/path"

    def test_borden_number_bare_reverse(self):
        url = reverse("borden_number_bare")
        assert url == "/bcap/borden_number"

    def test_borden_number_reverse(self):
        test_uuid = "12345678-1234-1234-1234-123456789abc"
        url = reverse("borden_number", kwargs={"resourceinstanceid": test_uuid})
        assert url == f"/bcap/borden_number/{test_uuid}"

    def test_borden_number_slash_reverse(self):
        url = reverse("borden_number_slash")
        assert url == "/bcap/borden_number/"

    def test_controlled_list_hierarchy_reverse(self):
        test_uuid = "12345678-1234-1234-1234-123456789abc"
        url = reverse("controlled_list_hierarchy", kwargs={"list_item_id": test_uuid})
        assert url == f"/bcap/api/hierarchy/{test_uuid}/"

    def test_legislative_act_reverse(self):
        test_uuid = "12345678-1234-1234-1234-123456789abc"
        url = reverse("legislative_act", kwargs={"act_id": test_uuid})
        assert url == f"/bcap/legislative_act/{test_uuid}"

    def test_localfiles_reverse(self):
        test_uuid = "12345678-1234-1234-1234-123456789abc"
        url = reverse("localfiles", kwargs={"fileid": test_uuid})
        assert url == f"/bcap/localfiles/{test_uuid}"

    def test_mvt_reverse(self):
        test_nodeid = "12345678-1234-1234-1234-123456789abc"
        url = reverse(
            "mvt", kwargs={"nodeid": test_nodeid, "zoom": "10", "x": "512", "y": "256"}
        )
        assert url == f"/bcap/mvt/{test_nodeid}/10/512/256.pbf"

    def test_related_site_resources_reverse(self):
        test_uuid = "12345678-1234-1234-1234-123456789abc"
        url = reverse(
            "api-related-site-resources",
            kwargs={"graph": "site_visit", "pk": test_uuid},
        )
        assert url == f"/bcap/api/arch_site_related_resources/site_visit/{test_uuid}"

    def test_related_sites_resources_reverse(self):
        url = reverse("api-related-sites-resources", kwargs={"graph": "site_visit"})
        assert url == "/bcap/api/arch_site_related_resources/site_visit"

    def test_resource_report_reverse(self):
        test_uuid = "12345678-1234-1234-1234-123456789abc"
        url = reverse("resource_report", kwargs={"resourceid": test_uuid})
        assert url == f"/bcap/report/{test_uuid}"

    def test_user_profile_reverse(self):
        url = reverse("user_profile")
        assert "/user_profile" in url


class UrlEdgeCaseTests(SimpleTestCase):
    def test_mvt_with_large_coordinates(self):
        test_nodeid = "12345678-1234-1234-1234-123456789abc"
        url = reverse(
            "mvt",
            kwargs={
                "nodeid": test_nodeid,
                "zoom": "22",
                "x": "4194303",
                "y": "4194303",
            },
        )
        resolver = resolve(url)
        assert resolver.view_name == "mvt"
        assert resolver.kwargs["x"] == "4194303"
        assert resolver.kwargs["y"] == "4194303"

    def test_bctileserver_with_minimal_path(self):
        url = reverse("bcap_tile_server", kwargs={"path": "a"})
        resolver = resolve(url)
        assert resolver.view_name == "bcap_tile_server"

    def test_bctileserver_with_special_characters_in_path(self):
        url = reverse(
            "bcap_tile_server", kwargs={"path": "layer/name-with_special.chars"}
        )
        resolver = resolve(url)
        assert resolver.view_name == "bcap_tile_server"
        assert resolver.kwargs["path"] == "layer/name-with_special.chars"

    def test_uuid_lowercase_resolves(self):
        lowercase_uuid = "12345678-1234-1234-1234-123456789abc"
        url = reverse("borden_number", kwargs={"resourceinstanceid": lowercase_uuid})
        resolver = resolve(url)
        assert resolver.view_name == "borden_number"
        assert str(resolver.kwargs["resourceinstanceid"]) == lowercase_uuid

    def test_graph_slug_with_underscores(self):
        url = reverse(
            "api-related-sites-resources", kwargs={"graph": "archaeological_site"}
        )
        resolver = resolve(url)
        assert resolver.kwargs["graph"] == "archaeological_site"

    def test_graph_slug_with_hyphens(self):
        url = reverse("api-related-sites-resources", kwargs={"graph": "site-visit"})
        resolver = resolve(url)
        assert resolver.kwargs["graph"] == "site-visit"
