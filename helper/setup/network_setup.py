#!/usr/bin/python
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils
import logging
import argparse
import os


def setup_sdn(net_topology):
    overcloud_novarc = mojo_utils.get_overcloud_auth()
    # Get os clients
    keystonec = mojo_os_utils.get_keystone_client(overcloud_novarc)
    neutronc = mojo_os_utils.get_neutron_client(overcloud_novarc)
    net_info = mojo_utils.get_mojo_config('network.yaml')[net_topology]
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
    tenant_network = mojo_os_utils.create_tenant_network(neutronc, tenant_id)
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
    parser.add_argument("net_topology", default='gre', nargs='?')
    options = parser.parse_args()
    net_topology = mojo_utils.parse_mojo_arg(options, 'net_topology')
    logging.info('Setting up %s network' % (net_topology))
    undercloud_novarc = mojo_utils.get_undercload_auth()
    novac = mojo_os_utils.get_nova_client(undercloud_novarc)
    neutronc = mojo_os_utils.get_neutron_client(undercloud_novarc)
    # Add an interface to the neutron-gateway units and tell juju to us it
    # as the external port
    mojo_os_utils.configure_gateway_ext_port(novac, neutronc)
    setup_sdn(net_topology)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
