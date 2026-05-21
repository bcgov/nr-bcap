# Note: We are using snake_case to be consistent with other arches returns.
from rest_framework.serializers import (
    Serializer,
    BooleanField,
    CharField,
    IntegerField,
    SerializerMethodField,
)


class UserProfileResponseSerializer(Serializer):
    username = CharField()
    first_name = CharField(allow_blank=True)
    last_name = CharField(allow_blank=True)
    groups = SerializerMethodField()
    contributor_id = SerializerMethodField()

    def get_groups(self, user) -> list[str]:
        return [group.name for group in user.groups.all()]

    def get_contributor_id(self, user) -> str | None:
        """TODO fill this in."""
        pass


class DashboardQuerySerializer(Serializer):
    filter_by = CharField(required=False, allow_blank=True)
    status = CharField(required=False, allow_blank=True)
    limit = IntegerField(required=False, default=50, min_value=1)
    page = IntegerField(required=False, default=1, min_value=1)
    order_by = CharField(required=False)


class DashboardCardResponseSerializer(Serializer):
    id = CharField()
    cap_priority = BooleanField()
    cap_label = CharField(allow_blank=True)
    cap_date = CharField(allow_blank=True)
    body_title = CharField(allow_blank=True)
    body_subtitle1 = CharField(allow_blank=True)
    body_subtitle2 = CharField(allow_blank=True)
    body1 = CharField(required=False, allow_blank=True)
    body2 = CharField(required=False, allow_blank=True)
    body3 = CharField(required=False, allow_blank=True)
    body4 = CharField(required=False, allow_blank=True)
    body5 = CharField(required=False, allow_blank=True)
    footer_date = CharField(allow_blank=True)
    footer_name = CharField(required=False, allow_blank=True)
    route = CharField(allow_blank=True)
    urgency = IntegerField()
