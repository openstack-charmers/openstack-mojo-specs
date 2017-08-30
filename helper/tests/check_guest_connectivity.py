#!/usr/bin/env python
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils
import logging


def main(argv):
    logging.basicConfig(level=logging.INFO)
    overcloud_novarc = mojo_utils.get_overcloud_auth()
    novac = mojo_os_utils.get_nova_client(overcloud_novarc)
    mojo_os_utils.check_guest_connectivity(novac)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
