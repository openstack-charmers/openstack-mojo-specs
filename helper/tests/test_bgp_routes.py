#!/usr/bin/env python
import argparse
import logging
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils


def main(argv):
    mojo_utils.setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument('--peer-application', '-a',
                        help='BGP Peer application name. Default: quagga',
                        default='quagga')
    options = parser.parse_args()

    peer_application_name = mojo_utils.parse_mojo_arg(options,
                                                      'peer_application')
    overcloud_novarc = mojo_utils.get_overcloud_auth()
    os_version = mojo_os_utils.get_current_os_versions('keystone')['keystone']
    # Keystone policy.json shipped the charm with liberty requires a domain
    # scoped token. Bug #1649106
    if os_version == 'liberty':
        scope = 'DOMAIN'
    else:
        scope = 'PROJECT'
    keystone_session = mojo_os_utils.get_keystone_session(overcloud_novarc,
                                                          scope=scope)
    neutronc = mojo_os_utils.get_neutron_session_client(keystone_session)

    # Run show ip route on BGP peer
    peer_unit = mojo_utils.get_juju_units(service=peer_application_name)[0]
    logging.info("Checking routes on BGP peer {}".format(peer_unit))
    routes = mojo_utils.remote_run(peer_unit,
                                   remote_cmd="vtysh -c 'show ip route'")[0]
    logging.debug(routes)

    # Check for expected advertised routes
    private_cidr = neutronc.list_subnets(
        name='private_subnet')['subnets'][0]['cidr']
    floating_ip_cidr = "{}/32".format(
        neutronc.list_floatingips()['floatingips'][0]['floating_ip_address'])
    assert private_cidr in routes, ("Private subnet CIDR, {}, not advertised "
                                    "to BGP peer".format(private_cidr))
    logging.info("Private subnet CIDR, {}, found in routing table"
                 .format(private_cidr))
    assert floating_ip_cidr in routes, ("Floating IP, {}, not advertised "
                                        "to BGP peer".format(floating_ip_cidr))
    logging.info("Floating IP CIDR, {}, found in routing table"
                 .format(floating_ip_cidr))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
