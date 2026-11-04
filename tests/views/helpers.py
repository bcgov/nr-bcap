from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone

from oauth2_provider.models import AccessToken, get_application_model

from arches_controlled_lists.models import ListItem

from bcap.permissions.groups import Groups
from bcap.util.graph import get_node


def login_as(client, user, login_source="IDIR"):
    """Log the client in the way an IDIR session looks. Takes the client so
    class-level fixture setup can use it too."""
    client.force_login(user)
    session = client.session
    session["oauth_token"] = {
        "expires_at": (timezone.now() + timedelta(hours=1)).timestamp(),
        "userinfo": {"loginSource": login_source},
    }
    session.save()


class AuthTestHelper:
    """Sets up cls.user, cls.application, cls.access_token for auth tests.

    cls.user is an external applicant, in the Submitter group registration puts
    them in; a test needing ministry staff adds an internal group itself.

    Subclasses that define setUpTestData must call super().setUpTestData().
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        User = get_user_model()
        cls.user = User.objects.create_user(
            username="testuser",
            password="pass",
            email="testuser@example.com",
        )
        cls.user.groups.add(Group.objects.get(name=Groups.SUBMITTER))

        Application = get_application_model()
        cls.application = Application.objects.create(
            user=cls.user,
            name="test-app",
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_PASSWORD,
        )

        cls.access_token = AccessToken.objects.create(
            user=cls.user,
            application=cls.application,
            token="test-access-token",
            scope="read write",
            expires=timezone.now() + timedelta(hours=1),
        )

    def idir_login_simulate(self, user=None, login_source="IDIR"):
        login_as(self.client, user or self.user, login_source)


def api_reference_value(slug, alias, label=None):
    """Build a reference value in the format the REST serializer expects.

    The builder's ``reference_value()`` returns bare UUID strings, which are
    correct for tile saves but are rejected by the DRF serializer's
    ``ReferenceDataType.to_python``, which requires dicts with ``uri``,
    ``labels``, and ``list_id`` keys."""
    node = get_node(slug, alias)
    list_id = node.config["controlledList"]
    qs = ListItem.objects.filter(list_id=list_id)
    item = (
        qs.filter(list_item_values__value=label).first()
        if label
        else qs.order_by("sortorder").first()
    )
    labels = [
        {
            "id": str(lv.pk),
            "value": lv.value,
            "language_id": lv.language_id,
            "valuetype_id": lv.valuetype_id,
            "list_item_id": str(item.pk),
        }
        for lv in item.list_item_values.all()
    ]
    return [{"uri": item.uri, "labels": labels, "list_id": str(list_id)}]
