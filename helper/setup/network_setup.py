#!/usr/bin/env python
import argparse
import logging
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils


def setup_sdn(net_topology, net_info):
    overcloud_novarc = mojo_utils.get_overcloud_auth()
    keystone_session = mojo_os_utils.get_keystone_session(overcloud_novarc)
    keystonec = mojo_os_utils.get_keystone_session_client(keystone_session)
    neutronc = mojo_os_utils.get_neutron_session_client(keystone_session)
    # Resolve the project name from the overcloud novarc into a project id
    project_id = mojo_os_utils.get_project_id(
        keystonec,
        'admin',
        api_version=overcloud_novarc['API_VERSION']
    )
    # Create the external network
    ext_network = mojo_os_utils.create_external_network(
        neutronc,
        project_id,
        net_info.get('dvr_enabled', False),
        net_info['external_net_name'])
    mojo_os_utils.create_external_subnet(
        neutronc,
        project_id,
        ext_network,
        net_info['default_gateway'],
        net_info['external_net_cidr'],
        net_info['start_floating_ip'],
        net_info['end_floating_ip'],
        net_info['external_subnet_name'])
    provider_router = (
        mojo_os_utils.create_provider_router(neutronc, project_id))
    mojo_os_utils.plug_extnet_into_router(
        neutronc,
        provider_router,
        ext_network)
    project_network = mojo_os_utils.create_project_network(
        neutronc,
        project_id,
        shared=False,
        network_type=net_info['network_type'])
    project_subnet = mojo_os_utils.create_project_subnet(
        neutronc,
        project_id,
        project_network,
        net_info['private_net_cidr'])
    mojo_os_utils.update_subnet_dns(
        neutronc,
        project_subnet,
        net_info['external_dns'])
    mojo_os_utils.plug_subnet_into_router(
        neutronc,
        net_info['router_name'],
        project_network,
        project_subnet)


def main(argv):
    mojo_utils.setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument('net_topology',
                        help='network topology type, default is GRE',
                        default='gre', nargs='?')
    parser.add_argument('--ignore_env_vars', '-i',
                        help='do not override using environment variables',
                        action='store_true',
                        default=False)
    options = parser.parse_args()
    net_topology = mojo_utils.parse_mojo_arg(options, 'net_topology')
    ignore_env_vars = mojo_utils.parse_mojo_arg(options, 'ignore_env_vars')
    logging.info('Setting up %s network' % (net_topology))
    net_info = mojo_utils.get_net_info(net_topology, ignore_env_vars)

    # Handle network for Openstack-on-Openstack scenarios
    if mojo_utils.get_provider_type() == 'openstack':
        logging.info('Configuring network for OpenStack undercloud/provider')
        session = mojo_os_utils.get_keystone_session(
                       mojo_utils.get_undercloud_auth())
        novac = mojo_os_utils.get_nova_session_client(session)
        neutronc = mojo_os_utils.get_neutron_session_client(session)

        # Add an interface to the neutron-gateway units and tell juju to use it
        # as the external port.
        if 'net_id' in net_info.keys():
            net_id = net_info['net_id']
        else:
            net_id = None

        mojo_os_utils.configure_gateway_ext_port(
            novac,
            neutronc,
            dvr_mode=net_info.get('dvr_enabled', False),
            net_id=net_id)

    setup_sdn(net_topology, net_info)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
