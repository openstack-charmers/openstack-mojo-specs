#!/usr/bin/env python
import logging
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils


def main(argv):
    mojo_utils.setup_logging()
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

    ips = neutronc.list_floatingips()
    address = None
    address = ips.get('floatingips')[-1].get('floating_ip_address', None)
    print(address)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    sys.exit(main(sys.argv))
