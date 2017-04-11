#!/usr/bin/python
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils


def main(argv):
    mojo_utils.setup_logging()
    overcloud_novarc = mojo_utils.get_overcloud_auth()
    user_config = mojo_utils.get_mojo_config('keystone_users.yaml')
    keystone_session = mojo_os_utils.get_keystone_session(overcloud_novarc)
    keystone_client = (
        mojo_os_utils.get_keystone_session_client(keystone_session))
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
