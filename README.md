# BCHeritage
BC Heritage Branch Arches configuration, schemas and extensions for Historic Places and
Fossils Management.

![Lifecycle:Experimental](https://img.shields.io/badge/Lifecycle-Experimental-339999)

### Running in Docker
1. Start Docker Desktop
1. Create the Arches Dependency Containers :
``` shell
cd .../git
git clone https://github.com/bcgov/arches-dependency-containers
cd arches-dependency-containers/arches-7-5-2
docker compose up
```
This should result in a set of docker containers that have the base dependency software to run
Arches (Postgres, Elasticsearch, Redis, etc).

2. Clone BCGov Arches Core at the same level as this directory.
``` shell
cd git
git clone https://github.com/bcgov/arches
git clone https://github.com/bcgov/arches_common
# This should result in a directory structure like the below:
.../git/bcap/
       /bcap/arches/      # <- This is a clone of the arches bcgov/arches repo
       /bcap/bcap-nr/     # <- This directory
       /bcap/bcap_common/ # <- This is a clone of the bcgov/arches_common repo
```

3. Change back to the nr-bcap directory and create the BCAP containers:
```shell
cd git/nr-bcap
docker compose up
```
