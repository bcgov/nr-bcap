"""Custom REST framework serializer fields."""

from rest_framework.fields import DateTimeField

# fix this upstream in arches-querysets. Its REST serializer maps a date
# node to DRF's DateTimeField, which strips an aware datetime to naive under
# USE_TZ off, producing a value core arches' own DateDataType then rejects. The
# field below is a local workaround. Sibling projects (bcfms, bcrhp) don't write
# datetime date nodes through this path, so they have not hit it.


class OffsetPreservingDateTimeField(DateTimeField):
    """Keep an aware datetime's UTC offset instead of dropping it. With USE_TZ
    off, DRF strips the offset to a naive value, which then fails date validation
    and Elasticsearch indexing (the accepted datetime formats all carry an
    offset). Naive inputs, such as a date-only value, are left as they are."""

    def enforce_timezone(self, value):
        return value


def register_offset_preserving_date_field():
    """Use the offset-preserving field for date nodes on the REST write path.
    Call from AppConfig.ready(): the imports must be deferred until the app
    registry is loaded."""
    from django.db.models import DateTimeField
    from arches_querysets.rest_framework.serializers import TileAliasedDataSerializer

    TileAliasedDataSerializer.register_custom_datatype_field(
        DateTimeField, OffsetPreservingDateTimeField
    )
