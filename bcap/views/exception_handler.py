"""DRF exception handler: every API error answers as readable JSON, never a
traceback, whatever DEBUG says. The traceback goes to the log instead."""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import exception_handler, set_rollback

from arches_querysets.rest_framework.view_mixins import ArchesModelAPIMixin

logger = logging.getLogger(__name__)

UNEXPECTED_ERROR = (
    "Something went wrong on our end. Please try again, or contact support if "
    "it keeps happening."
)


def bcap_exception_handler(exc, context):
    """Tile saves raise Django's ValidationError, which DRF leaves as a 500."""
    if isinstance(exc, DjangoValidationError):
        errors = ArchesModelAPIMixin.flatten_validation_errors(exc)
        if not isinstance(errors, dict):
            errors = {api_settings.NON_FIELD_ERRORS_KEY: errors}
        exc = ValidationError(errors)

    response = exception_handler(exc, context)
    if response is not None:
        return response

    logger.error("Unhandled error in %s", context.get("view"), exc_info=exc)
    set_rollback()
    return Response(
        {"detail": UNEXPECTED_ERROR}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
