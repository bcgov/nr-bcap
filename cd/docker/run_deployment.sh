# Must be run from bcap root
export APP_INSTANCE=$1
export ANSIBLE_BRANCH=feat/v8_updates
docker exec -it \
      --env-file "./cd/docker/config/app_env" \
      --env-file "./cd/docker/config/deployment_secrets" \
      --env "ARCHES_ANSIBLE_GITHUB_BRANCH=${ANSIBLE_BRANCH}" \
      --env-file "./cd/docker/config/${APP_INSTANCE}_env" \
      bcap-deployer bash -c "/home/runner/init_ansible.sh && /home/runner/run_playbook.sh $APP_INSTANCE"
