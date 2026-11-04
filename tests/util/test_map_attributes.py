from django.test import SimpleTestCase
from unittest.mock import MagicMock, patch

from bcap.util.map_attributes import inject_map_attributes


def _make_response(alias, features=None):
    if features is None:
        features = [{"type": "Feature", "geometry": None, "properties": {}}]
    return {
        "aliased_data": {
            alias: {"aliased_data": {alias: {"node_value": {"features": features}}}}
        }
    }


class InjectMapAttributesTests(SimpleTestCase):
    def test_noop_for_unknown_graph_slug(self):
        with patch("bcap.util.map_attributes.connection") as mock_conn:
            inject_map_attributes({}, "rid", "unknown_slug")
            mock_conn.cursor.assert_not_called()

    @patch("bcap.util.map_attributes.connection")
    def test_noop_when_no_attrs_returned(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        features = [{"type": "Feature", "geometry": None, "properties": {}}]
        response = _make_response("site_boundary", features)
        inject_map_attributes(response, "rid", "archaeological_site")

        self.assertEqual(features[0]["properties"], {})

    @patch("bcap.util.map_attributes.connection")
    def test_noop_when_node_not_in_response(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [("borden_number", "EeRm-1")]

        # Should not raise even though response_data has no aliased_data
        inject_map_attributes({}, "rid", "archaeological_site")

    @patch("bcap.util.map_attributes.connection")
    def test_injects_attributes_into_feature_properties(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            ("borden_number", "EeRm-1"),
            ("registration_status", "Registered"),
        ]

        features = [{"type": "Feature", "geometry": None, "properties": {}}]
        response = _make_response("site_boundary", features)
        inject_map_attributes(response, "rid", "archaeological_site")

        self.assertEqual(features[0]["properties"]["borden_number"], "EeRm-1")
        self.assertEqual(features[0]["properties"]["registration_status"], "Registered")

    @patch("bcap.util.map_attributes.connection")
    def test_injects_attributes_into_all_features(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [("borden_number", "EeRm-1")]

        features = [
            {"type": "Feature", "geometry": None, "properties": {}},
            {"type": "Feature", "geometry": None, "properties": {}},
        ]
        response = _make_response("site_boundary", features)
        inject_map_attributes(response, "rid", "archaeological_site")

        for feature in features:
            self.assertEqual(feature["properties"]["borden_number"], "EeRm-1")

    @patch("bcap.util.map_attributes.connection")
    def test_preserves_existing_feature_properties(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [("borden_number", "EeRm-1")]

        features = [
            {
                "type": "Feature",
                "geometry": None,
                "properties": {"existing": "value"},
            }
        ]
        response = _make_response("site_boundary", features)
        inject_map_attributes(response, "rid", "archaeological_site")

        self.assertEqual(features[0]["properties"]["existing"], "value")
        self.assertEqual(features[0]["properties"]["borden_number"], "EeRm-1")

    @patch("bcap.util.map_attributes.connection")
    def test_creates_properties_dict_when_missing(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [("borden_number", "EeRm-1")]

        features = [{"type": "Feature", "geometry": None}]
        response = _make_response("site_boundary", features)
        inject_map_attributes(response, "rid", "archaeological_site")

        self.assertEqual(features[0]["properties"]["borden_number"], "EeRm-1")

    @patch("bcap.util.map_attributes.connection")
    def test_site_visit_slug_is_supported(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [("site_visit_type", "Inspection")]

        features = [{"type": "Feature", "geometry": None, "properties": {}}]
        response = _make_response("site_visit_location", features)
        inject_map_attributes(response, "rid", "site_visit")

        self.assertEqual(features[0]["properties"]["site_visit_type"], "Inspection")

    @patch("bcap.util.map_attributes.connection")
    def test_executes_sql_with_correct_resource_and_node_args(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        inject_map_attributes({}, "my-resource-id", "archaeological_site")

        args = mock_cursor.execute.call_args[0][1]
        self.assertEqual(args[0], "my-resource-id")
        # nodeid comes from GRAPH_CONFIG for archaeological_site
        self.assertEqual(args[1], "b18223c2-13ef-11f0-8695-0242ac170007")
