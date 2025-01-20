# BCHeritage
BC Heritage Branch Arches configuration, schemas and extensions for Historic Places and
Fossils Management.

![Lifecycle:Experimental](https://img.shields.io/badge/Lifecycle-Experimental-339999)

### Running in Docker
**These steps assume that the base directory is ~/git.**
1. Start Docker Desktop
2. Create the Arches Dependency Containers:
``` shell
cd ~/git
git clone https://github.com/bcgov/arches-dependency-containers
cd arches-dependency-containers/arches-7-5-2
docker compose up
```
This should result in a set of docker containers that have the base dependency software to run
Arches (Postgres, Elasticsearch, Redis, etc).

3. Clone BCGov Arches Core at the same level as this directory. Assuming that all dependencies
are installed in ~/git/bcap/.
``` shell
cd git
git clone https://github.com/bcgov/arches
git clone https://github.com/bcgov/arches_common
cd arches && git checkout stable/7.6.4_bcgov_11578_11716
# This should result in a directory structure like the below:
~/git/bcap/
     /bcap/arches/      # <- This is a clone of the arches bcgov/arches repo
     /bcap/bcap-nr/     # <- This directory
     /bcap/bcap_common/ # <- This is a clone of the bcgov/arches_common repo
```


4. Change back to the nr-bcap directory and create the test user data file at
`bcap/management/data/test_user_list.py`:

    1. the password is only a dummy password so it can be left as is. OIDC is used so when
authenticating you will use your IDIR username and password.
   2. the `@idir` suffix is necessary
   3. tht `<idir username>` must be in lower case
``` python
def get_user_list():
   return (
   {"name": "<idir username>@idir", "email": "<email>", "password": "Test12345!", "is_superuser": True,
   "is_staff": True, "first_name": "<first name>", "last_name": "<last name>",
   "groups": ["Resource Editor", "Resource Reviewer", "Archaeology Branch", "Resource Exporter"]},
   )
```

5. Create the BCAP containers:
```shell
cd git/nr-bcap
docker compose up
```

You should now be able to access BCAP at http://localhost:82/bcap

6. After logging into BCAP, the map will initially be blank. Navigate to the system settings in the LHS
menu and enter your Mapbox token there.