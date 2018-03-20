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
                        help='BGP peer application name. Default: quagga',
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

    logging.info("Setting up BGP speaker")
    bgp_speaker = mojo_os_utils.create_bgp_speaker(neutronc, local_as=12345)

    logging.info("Advertising BGP routes")
    # Add networks to bgp speaker
    mojo_os_utils.add_network_to_bgp_speaker(neutronc, bgp_speaker, 'ext_net')
    mojo_os_utils.add_network_to_bgp_speaker(neutronc, bgp_speaker, 'private')
    logging.debug("Advertised routes: {}"
                  .format(
                      neutronc.list_route_advertised_from_bgp_speaker(
                          bgp_speaker['id'])))

    # Create peer
    logging.info("Setting up BGP peer")
    bgp_peer = mojo_os_utils.create_bgp_peer(neutronc,
                                             peer_application_name,
                                             remote_as=10000)
    # Add peer to bgp speaker
    mojo_os_utils.add_peer_to_bgp_speaker(neutronc, bgp_speaker, bgp_peer)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
