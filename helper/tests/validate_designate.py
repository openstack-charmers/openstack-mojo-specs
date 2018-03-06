#!/usr/bin/env python
import argparse
import logging
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils


def main(argv):
    mojo_utils.setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--domain_name', help='DNS Domain Name. '
                                                    'Must end in a .',
                        default='mojo.serverstack.')
    options = parser.parse_args()
    domain_name = mojo_utils.parse_mojo_arg(options, 'domain_name')
    overcloud_novarc = mojo_utils.get_overcloud_auth()
    keystone_session = mojo_os_utils.get_keystone_session(overcloud_novarc,
                                                          scope='PROJECT')
    nova_client = mojo_os_utils.get_nova_session_client(keystone_session)
    des_client = mojo_os_utils.get_designate_session_client(keystone_session,
                                                            all_tenants=True)
    nova_domain = mojo_utils.juju_get('designate', 'nova-domain')
    for server in nova_client.servers.list():
        for addr_info in server.addresses['private']:
            if addr_info['OS-EXT-IPS:type'] == 'floating':
                mojo_os_utils.check_dns_entry_in_bind(
                    addr_info['addr'],
                    '{}.{}'.format(server.name, domain_name))
            # Test legacy notifications based records
            if addr_info['OS-EXT-IPS:type'] == 'fixed' and nova_domain:
                keystone_client = mojo_os_utils.get_keystone_session_client(
                    keystone_session)

                record_ctxt = {
                    'hostname': server.name,
                    'zone': nova_domain}

                target_project = overcloud_novarc.get(
                    'OS_TENANT_NAME',
                    overcloud_novarc['OS_PROJECT_NAME'])
                for project in keystone_client.projects.list():
                    if project.name == target_project:
                        record_ctxt['project_id'] = project.id
                        record_ctxt['tenant_id'] = project.id

                record_format = mojo_utils.juju_get(
                    'designate',
                    'nova-record-format')
                record_name = record_format % record_ctxt
                mojo_os_utils.check_dns_entry_in_designate(
                    des_client,
                    addr_info['addr'],
                    nova_domain,
                    record_name=record_name)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
