#!/usr/bin/env bash
set -euo pipefail

# Must be run from bcap root
APP_INSTANCE=$1
ANSIBLE_BRANCH=main

IDIR_PASSWORD=$(op item get "bferguso@idir" --vault "BCGov" --fields label=password --reveal)
GITHUB_TOKEN=$(op item get "github Ansible token" --vault "Private" --fields label=password --reveal)

if [[ "$APP_INSTANCE" == "prod" ]]; then
    DB_ADMIN_PASSWORD=$(op item get "postgres@early.bcgov" --vault "BCGov Arches" --fields label=password --reveal)
else
    DB_ADMIN_PASSWORD=$(op item get "postgres@endowment.bcgov" --vault "BCGov Arches" --fields label=password --reveal)
fi

docker exec -it \
    --env-file "./cd/docker/config/app_env" \
    --env "IDIR_PASSWORD=${IDIR_PASSWORD}" \
    --env "ANSIBLE_SSH_PASS=${IDIR_PASSWORD}" \
    --env "GITHUB_TOKEN=${GITHUB_TOKEN}" \
    --env "DB_ADMIN_PASSWORD=${DB_ADMIN_PASSWORD}" \
    --env "ARCHES_ANSIBLE_GITHUB_BRANCH=${ANSIBLE_BRANCH}" \
    --env-file <(op document get "BCAP deployment config-${APP_INSTANCE}_env" --vault "BCGov Arches") \
    bcap-deployer bash -c "/home/runner/init_ansible.sh && /home/runner/run_playbook.sh $APP_INSTANCE"
