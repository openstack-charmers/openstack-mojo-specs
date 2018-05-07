#!/usr/bin/env python3
import sys
import utils.mojo_utils as mojo_utils
import logging
import argparse

from zaza.utilities import _local_utils


def main(argv):
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("application", nargs="*")
    options = parser.parse_args()
    unit_args = _local_utils.parse_arg(
        options,
        'application', multiargs=True)
    for application in unit_args:
        mojo_utils.delete_application(application)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
