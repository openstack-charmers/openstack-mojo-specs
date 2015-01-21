#!/usr/bin/python
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils
import logging
import argparse


def main(argv):
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("router", nargs="?")
    options = parser.parse_args()
    router_name = mojo_utils.parse_mojo_arg(options, 'router')
    overcloud_novarc = mojo_utils.get_overcloud_auth()
    neutron_client = mojo_os_utils.get_neutron_client(overcloud_novarc)
    router = neutron_client.list_routers(name=router_name)['routers'][0]['id']
    l3_agent = neutron_client.list_l3_agent_hosting_routers(router=router)
    hosting_machine = l3_agent['agents'][0]['host']
    mojo_utils.delete_machine(hosting_machine)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
