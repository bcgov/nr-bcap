"""The API reports Django validation errors as 400s rather than letting them
escape as 500s."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import SimpleTestCase
from rest_framework.exceptions import NotFound

from bcap.views.exception_handlers import bcap_exception_handler


class ExceptionHandlerTests(SimpleTestCase):
    def test_field_keyed_error_keeps_its_alias(self):
        error = DjangoValidationError({"report_file": ["File failed virus scan"]})
        response = bcap_exception_handler(error, {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {"report_file": ["File failed virus scan"]})

    def test_unkeyed_error_is_not_echoed_back(self):
        # No field to attach it to means it was not about the submitted data.
        self.assertIsNone(bcap_exception_handler(DjangoValidationError("nope"), {}))

    def test_other_exceptions_are_left_to_drf(self):
        response = bcap_exception_handler(NotFound(), {})
        self.assertEqual(response.status_code, 404)
