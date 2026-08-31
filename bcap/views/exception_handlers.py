from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from rest_framework.views import exception_handler


def bcap_exception_handler(exc, context):
    """Report tile validation failures as 400s.

    Saving aliased data raises Django's ValidationError, which DRF leaves alone.
    Only the field-keyed form is translated; an unkeyed one was not written
    about the submitted data, so it stays a 500.
    """
    if isinstance(exc, DjangoValidationError) and hasattr(exc, "error_dict"):
        exc = ValidationError(exc.message_dict)
    return exception_handler(exc, context)
