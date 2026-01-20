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

    def add_arguments(self, parser):
        parser.add_argument(
            "-cid",
            "--client-id",
            action="store",
            dest="client_id",
            help="Well known client id for the OAUTH2 provider.",
        )
        parser.add_argument(
            "-cn",
            "--config-name",
            action="store",
            dest="config_name",
            help="Name of the OAuth2 provider configuration. Must be unique in the configurations.",
        )
        parser.add_argument(
            "-ct",
            "--client-type",
            action="store",
            dest="client_type",
            default="confidential",
            help="Client type. One of 'confidential' or 'public'.",
        )
        parser.add_argument(
            "-gt",
            "--grant-type",
            action="store",
            dest="grant_type",
            default="confidential",
            help="Authorization grant type. One of 'authorization-code', 'client-credentials', ...",
        )
        parser.add_argument(
            "-ru",
            "--redirect-uris",
            action="store",
            dest="redirect_uris",
            default="",
            help="Valid redirect URIs for the OAuth2 provider. Comma separated.",
        )
        parser.add_argument(
            "-ao",
            "--allowed_origins",
            action="store",
            dest="allowed_origins",
            default="",
            help="Allowed origins for CORS requests. Comma separated.",
        )
        parser.add_argument(
            "-ha",
            "--hash",
            action="store_true",
            dest="hash_secret",
            default=True,
            help="Whether to hash the client secret.",
        )

    def handle(self, *args, **options):
        client_secret = os.environ.get("CLIENT_SECRET")
        if not client_secret:
            print(
                "CLIENT_SECRET environment variable must be set to create new OAuth2 provider configuration."
            )
        apps = Application.objects.filter(name=options["config_name"]).all()
        if len(apps) == 0:
            add_oauth_config(client_secret, options)
        elif len(apps) > 1:
            print(
                "More than one BCRHP API application found. Please delete the extra applications."
            )
        else:
            update_oauth_secret(apps[0], client_secret)


def add_oauth_config(client_secret, options):
    app = Application()
    app.name = options["config_name"]
    app.client_id = options["client_id"]
    app.client_type = options["client_type"]
    app.authorization_grant_type = options["grant_type"]
    app.redirect_uris = options["redirect_uris"]
    app.allowed_origins = options["allowed_origins"]
    app.client_secret = client_secret
    app.skip_authorization = False
    app.hash_client_secret = True
    app.save()


def update_oauth_secret(app, client_secret):
    app.client_secret = client_secret
    app.save()
