from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import SimpleTestCase
from rest_framework.exceptions import NotFound

from bcap.views.exception_handler import UNEXPECTED_ERROR, bcap_exception_handler

MISSING = "This card requires values for the following: Submission Type"


class ExceptionHandlerTests(SimpleTestCase):
    def handle(self, exc):
        return bcap_exception_handler(exc, {"view": None})

    def test_a_tile_validation_error_is_a_400_per_field(self):
        response = self.handle(DjangoValidationError({"submission_type": MISSING}))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {"submission_type": [MISSING]})

    def test_a_bare_validation_error_is_a_400(self):
        response = self.handle(DjangoValidationError(MISSING))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {"non_field_errors": [MISSING]})

    def test_anything_else_is_a_generic_500(self):
        with self.assertLogs("bcap.views.exception_handler", "ERROR"):
            response = self.handle(RuntimeError("secret internals"))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data, {"detail": UNEXPECTED_ERROR})

    def test_drf_errors_pass_through(self):
        self.assertEqual(self.handle(NotFound()).status_code, 404)
