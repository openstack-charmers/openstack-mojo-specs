#!/usr/bin/env python
import sys
import utils.mojo_utils as mojo_utils
import logging
import argparse

from zaza.utilities import _local_utils


def main(argv):
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("services", nargs="*")
    options = parser.parse_args()
    services = _local_utils.parse_arg(options, 'services', multiargs=True)
    for service in services:
        mojo_utils.upgrade_service(service)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
