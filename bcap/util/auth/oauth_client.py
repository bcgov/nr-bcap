from authlib.integrations.django_client import OAuth
from django.conf import settings
from bcap.util.auth.token_store import save_token


oauth = OAuth()
oauth.register(
    name="bcap_oauth",
    **settings.AUTHLIB_OAUTH_CLIENTS["bcap_oauth"],
    update_token=save_token,
)
