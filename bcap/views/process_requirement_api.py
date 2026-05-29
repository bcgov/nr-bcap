"""Process Requirement write API: validate the body, drive the service, save."""

from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import JSONParser
from rest_framework.request import Request
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema

from arches_querysets.models import ResourceTileTree
from arches_querysets.rest_framework.permissions import ResourceEditor

from bcap.serializers.process_requirement_serializers import (
    ProcessRequirementSerializer,
)
from bcap.services.exceptions import StaleReference
from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)
from bcap.services.process_requirement.process_requirement_types import (
    ProcessRequirement,
)


class ProcessRequirementWriteView(GenericAPIView):
    """Edit an existing Process Requirement; it does not create one."""

    authentication_classes = [SessionAuthentication]
    # Will need to extend this later.
    permission_classes = [ResourceEditor]
    parser_classes = [JSONParser]
    serializer_class = ProcessRequirementSerializer
    lookup_url_kwarg = "resource_id"
    service = ProcessRequirementService()

    def get_queryset(self):
        """The Process Requirement tile trees get_object() resolves against."""
        return self.service.get_queryset()

    @extend_schema(responses=ProcessRequirementSerializer)
    def patch(self, request: Request, *args, **kwargs) -> Response:
        """Apply the provided dates and sub-requirement edits, then save."""
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data: ProcessRequirement = serializer.validated_data
        resource: ResourceTileTree = self.get_object()  # 404s if it doesn't exist
        self.service.set_requirement_process_dates(
            resource,
            start_date=data.start_date,
            due_date=data.due_date,
            completion_date=data.completion_date,
        )
        try:
            self.service.edit_sub_requirements(resource, data.sub_requirements)
        except StaleReference as exc:
            raise NotFound("Sub-requirement not found on this requirement.") from exc
        except ValueError as exc:
            raise ValidationError(
                "A new sub-requirement needs a name and sort order."
            ) from exc

        resource.save(request=request)
        result = self.service.to_output(resource)
        return Response(ProcessRequirementSerializer(result).data)
