#!/usr/bin/env python3
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils

from zaza.utilities import (
    _local_utils,
    openstack_utils,
)


def main(argv):
    _local_utils.setup_logging()
    overcloud_novarc = openstack_utils.get_overcloud_auth()
    user_file = mojo_utils.get_mojo_file('keystone_users.yaml')
    user_config = _local_utils.get_yaml_config(user_file)
    keystone_session = openstack_utils.get_overcloud_keystone_session()
    keystone_client = openstack_utils.get_keystone_session_client(
        keystone_session)
    if overcloud_novarc.get('API_VERSION', 2) == 2:
        projects = [user['project'] for user in user_config]
        mojo_os_utils.project_create(keystone_client, projects)
        mojo_os_utils.user_create_v2(keystone_client, user_config)
        # TODO validate this works without adding roles
        # mojo_os_utils.add_users_to_roles(keystone_client, user_config)
    else:
        for user in user_config:
            mojo_os_utils.domain_create(keystone_client, [user['domain']])
            mojo_os_utils.project_create(keystone_client, [user['project']],
                                         user['domain'])
    mojo_os_utils.user_create_v3(keystone_client, user_config)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
