#!/usr/bin/env python
import sys
import utils.mojo_utils as mojo_utils
import logging
import argparse

from zaza.utilities import (
    _local_utils,
    openstack_utils,
)


def main(argv):
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("router", nargs="?")
    options = parser.parse_args()
    router_name = _local_utils.parse_arg(options, 'router')
    keystone_session = openstack_utils.get_overcloud_keystone_session()
    neutron_client = openstack_utils.get_neutron_session_client(
        keystone_session)
    router = neutron_client.list_routers(name=router_name)['routers'][0]['id']
    l3_agent = neutron_client.list_l3_agent_hosting_routers(router=router)
    hosting_machine = l3_agent['agents'][0]['host']
    mojo_utils.delete_machine(hosting_machine)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
