# BC Archaeology
BC Archaeology Branch Arches configuration, schemas and extensions for the BC Archaeology Portal.

![Lifecycle:Experimental](https://img.shields.io/badge/Lifecycle-Experimental-339999)

## Prerequisites
- Docker Desktop

## Project Setup
1. Create a directory called `bcap`
2. Open a terminal and navigate to the `bcap` directory
3. Run the following to clone the repositories required for this project:
```
git clone https://github.com/bcgov/arches-dependency-containers
git clone https://github.com/bcgov/arches
git clone https://github.com/archesproject/arches-component-lab
git clone https://github.com/archesproject/arches-controlled-lists
git clone https://github.com/archesproject/arches-querysets
git clone https://github.com/bcgov/bcgov-arches-common
git clone https://github.com/bcgov/nr-bcap
```

- You should now have the following directory structure:
```
.
└── 📁 bcap/
    ├── 📁 arches-dependency-containers/
    ├── 📁 arches/
    ├── 📁 bcgov-arches-common/
    ├── 📁 arches-querysets/
    ├── 📁 arches-component-lab/
    ├── 📁 arches-controlled-lists/
    └── 📁 nr-bcap/
```

## Arches
1. Open or navigate to the `bcap` directory in the terminal
2. Run the following command:
```
cd arches && git checkout stable/8.0.3_bcgov_12377
```

# Docker configuration
There are 3 application specific docker containers and 4 common depdendency containers:
1. bcap7-6: Application container (Django dev server, BCAP codebase)
2. bcap-proxy7-6: Nginx proxy container
3. bcap-pg_tileserv7-6: Postgres Tileserve container - tile server for generating local map tiles
4. Depdendency containers - These containers can be shared across applications
   1. postgres16-3_arches7-5-2: Postgres/PostGIS container
   2. elasticsearch8-3_arches7-5-2: Elasticsearch container
   3. redis_arches7-5-2: Redis container
   4. rabbitmq3_arches7-5-2: RabbitMQ (not currently used, but still there)

## Arches Dependency Containers
- We need to load the base dependencies needed for Arches (i.e., Postgres, Elasticsearch, Redis, etc).
1. Open or navigate to the `bcap` directory in the terminal
2. Run the following command to setup the project's dependencies:
```
cd arches-dependency-containers/arches-7-5-2 && docker compose up -d
```

## nr-bcap

### Prerequisites
- An .env file

### Setup

#### Docker Desktop
1. Open or navigate to the `bcap` directory in the terminal
2. Run the following command:
```
cd nr-bcap && docker compose up -d
```
3. Let the `bcap7-6` container fully load (i.e., watch the "Logs" tab). There will be a warning about missing environment variables.
    - You will see: `django.core.exceptions.ImproperlyConfigured: Set the BCGOV_PROXY_PREFIX environment variable`
    - This can take some time.
4. You need to create or move the .env file to `bcap/nr-bcap/.env`
6. Restart the `bcap7-6` container in Docker Desktop
7. Open the `bcap7-6` container in Docker Desktop
8. Go to the "Exec" tab and run the following:
```
bash
cd bcap && mkdir logs
```
9. Restart the `bcap7-6` container in Docker Desktop

#### `test_user_list.py`
1. Create  `test_user_list.py` in `bcap/nr-bcap/bcap/management/data/test_user_list.py`
2. Put the following function in the `test_user_list.py` file if you do not have an IDIR username/password:
```
def get_user_list():
    return [
        {
            "name": "testuser123",
            "email": "test@email.com",
            "password": "Test12345!",
            "is_superuser": True,
            "is_staff": True,
            "first_name": "Test",
            "last_name": "User",
            "groups": [
                "Resource Editor",
                "Resource Reviewer",
                "Archaeology Branch",
                "Resource Exporter"
            ]
        }
    ]
```
3. Put the following function in the `test_user_list.py` file if you do have an IDIR username/password:
```
def get_user_list():
    return [
        {
            "name": "<idir username>@idir",
            "email": "<email>",
            "password": "Test12345!",
            "is_superuser": True,
            "is_staff": True,
            "first_name": "<first name>",
            "last_name": "<last name>",
            "groups": [
                "Resource Editor",
                "Resource Reviewer",
                "Archaeology Branch",
                "Resource Exporter",
            ],
        },
    ]
```
- The password is a dummy password so it can be left as is.
- OIDC is used so when authenticating you will use your IDIR username and password.
- The `@idir` suffix is necessary
- The `<idir username>` must be in lowercase
4. Start and open the `bcap7-6` container in Docker Desktop
5. Go to the "Exec" tab and run the following:
```
python3.11 manage.py bc_test_users --refresh
```
6. Open the "Inspect" tab in the container
7. `Ctrl + F` for `Networks` and look for `IPAddress`
8. Copy the IP Address and open the `bcap/nr-bcap/.env` file
9. Add the IP Address to the `AUTH_BYPASS_HOSTS` variable:
    - `AUTH_BYPASS_HOSTS = ... ... <IPAddress>`

10. Open the `bcap7-6` container in Docker Desktop
11. Go to the "Exec" tab and run the following:
```
npm run build_development
python3.11 manage.py setup_db
```

#### Authentication
1. Open `bcap/nr-bcap/bcap/settings.py` and `bcap/nr-bcap/bcap/urls.py`
2. Find `AUTHENTICATION_BACKENDS` in the `settings.py` file

#### Django Auth
- Comment out the following:
```
"oauth2_provider.backends.OAuth2Backend",
"bcap.util.external_oauth_backend.ExternalOauthAuthenticationBackend",
```
- Uncomment the following:
```
"django.contrib.auth.backends.ModelBackend"
```

#### OAuth2
- Uncomment the following:
```
"oauth2_provider.backends.OAuth2Backend",
"bcap.util.external_oauth_backend.ExternalOauthAuthenticationBackend",
```
- Comment out the following:
```
"django.contrib.auth.backends.ModelBackend"
```

- You must also add the secret to the `OAUTH_CLIENT_SECRET` variable in the .env file

3. Go to the `urls.py` file

4. If you are using...
- Django Auth, then comment out the following:
- OAuth2, then uncomment the following:
```
    re_path(
        bc_path_prefix(r"^admin/login/$"),
        ExternalOauth.start,
        name="external_oauth_start",
    ),
    re_path(
        bc_path_prefix(r"^auth/$"),
        ExternalOauth.start,
        name="external_oauth_start"
    ),
    re_path(
        bc_path_prefix(r"^auth/eoauth_cb$"),
        ExternalOauth.callback,
        name="external_oauth_callback",
    ),
    re_path(
        bc_path_prefix(r"^auth/eoauth_start$"),
        ExternalOauth.start,
        name="external_oauth_start",
    ),
    re_path(
        bc_path_prefix(r"^unauthorized/"),
        UnauthorizedView.as_view(),
        name="unauthorized",
    ),
```
#### Run
1. You should now be able to access BCAP at http://localhost:82/bcap
2. If it doesn't work, then open or navigate to the `bcap` directory in the terminal
2. Restart the `bcap7-6` container or run the following command:
```
cd nr-bcap && docker compose up -d
```
4. After logging into BCAP, the map will initially be blank.
    - You must navigate to the "System Settings" from the menu on the left-hand side, and enter your `Mapbox` token there.

## Developing the UI using Vite
See [README.vite.md](./README.vite.md) for details about developing using the Vite dev server.

## Notes
- RabbitMQ is not being used
- We do not use the Django template engine, therefore changes to the Django code need to be rebuilt with the webpack


