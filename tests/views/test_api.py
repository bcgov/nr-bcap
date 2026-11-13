import json
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import Group
from django.core.exceptions import FieldError
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from rest_framework.exceptions import ValidationError

from arches_querysets.rest_framework.generic_views import ArchesResourceDetailView

from bcap.permissions.groups import Groups
from bcap.util.borden_number_api import BordenGridServiceError, MissingGeometryError
from bcap.views.api import (
    BCAPResourceDetailView,
    BordenNumber,
    ControlledListHierarchy,
    LegislativeAct,
    RegisterType,
    RelatedSiteVisits,
)
from tests.views.helpers import AuthTestHelper


@override_settings(ROOT_URLCONF="tests.test_urls")
class BordenNumberImplTests(TestCase):
    """Unit tests for BordenNumberBase._get_impl error handling."""

    def setUp(self):
        super().setUp()
        self.view = BordenNumber()
        self.factory = RequestFactory()

    def _call_get_impl(self, exc):
        self.view.api = MagicMock()
        self.view.api.get_next_borden_number.side_effect = exc
        return self.view._get_impl(self.factory.get("/"))

    def test_borden_grid_service_error_returns_error_json_with_message(self):
        exc = BordenGridServiceError(
            "The Borden Grid lookup service returned an unexpected error (HTTP 503). "
            "Please try again or contact system support."
        )
        with self.assertLogs("bcap.views.api", level="ERROR"):
            body = json.loads(self._call_get_impl(exc).content)
        self.assertEqual(body["status"], "error")
        self.assertIn("503", body["message"])

    def test_borden_grid_service_error_is_logged(self):
        exc = BordenGridServiceError("upstream failure")
        with self.assertLogs("bcap.views.api", level="ERROR") as cm:
            self._call_get_impl(exc)
        self.assertTrue(any("upstream failure" in line for line in cm.output))

    def test_missing_geometry_error_returns_error_json_with_message(self):
        exc = MissingGeometryError(
            "No Borden Grid was found for the provided location. "
            "Please ensure the site boundary is within British Columbia."
        )
        body = json.loads(self._call_get_impl(exc).content)
        self.assertEqual(body["status"], "error")
        self.assertIn("British Columbia", body["message"])

    def test_unexpected_exception_returns_generic_error_json(self):
        with self.assertLogs("bcap.views.api", level="ERROR"):
            body = json.loads(self._call_get_impl(RuntimeError("boom")).content)
        self.assertEqual(body["status"], "error")
        self.assertIn("unexpected error", body["message"])


@override_settings(ROOT_URLCONF="tests.test_urls")
class BordenNumberExternalViewTests(AuthTestHelper, TestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("borden-number-external")
        self.post_data = {
            "site_boundary": json.dumps(
                {"type": "Point", "coordinates": [-123.2, 49.2]}
            ),
            "reserve_borden_number": "false",
        }

    def test_post_requires_bearer_token(self):
        resp = self.client.post(self.url, data=self.post_data)

        # django-oauth-toolkit ProtectedResourceView returns 403 for missing/invalid token
        # django-oauth-toolkit only runs if the auth_exempt_pages is enabled for this route in settings.py
        # Otherwise this is a 302 to homepage.
        self.assertIn(resp.status_code, [302, 403])

    @patch("bcap.views.api.BordenNumberBase._post_impl")
    def test_post_with_valid_token_allows_request(self, post_impl_patch):
        # If auth passes, we should reach _post_impl (avoid real impl)
        post_impl_patch.return_value = HttpResponse(
            json.dumps({"status": "success", "borden_number": "EhRa-001"}),
            content_type="application/json",
        )

        resp = self.client.post(
            self.url,
            data=self.post_data,
            HTTP_AUTHORIZATION=f"Bearer {self.access_token.token}",
        )

        self.assertEqual(resp.status_code, 200)
        post_impl_patch.assert_called_once()


@override_settings(ROOT_URLCONF="tests.test_urls")
class MVTAccessTests(AuthTestHelper, TestCase):
    """The tile route is staff only. Without the gate an applicant's tile is
    narrowed by the search index alone, so a stale index leaks site geometry."""

    def setUp(self):
        super().setUp()
        self.url = reverse(
            "mvt",
            kwargs={
                "nodeid": "22222222-2222-2222-2222-222222222222",
                "zoom": "10",
                "x": "512",
                "y": "256",
            },
        )

    def test_applicant_is_refused(self):
        self.idir_login_simulate(login_source="BCEID")

        self.assertEqual(self.client.get(self.url).status_code, 403)

    @patch("bcap.views.api.MVTTiler")
    def test_internal_user_reaches_the_tiler(self, tiler):
        tiler.return_value.createTile.return_value = b"tile"
        self.user.groups.add(Group.objects.get(name=Groups.ARCHAEOLOGY_BRANCH))
        self.idir_login_simulate()

        self.assertEqual(self.client.get(self.url).status_code, 200)


# ---------------------------------------------------------------------------
# BordenNumberBase._post_impl
# ---------------------------------------------------------------------------


class BordenNumberPostImplTests(SimpleTestCase):
    def setUp(self):
        self.view = BordenNumber()
        self.view.api = MagicMock()
        self.view.api.get_next_borden_number.return_value = "EhRa-001"
        self.view.api.reserve_borden_number.return_value = "EhRa"
        self.factory = RequestFactory()

    def _post(self, reserve="false"):
        data = {
            "site_boundary": json.dumps(
                {"type": "Point", "coordinates": [-123.1, 49.2]}
            ),
        }
        if reserve != "_absent_":
            data["reserve_borden_number"] = reserve
        return self.view._post_impl(self.factory.post("/", data=data))

    def test_returns_borden_number_in_response(self):
        response = self._post()
        body = json.loads(response.content)
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["borden_number"], "EhRa-001")

    def test_reserve_true_calls_reserve_borden_number(self):
        self._post(reserve="true")
        self.view.api.reserve_borden_number.assert_called_once()

    def test_reserve_false_does_not_call_reserve(self):
        self._post(reserve="false")
        self.view.api.reserve_borden_number.assert_not_called()

    def test_missing_reserve_flag_does_not_call_reserve(self):
        self._post(reserve="_absent_")
        self.view.api.reserve_borden_number.assert_not_called()

    def test_reserve_strips_suffix_before_reserving(self):
        """re.sub('-.*', '', 'EhRa-001') → 'EhRa' passed to reserve_borden_number."""
        self._post(reserve="true")
        self.view.api.reserve_borden_number.assert_called_once_with("EhRa")


# ---------------------------------------------------------------------------
# ControlledListHierarchy.get
# ---------------------------------------------------------------------------


class ControlledListHierarchyTests(SimpleTestCase):
    def setUp(self):
        self.view = ControlledListHierarchy()
        self.factory = RequestFactory()

    def _get(self, item_id="some-uuid"):
        request = self.factory.get(f"/bcap/api/hierarchy/{item_id}/")
        return self.view.get(request, list_item_id=item_id)

    def test_returns_empty_labels_when_item_not_found(self):
        class FakeDoesNotExist(Exception):
            pass

        mock_li = MagicMock()
        mock_li.DoesNotExist = FakeDoesNotExist
        mock_li.objects.get.side_effect = FakeDoesNotExist

        with patch("bcap.views.api.ListItem", mock_li):
            response = self._get()

        body = json.loads(response.content)
        self.assertEqual(body["labels"], [])

    def test_returns_single_label_for_root_item(self):
        root = MagicMock()
        root.parent = None

        mock_lv = MagicMock()
        mock_lv.objects.filter.return_value.values_list.return_value.first.return_value = (
            "Root Label"
        )

        with (
            patch("bcap.views.api.ListItem") as mock_li,
            patch("bcap.views.api.ListItemValue", mock_lv),
        ):
            mock_li.DoesNotExist = Exception
            mock_li.objects.get.return_value = root
            response = self._get()

        body = json.loads(response.content)
        self.assertEqual(body["labels"], ["Root Label"])

    def test_labels_ordered_root_to_leaf(self):
        root = MagicMock()
        root.parent = None
        child = MagicMock()
        child.parent = root

        label_map = {id(root): "Root Label", id(child): "Child Label"}

        def filter_side(*_, list_item, **__):
            mock_qs = MagicMock()
            mock_qs.values_list.return_value.first.return_value = label_map.get(
                id(list_item)
            )
            return mock_qs

        with (
            patch("bcap.views.api.ListItem") as mock_li,
            patch("bcap.views.api.ListItemValue") as mock_lv,
        ):
            mock_li.DoesNotExist = Exception
            mock_li.objects.get.return_value = child
            mock_lv.objects.filter.side_effect = filter_side
            response = self._get()

        body = json.loads(response.content)
        self.assertEqual(body["labels"], ["Root Label", "Child Label"])


# ---------------------------------------------------------------------------
# LegislativeAct.get
# ---------------------------------------------------------------------------


class LegislativeActTests(SimpleTestCase):
    def setUp(self):
        self.view = LegislativeAct()
        self.factory = RequestFactory()

    def test_returns_serialized_act(self):
        with (
            patch("bcap.views.api.LegislativeActDataProxy") as mock_proxy_cls,
            patch("bcap.views.api.JSONSerializer") as mock_serializer_cls,
        ):
            mock_proxy = mock_proxy_cls.return_value
            mock_proxy.get_authorities.return_value = {"act": "data"}
            mock_serializer_cls.return_value.serializeToPython.return_value = {
                "act": "data"
            }

            response = self.view.get(self.factory.get("/"), act_id="abc-123")

        body = json.loads(response.content)
        self.assertEqual(body, {"act": "data"})

    def test_calls_get_authorities_with_act_id(self):
        with (
            patch("bcap.views.api.LegislativeActDataProxy") as mock_proxy_cls,
            patch("bcap.views.api.JSONSerializer") as mock_serializer_cls,
        ):
            mock_proxy = mock_proxy_cls.return_value
            mock_proxy.get_authorities.return_value = {}
            mock_serializer_cls.return_value.serializeToPython.return_value = {}
            self.view.get(self.factory.get("/"), act_id="act-999")

        mock_proxy.get_authorities.assert_called_once_with("act-999")


# ---------------------------------------------------------------------------
# RegisterType.get
# ---------------------------------------------------------------------------


class RegisterTypeTests(SimpleTestCase):
    def setUp(self):
        self.view = RegisterType()
        self.view.api = MagicMock()
        self.factory = RequestFactory()

    def test_successful_calculation_returns_result(self):
        self.view.api.calculate.return_value = {"register_type": "cultural"}
        response = self.view.get(self.factory.get("/"), resourceinstanceid="some-uuid")
        body = json.loads(response.content)
        self.assertEqual(body["register_type"], "cultural")

    def test_exception_returns_error_json(self):
        self.view.api.calculate.side_effect = RuntimeError("boom")
        with self.assertLogs("bcap.views.api", level="ERROR"):
            response = self.view.get(
                self.factory.get("/"), resourceinstanceid="some-uuid"
            )
        body = json.loads(response.content)
        self.assertEqual(body["status"], "error")
        self.assertIn("unexpected error", body["message"])

    def test_exception_is_logged(self):
        self.view.api.calculate.side_effect = ValueError("bad input")
        with self.assertLogs("bcap.views.api", level="ERROR"):
            self.view.get(self.factory.get("/"), resourceinstanceid="some-uuid")


# ---------------------------------------------------------------------------
# BCAPResourceDetailView.retrieve
# ---------------------------------------------------------------------------


class BCAPResourceDetailViewTests(SimpleTestCase):
    def setUp(self):
        self.view = BCAPResourceDetailView()
        self.factory = RequestFactory()

    def test_inject_map_attributes_called_with_pk_and_graph(self):
        mock_response = MagicMock()
        mock_response.data = {"type": "FeatureCollection"}
        request = self.factory.get("/")

        with (
            patch.object(
                ArchesResourceDetailView, "retrieve", return_value=mock_response
            ),
            patch("bcap.views.api.inject_map_attributes") as mock_inject,
        ):
            self.view.retrieve(request, pk="some-uuid", graph="archaeological_site")

        mock_inject.assert_called_once_with(
            mock_response.data, "some-uuid", "archaeological_site"
        )

    def test_returns_response_from_super(self):
        mock_response = MagicMock()
        mock_response.data = {}
        request = self.factory.get("/")

        with (
            patch.object(
                ArchesResourceDetailView, "retrieve", return_value=mock_response
            ),
            patch("bcap.views.api.inject_map_attributes"),
        ):
            result = self.view.retrieve(request, pk="some-uuid", graph="arch_site")

        self.assertIs(result, mock_response)

    def test_graph_kwarg_absent_passes_none_to_inject(self):
        mock_response = MagicMock()
        mock_response.data = {}
        request = self.factory.get("/")

        with (
            patch.object(
                ArchesResourceDetailView, "retrieve", return_value=mock_response
            ),
            patch("bcap.views.api.inject_map_attributes") as mock_inject,
        ):
            self.view.retrieve(request, pk="some-uuid")

        _, _, graph_arg = mock_inject.call_args[0]
        self.assertIsNone(graph_arg)


# ---------------------------------------------------------------------------
# RelatedSiteVisits.get_queryset
# ---------------------------------------------------------------------------


class RelatedSiteVisitsTests(SimpleTestCase):
    def _make_view(self, graph_slug="archaeological_site", resource_ids=None):
        view = RelatedSiteVisits()
        view.graph_slug = graph_slug
        view.resource_ids = resource_ids or ["some-uuid"]
        return view

    def test_field_error_raises_validation_error(self):
        view = self._make_view()
        with patch(
            "bcap.views.api.RelatedResourceService.base_query",
            side_effect=FieldError("field not found"),
        ):
            with self.assertRaises(ValidationError) as ctx:
                view.get_queryset()

        self.assertIn("archaeological_site", str(ctx.exception.detail))

    def test_value_error_raises_validation_error(self):
        view = self._make_view(graph_slug="unknown_graph")
        with patch(
            "bcap.views.api.RelatedResourceService.base_query",
            side_effect=ValueError("no nodes found"),
        ):
            with self.assertRaises(ValidationError) as ctx:
                view.get_queryset()

        self.assertIn("unknown_graph", str(ctx.exception.detail))
