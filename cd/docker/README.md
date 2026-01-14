## BC Archaological Portal Docker deployment configuration

This directory contains BCAP-specific assets required to deploy to the Ministry environments. It uses
the Docker deployment container (found in GitHub here https://github.com/bferguso/arches_deployer.git)
and the Arches Ansible scripts (available here: https://github.com/bferguso/arches-ansible.git).

The Docker image needs to be created from within the Docker deployment container repo, and containers can
be created from that with application-specific container configuration.

1. `build_container.sh`: Use this script to build an app-specific deployer.
   - ensure the `APP_NAME`, `CONFIG_DIR`, `LOG_DIR` and `IMAGE_NAME` values are correct
   - This needs to be run from this directory for the volume mount paths to be correct

2. `run_deploymet.sh`: Use this script to deploy to a specific environment
   - ensure the `ANSIBLE_BRANCH` value is correct
   - requires the target environment to be provided (`dlvr`|`test`| `prod`)
   - Ensure the appropriate instance-specific config file has been created in the `config` directory and that
     the `app_env` and `deployment_secret` values have been populated

3. `config/` directory contains environment variables required for application deployment and configuration
4. `files/` this is mounted in the docker container and is used to provide variables to the Ansible playbook
    - This file controls how and if Django migrations are performed
5. `logs/` this directory is mounted in the docker container - Ansible log files are stored here.

### Configuration directory for deploying 
The following files need to be configured in the `config/` directory:
1. `deployment_secrets.j2` - copy to `deployment_secrets` and populate. Contains secrets required to deploy BCAP, not part of the application configuration
2. `app_env` - common configuration for all instances
3. `instance_env` - copy to instance-specific filename (eg `dlvr_env`, `test_env` or `prod_env` and add configuration)

Most non-sensitive configuration is provided in the `/bcap/cd/config/` directory.