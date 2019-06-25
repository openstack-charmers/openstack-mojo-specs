#!/usr/bin/env python3
import sys
import utils.mojo_utils as mojo_utils
import argparse

from zaza.openstack.utilities import cli as cli_utils


def main(argv):
    cli_utils.setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("services", nargs="*")
    options = parser.parse_args()
    services = cli_utils.parse_arg(options, 'services', multiargs=True)
    for service in services:
        mojo_utils.upgrade_service(service)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
