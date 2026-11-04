from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from bcap.views.parsers import ValidatedMultiPartJSONParser

# How the permit forms key an upload: by tile as well as node, which arches'
# own file-type check never looks at.
TILE_KEY = "file-list_11111111-1111-1111-1111-111111111111-node"


def parsed(*uploads):
    django_request = APIRequestFactory().post(
        "/", {"json": "{}", TILE_KEY: list(uploads)}, format="multipart"
    )
    request = Request(django_request, parsers=[ValidatedMultiPartJSONParser()])
    request.data
    return request


class ValidatedMultiPartJSONParserTests(SimpleTestCase):
    def test_refused_uploads_are_listed_by_name(self):
        with self.assertRaises(ValidationError) as caught:
            parsed(
                SimpleUploadedFile("setup.exe", b"MZ\x90\x00binary"),
                SimpleUploadedFile("setup - Copy.exe", b"MZ\x90\x00binary"),
            )
        lines = caught.exception.detail["files"]
        self.assertEqual(
            lines[:3],
            ["These files are not permitted:", "setup.exe", "setup - Copy.exe"],
        )
        self.assertTrue(lines[-1].startswith("Allowed file types: "))

    def test_an_allowed_upload_arrives_rewound(self):
        request = parsed(SimpleUploadedFile("note.txt", b"hello"))
        self.assertEqual(request.FILES[TILE_KEY].read(), b"hello")
