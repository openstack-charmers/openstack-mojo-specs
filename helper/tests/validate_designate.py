#!/usr/bin/env python3
import argparse
import sys
import utils.mojo_os_utils as mojo_os_utils

from zaza.utilities import (
    cli_utils,
    openstack_utils,
)


def main(argv):
    cli_utils.setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--domain_name', help='DNS Domain Name. '
                                                    'Must end in a .',
                        default='mojo.serverstack.')
    options = parser.parse_args()
    domain_name = cli_utils.parse_arg(options, 'domain_name')

    os_version = openstack_utils.get_current_os_versions(
        'keystone')['keystone']
    if os_version >= 'queens':
        designate_api = '2'
    else:
        designate_api = '1'
    keystone_session = openstack_utils.get_overcloud_keystone_session()

    nova_client = openstack_utils.get_nova_session_client(keystone_session)
    des_client = mojo_os_utils.get_designate_session_client(
        keystone_session, all_tenants=True, client_version=designate_api)
    for server in nova_client.servers.list():
        for addr_info in server.addresses['private']:
            if addr_info['OS-EXT-IPS:type'] == 'floating':
                mojo_os_utils.check_dns_entry(
                    des_client,
                    addr_info['addr'],
                    domain_name,
                    '{}.{}'.format(server.name, domain_name))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
