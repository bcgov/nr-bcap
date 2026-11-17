"""End-to-end tests for the BCAP Service Request create endpoint."""

import json
from django.test import TestCase, override_settings
from django.urls import reverse

from bcap.util.aliases.bcap_service_request import (
    BcapServiceRequestAliases as aliases,
    BcapServiceRequestGroupAliases as group_aliases,
)
from bcap.util.bcap_aliases import ALIASED_DATA, GraphSlugs

from tests.views.helpers import AuthTestHelper, api_reference_value, login_as


def _identification_tile():
    """SERVICE_REQUEST_IDENTIFICATION tile with required service_request_type."""
    return {
        group_aliases.SERVICE_REQUEST_IDENTIFICATION: {
            ALIASED_DATA: {
                aliases.SERVICE_REQUEST_TYPE: api_reference_value(
                    GraphSlugs.BCAP_SERVICE_REQUEST,
                    aliases.SERVICE_REQUEST_TYPE,
                )
            }
        }
    }


def create_payload():
    """Minimal create body — service_request_id is backend-generated and
    injected before validation; only service_request_type is user-required."""
    return {ALIASED_DATA: _identification_tile()}


def boundary_payload(feature_id="not-a-uuid"):
    """A create body carrying a GeoJSON boundary with a non-UUID feature ID."""
    return {
        ALIASED_DATA: {
            **_identification_tile(),
            group_aliases.SERVICE_REQUEST_LOCATION: {
                ALIASED_DATA: {
                    aliases.PROPERTY_TYPE: api_reference_value(
                        GraphSlugs.BCAP_SERVICE_REQUEST,
                        aliases.PROPERTY_TYPE,
                    ),
                    aliases.SERVICE_REQUEST_BOUNDARY: {
                        "node_value": {
                            "type": "FeatureCollection",
                            "features": [
                                {
                                    "type": "Feature",
                                    "id": feature_id,
                                    "geometry": {
                                        "type": "Point",
                                        "coordinates": [-123.0, 49.0],
                                    },
                                    "properties": {},
                                }
                            ],
                        }
                    },
                }
            },
        }
    }


@override_settings(ROOT_URLCONF="tests.test_urls")
class BcapServiceRequestCreateTests(AuthTestHelper, TestCase):
    def _post(self, payload, client=None):
        c = client or self.client
        return c.post(
            reverse("bcap_service_request_create"),
            data=json.dumps(payload),
            content_type="application/json",
        )

    def setUp(self):
        self.idir_login_simulate()

    def test_authenticated_submitter_can_create(self):
        resp = self._post(create_payload())
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertIn("resourceinstanceid", resp.json())

    def test_anonymous_post_is_forbidden(self):
        from django.test import Client

        resp = self._post(create_payload(), client=Client())
        self.assertEqual(resp.status_code, 302)

    def test_service_request_id_is_seeded(self):
        """The backend must inject a reference-number-widget style id (e.g.
        SR-2024-0001) when the payload omits it, because the graph requires
        it but the form never sets it."""
        import re

        resp = self._post(create_payload())
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()
        ident = (data.get(ALIASED_DATA) or {}).get(
            group_aliases.SERVICE_REQUEST_IDENTIFICATION, {}
        )
        sr_id = (ident.get(ALIASED_DATA) or {}).get(aliases.SERVICE_REQUEST_ID, {})
        node_value = sr_id.get("node_value") or ""
        self.assertRegex(
            str(node_value),
            re.compile(r"^[A-Z]+-\d{4}-\d+$"),
            f"service_request_id {node_value!r} is not in <ABBR>-YYYY-NNNN format",
        )

    def test_non_uuid_feature_ids_are_sanitized(self):
        """WFS feature IDs (text strings) must be replaced with UUIDs before
        the geometry is saved, otherwise Arches rejects the tile."""
        resp = self._post(boundary_payload("WHSE_CADASTRE.PMBC.fid--abc123"))
        self.assertEqual(resp.status_code, 201, resp.content)

        # The persisted boundary must carry a UUID feature id, not the
        # original text string.
        data = resp.json()
        project_location = (data.get(ALIASED_DATA) or {}).get(
            group_aliases.SERVICE_REQUEST_LOCATION, {}
        )
        boundary = (project_location.get(ALIASED_DATA) or {}).get(
            aliases.SERVICE_REQUEST_BOUNDARY, {}
        )
        features = (boundary.get("node_value") or {}).get("features", [])
        if features:
            import uuid

            fid = features[0].get("id", "")
            try:
                uuid.UUID(str(fid))
                is_uuid = True
            except ValueError:
                is_uuid = False
            self.assertTrue(is_uuid, f"Feature id {fid!r} is not a UUID")
