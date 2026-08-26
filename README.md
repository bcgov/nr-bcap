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
git clone https://github.com/archesproject/arches-vue-components
git clone https://github.com/archesproject/arches-controlled-lists
git clone https://github.com/archesproject/arches-querysets
git clone https://github.com/bcgov/bcgov-arches-common
git clone https://github.com/bferguso/arches-workflow-stepper
git clone https://github.com/bferguso/arches-zod-validation
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
    ├── 📁 arches-vue-components/
    ├── 📁 arches-controlled-lists/
    ├── 📁 arches-workflow-stepper/
    ├── 📁 arches-zod-validation/
    └── 📁 nr-bcap/
```

## Arches
1. Open or navigate to the `bcap` directory in the terminal
2. Run the following command:
```
cd arches && git checkout dev/8.1.x_bcgov
```

# Docker configuration
There are 3 application specific docker containers and 4 common depdendency containers:
1. bcap: Application container (Django dev server, BCAP codebase)
2. bcap-proxy: Nginx proxy container
3. bcap-pg_tileserv: Postgres Tileserve container - tile server for hosting local map tiles
3. bcap-pg_featureserv: Postgres Featureserv container - tile server for hosting local wfs (Used for QGIS plugin)
4. bcap-nginx: Nginx container - reverse proxy for the Arches application
5. bcap-jupyter: Jupyter container - for development
6. Depdendency containers - These containers can be shared across applications
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

## Debugging w/ PyCharm
This is done w/ modifications to the manage.py file that connects from the docker container back to the host so no ports
need to be configured in the docker-compose.yml file.

To activate this debugging mode:
1. Add/edit the following lines in the ./docker/docker.dev.env file:
   ```
   INSTALL_PYCHARM_DEBUG=true
   PYCHARM_DEBUG=true
   DOCKER_HOST_PLATFORM=linux/arm64 # One of linux/arm64, linux/amd64
   ```
2. Create a Python Debug Server configuration in PyCharm and set the following:
   - host: localhost
   - port: 5680
   - path mappings:
      - `<dir to nr-bcap parent on host> -> /web_root`
      - `<dir to nr-bcap on host> -> /web_root/bcap`

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
3. Let the `bcap` container fully load (i.e., watch the "Logs" tab). There will be a warning about missing environment variables.
    - You will see: `django.core.exceptions.ImproperlyConfigured: Set the BCGOV_PROXY_PREFIX environment variable`
    - This can take some time.
4. You need to create or move the .env file to `bcap/nr-bcap/.env`
6. Restart the `bcap` container in Docker Desktop
7. Open the `bcap` container in Docker Desktop
8. Go to the "Exec" tab and run the following:
```
bash
cd bcap && mkdir logs
```
9. Restart the `bcap` container in Docker Desktop

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
4. Start and open the `bcap` container in Docker Desktop
5. Go to the "Exec" tab and run the following:
```
python3 manage.py bc_test_users --refresh
```
6. Open the "Inspect" tab in the container
7. `Ctrl + F` for `Networks` and look for `IPAddress`
8. Copy the IP Address and open the `bcap/nr-bcap/.env` file
9. Add the IP Address to the `AUTH_BYPASS_HOSTS` variable:
    - `AUTH_BYPASS_HOSTS = ... ... <IPAddress>`

10. Open the `bcap` container in Docker Desktop
11. Go to the "Exec" tab and run the following:
```
npm run build_development
python3 manage.py setup_db
```

#### Authentication
1. Open `bcap/nr-bcap/bcap/settings.py`
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
"django.contrib.auth.backends.ModelBackend",
"guardian.backends.ObjectPermissionBackend",
"arches.app.utils.permission_backend.PermissionBackend",
```
- Comment out the following:
```
"arches.app.utils.email_auth_backend.EmailAuthenticationBackend",
"django.contrib.auth.backends.RemoteUserBackend",
```

- You must also add the secret to the `OAUTH_CLIENT_SECRET` variable in the .env file

#### Run
1. You should now be able to access BCAP at http://localhost:82/bcap
2. If it doesn't work, then open or navigate to the `bcap` directory in the terminal
2. Restart the `bcap` container or run the following command:
```
cd nr-bcap && docker compose up -d
```
4. After logging into BCAP, the map will initially be blank.
    - You must navigate to the "System Settings" from the menu on the left-hand side, and enter your `Mapbox` token there.

### Loading in a Database
If you have been given a database dump like bcap.sql follow these steps to load it into the system.
1. Copy db file into your docker container from any terminal.
```
docker cp bcap.sql bcap:/tmp/bcap.sql
```
2. Create and index the database from the Exec tab inside your container (indexing may take up to an hour).
```
createdb -U postgres -h postgres16-3_arches7-5-2 bcap
psql -U postgres -h postgres16-3_arches7-5-2 -d bcap -c "CREATE EXTENSION IF NOT EXISTS postgis;"
psql -U postgres -h postgres16-3_arches7-5-2 -d bcap -f /tmp/bcap.sql
python3 manage.py es index_database
```
3. If you are having trouble with logins you might need to refresh your test user list
```
python3 manage.py bc_test_users --refresh
```

## Developing the UI using Vite
See [README.vite.md](./README.vite.md) for details about developing using the Vite dev server.

### Dashboard API contract

Documented DRF views → `schema.yml` (OpenAPI) → Zod schemas in
`bcap/src/bcap/client/` (via [@hey-api/openapi-ts](https://heyapi.dev); types via
`z.infer`). Regenerate in the `bcap` container after changing a documented
serializer, view, route, or resource model:

```bash
python3 manage.py regenerate_api
```

This runs the full pipeline: generated views → OpenAPI spec (drf_spectacular) →
zod client (openapi-ts) → formatting (black, prettier). Useful flags:

- `--check` — fail if any generated artifact drifts from the git index (CI use)
- `--skip-zod` — backend-only environments without npm
- `--skip-views` — use the committed generated views as-is

NOTE: Only the limited documented routes for now; arches-queryset routes later.

To load sample dashboard data into the current database (permit application, related resources, and Elasticsearch indexing):

```bash
# Small demo graph (one permit, three short requirements)
python3 manage.py seed_dashboard_demo

# Just the process-requirement templates (no permit application)
python3 manage.py seed_template_requirements

# Seed several cards at once (each with randomized names and application id)
python3 manage.py seed_dashboard_demo --count 20
```

Seeded data uses [Faker](https://faker.readthedocs.io/) to randomize holder names, project officer, ministry assignees, and the application id, so each card is distinct. Both commands take `--count N` (default 1) and `--no-index` (for when Elasticsearch is not running).

To remove the seeded data again (only resources the seeders created are deleted — real data in the same graphs is left untouched):

```bash
python3 manage.py clear_dashboard_data
```

These are temporary developer aids and will be removed in a future release.

## Running Backend Unit Tests

```
python3 manage.py test tests --pattern="*.py" --settings="tests.test_settings" --keepdb
```

- `--keepdb` reuses the existing test database between runs to save time
- To run a specific test module or class, replace `tests` with the dotted path (e.g. `tests.views.test_api`)

## Notes
- RabbitMQ is not being used
- We do not use the Django template engine, therefore changes to the Django code need to be rebuilt with the webpack


