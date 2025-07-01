import logging

logger = logging.getLogger(__name__)


# This is called automatically by Authlib on refresh
def save_token(token, request=None, **kwargs):
    logger.info(f"[Token Store] Token refreshed: {token}")
    if request:
        request.session["oauth_token"] = token
    else:
        logger.warning("Token refresh occurred without request context.")
