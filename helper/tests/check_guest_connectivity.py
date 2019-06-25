#!/usr/bin/env python3
import sys
import utils.mojo_os_utils as mojo_os_utils

from zaza.openstack.utilities import (
    cli as cli_utils,
    openstack as openstack_utils,
)


def main(argv):
    cli_utils.setup_logging()
    keystone_session = openstack_utils.get_overcloud_keystone_session()
    novac = openstack_utils.get_nova_session_client(keystone_session)
    mojo_os_utils.check_guest_connectivity(novac)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
