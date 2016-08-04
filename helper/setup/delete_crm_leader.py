#!/usr/bin/python
import sys
import os
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils
from utils.os_versions import ubuntu_version
import logging
import argparse


def main(argv):
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--service")
    parser.add_argument("--resource")
    options = parser.parse_args()
    service = mojo_utils.parse_mojo_arg(options, 'service')
    resource = mojo_utils.parse_mojo_arg(options, 'resource')
    xenial = distro_info.UbuntuDistroInfo().all.index('xenial')
    mojo_env = distro_info.UbuntuDistroInfo().all.index(os.environ.get('MOJO_SERIES'))
    if mojo_env >= xenial:
        resource = resource.replace('eth0', 'ens2')
    print("service: {} || resource: {}".format(service, resource))
    mojo_os_utils.delete_crm_leader(service, resource)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
