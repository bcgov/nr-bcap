"""
ARCHES - a program developed to inventory and manage immovable cultural heritage.
Copyright (C) 2013 J. Paul Getty Trust and World Monuments Fund

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import os
from django.core.management.base import BaseCommand
from oauth2_provider.models import Application


class Command(BaseCommand):
    """
    Commands for adding the BCAP API OAuth2 provider configuration.
    This requires the following environment variables to be set:
    1. BCRHP_API_CLIENT_ID
    2. BCRHP_API_CLIENT_SECRET (only if the config doesn't exist yet)

    """

    def handle(self, *args, **options):
        apps = Application.objects.filter(name="BCRHP API").all()
        if len(apps) == 0:
            add_bcrhp_oauth_config()
        elif len(apps) > 1:
            print(
                "More than one BCRHP API application found. Please delete the extra applications."
            )
        else:
            update_bcrhp_oauth_secret(apps[0])


def add_bcrhp_oauth_config():
    client_id = os.environ.get("BCRHP_API_CLIENT_ID")
    client_secret = os.environ.get("BCRHP_API_CLIENT_SECRET")
    if not client_id:
        print(
            "BCRHP_API_CLIENT_ID environment variable must be set to create new OAuth2 provider configuration."
        )
        return
    if not client_secret:
        print(
            "BCRHP_API_CLIENT_SECRET environment variable must be set to create new OAuth2 provider configuration."
        )

    app = Application()
    app.name = "BCRHP API"
    app.client_id = client_id
    app.client_type = "confidential"
    app.authorization_grant_type = "client-credentials"
    app.client_secret = client_secret
    app.skip_authorization = False
    app.hash_client_secret = True
    app.save()


def update_bcrhp_oauth_secret(app):
    client_secret = os.environ.get("BCRHP_API_CLIENT_SECRET")
    if not client_secret:
        print(
            "BCRHP_API_CLIENT_SECRET environment variable must be set to update new OAuth2 provider configuration."
        )
    app.client_secret = client_secret
    app.save()
