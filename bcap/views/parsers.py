"""Multipart parsing that refuses disallowed uploads before any view sees them."""

from django.conf import settings
from rest_framework.exceptions import ValidationError

from arches.app.utils.file_validator import FileValidator
from arches_querysets.rest_framework.multipart_json_parser import MultiPartJSONParser


def is_refused(upload):
    """Whether arches' validator refuses this upload."""
    errors = FileValidator().validate_file_type(upload, upload.name.split(".")[-1])
    # The validator reads the file and only sometimes rewinds it.
    upload.seek(0)
    return bool(errors)


class ValidatedMultiPartJSONParser(MultiPartJSONParser):
    """Arches checks file types only for uploads keyed by node id, and the permit
    forms key theirs by tile as well, so every upload is checked here.

    TODO: arches bug. FileListDataType.validate_file_types looks the files up
    without the tile, so file-list_<tileid>-<nodeid> uploads skip the type check
    while the save still stores them. Report upstream; once fixed this only adds
    the friendlier message."""

    def parse(self, stream, media_type=None, parser_context=None):
        parsed = super().parse(stream, media_type, parser_context)
        refused = [
            upload.name
            for key, uploads in parsed.files.lists()
            if key != "json"
            for upload in uploads
            if is_refused(upload)
        ]
        if refused:
            # One line each, which the frontend shows as is.
            raise ValidationError(
                {
                    "files": [
                        "These files are not permitted:",
                        *refused,
                        f"Allowed file types: {', '.join(settings.FILE_TYPES)}.",
                    ]
                }
            )
        return parsed
