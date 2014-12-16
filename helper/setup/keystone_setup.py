#!/usr/bin/python
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils


def main(argv):
    overcloud_novarc = mojo_utils.get_overcloud_auth()
    keystone_client = mojo_os_utils.get_keystone_client(overcloud_novarc)
    user_config = mojo_utils.get_mojo_config('keystone_users.yaml')
    tenants = [user['tenant'] for user in user_config]
    mojo_os_utils.tenant_create(keystone_client, tenants)
    mojo_os_utils.user_create(keystone_client, user_config)
    mojo_os_utils.add_users_to_roles(keystone_client, user_config)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
