#!/usr/bin/env python3
import argparse
import logging
import os
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils

from designateclient.v1.domains import Domain
from designateclient.v1.records import Record
from designateclient.v1.servers import Server

from zaza.openstack.utilities import (
    cli as cli_utils,
    openstack as openstack_utils,
)


def main(argv):
    cli_utils.setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--resolver',
                        help='Resolver address. '
                             'Usually designate-bind address.',
                        required=False)
    parser.add_argument('-d', '--domain_name', help='DNS Domain Name. '
                                                    'Must end in a .',
                        default='mojo.serverstack.')
    parser.add_argument('-e', '--email', help='Email address',
                        default='fake@mojo.serverstack')
    parser.add_argument('-b', '--bind-service', help='Bind Service Name',
                        default='designate-bind')

    options = parser.parse_args()
    bind_service_name = cli_utils.parse_arg(options, 'bind_service')
    resolver = cli_utils.parse_arg(options, 'resolver')

    bind_unit = mojo_utils.get_juju_units(bind_service_name)[0]
    if not resolver:
        resolver = mojo_utils.get_juju_unit_ip(bind_unit)
    domain_name = cli_utils.parse_arg(options, 'domain_name')
    email = cli_utils.parse_arg(options, 'email')
    nameserver = 'ns1.{}'.format(domain_name)

    logging.info('Setting up designate {} {}'.format(nameserver, resolver))

    os_version = openstack_utils.get_current_os_versions(
        'keystone')['keystone']
    try:
        cacert = os.path.join(os.environ.get('MOJO_LOCAL_DIR'), 'cacert.pem')
        os.stat(cacert)
    except FileNotFoundError:
        cacert = None
    keystone_session = openstack_utils.get_overcloud_keystone_session(
        verify=cacert)
    neutronc = openstack_utils.get_neutron_session_client(keystone_session)

    if os_version >= 'mitaka':
        designatec = mojo_os_utils.get_designate_session_client(
            keystone_session,
            client_version='2')
        zone = mojo_os_utils.create_or_return_zone(
            designatec,
            domain_name,
            email)
        mojo_os_utils.create_or_return_recordset(
            designatec,
            zone['id'],
            'www',
            'A',
            [resolver])
    else:
        designatec = mojo_os_utils.get_designate_session_client(
            keystone_session,
            client_version='1')
        if not mojo_os_utils.get_designate_server_id(designatec, nameserver):
            logging.info('Creating server {}'.format(nameserver))
            server = Server(name=nameserver)
            server_id = designatec.servers.create(server)
            assert(server_id is not None)
        else:
            logging.info('{} server already exists.'.format(nameserver))

        domain_id = mojo_os_utils.get_designate_domain_id(
            designatec,
            domain_name)
        if not domain_id:
            logging.info('Creating domain {}'.format(domain_name))
            domain = Domain(name=domain_name, email=email)
            domain_id = designatec.domains.create(domain)
            assert(domain_id is not None)
        else:
            logging.info('{} domain already exists.'.format(domain_name))

        if not mojo_os_utils.get_designate_record_id(designatec, domain_id,
                                                     nameserver):
            logging.info('Creating NS record {}'.format(nameserver))
            ns_record = Record(
                name=nameserver,
                type="A",
                data=resolver)
            record_id = designatec.records.create(domain_id, ns_record)
            assert(record_id is not None)
        else:
            logging.info('{} record already exists.'.format(nameserver))

    logging.info('Update network to use domain {}'.format(domain_name))
    net_uuid = openstack_utils.get_net_uuid(neutronc, 'private')
    mojo_os_utils.update_network_dns(neutronc, net_uuid, domain_name)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
