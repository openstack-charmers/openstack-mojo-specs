#!/usr/bin/python
import argparse
import logging
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils


def setup_sdn(net_topology, ignore_env_vars):
    overcloud_novarc = mojo_utils.get_overcloud_auth()
    # Get os clients
    keystonec = mojo_os_utils.get_keystone_client(overcloud_novarc)
    neutronc = mojo_os_utils.get_neutron_client(overcloud_novarc)
    net_info = mojo_utils.get_mojo_config('network.yaml')[net_topology]

    # Override network.yaml values with env var values if they exist
    if not ignore_env_vars:
        logging.info('Consuming network environment variables as overrides.')
        net_env_vars = mojo_utils.get_network_env_vars()
        net_info.update(net_env_vars)

    logging.info('Network info: {}'.format(mojo_utils.dict_to_yaml(net_info)))

    # Resolve the tenant name from the overcloud novarc into a tenant id
    tenant_id = mojo_os_utils.get_tenant_id(keystonec,
                                            overcloud_novarc['OS_TENANT_NAME'])
    # Create the external network
    ext_network = mojo_os_utils.create_external_network(
        neutronc,
        tenant_id,
        net_info['external_net_name'],
        net_info['network_type'])
    mojo_os_utils.create_external_subnet(
        neutronc,
        tenant_id,
        ext_network,
        net_info['default_gateway'],
        net_info['external_net_cidr'],
        net_info['start_floating_ip'],
        net_info['end_floating_ip'],
        net_info['external_subnet_name'])
    provider_router = mojo_os_utils.create_provider_router(neutronc, tenant_id)
    mojo_os_utils.plug_extnet_into_router(
        neutronc,
        provider_router,
        ext_network)
    tenant_network = mojo_os_utils.create_tenant_network(
        neutronc,
        tenant_id,
        shared=False,
        network_type=net_info['network_type'])
    tenant_subnet = mojo_os_utils.create_tenant_subnet(
        neutronc,
        tenant_id,
        tenant_network,
        net_info['private_net_cidr'])
    mojo_os_utils.update_subnet_dns(
        neutronc,
        tenant_subnet,
        net_info['external_dns'])
    mojo_os_utils.plug_subnet_into_router(
        neutronc,
        net_info['router_name'],
        tenant_network,
        tenant_subnet)


def main(argv):
    logging.basicConfig(level=logging.INFO)
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

    # Handle network for Openstack-on-Openstack scenarios
    if mojo_utils.get_provider_type() == 'openstack':
        logging.info('Configuring network for OpenStack undercloud/provider')
        undercloud_novarc = mojo_utils.get_undercloud_auth()
        novac = mojo_os_utils.get_nova_client(undercloud_novarc)
        neutronc = mojo_os_utils.get_neutron_client(undercloud_novarc)
        # Add an interface to the neutron-gateway units and tell juju to use it
        # as the external port.
        net_info = mojo_utils.get_mojo_config('network.yaml')[net_topology]
        mojo_os_utils.configure_gateway_ext_port(
            novac,
            neutronc,
            dvr_mode=net_info.get('dvr_enabled', False))

    setup_sdn(net_topology, ignore_env_vars)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
