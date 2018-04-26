#!/usr/bin/env python
import sys
import os
import utils.mojo_os_utils as mojo_os_utils
import distro_info
import logging
import argparse

from zaza.utilities import _local_utils


def main(argv):
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--service")
    parser.add_argument("--resource")
    options = parser.parse_args()
    service = _local_utils.parse_arg(options, 'service')
    resource = _local_utils.parse_arg(options, 'resource')
    xenial = distro_info.UbuntuDistroInfo().all.index('xenial')
    series = os.environ.get('MOJO_SERIES')
    mojo_env = distro_info.UbuntuDistroInfo().all.index(series)
    if mojo_env >= xenial:
        resource = resource.replace('eth0', 'ens2')
    mojo_os_utils.delete_crm_leader(service, resource)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
