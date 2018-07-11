#!/usr/bin/env python3
import os
import sys
import utils.mojo_utils as mojo_utils
import logging
import argparse

from zaza.utilities import (
    cli as cli_utils,
    openstack as openstack_utils,
)


def main(argv):
    cli_utils.setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("router", nargs="?")
    options = parser.parse_args()
    router_name = cli_utils.parse_arg(options, 'router')
    try:
        cacert = os.path.join(os.environ.get('MOJO_LOCAL_DIR'), 'cacert.pem')
        os.stat(cacert)
    except FileNotFoundError:
        cacert = None
    keystone_session = openstack_utils.get_overcloud_keystone_session(
        verify=cacert)
    neutron_client = openstack_utils.get_neutron_session_client(
        keystone_session)
    router = neutron_client.list_routers(name=router_name)['routers'][0]['id']
    l3_agent = neutron_client.list_l3_agent_hosting_routers(router=router)
    hosting_machine = l3_agent['agents'][0]['host']
    mojo_utils.delete_machine(hosting_machine)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
