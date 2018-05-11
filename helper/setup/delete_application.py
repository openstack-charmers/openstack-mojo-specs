#!/usr/bin/env python3
import sys
import utils.mojo_utils as mojo_utils
import logging
import argparse

from zaza.utilities import cli as cli_utils


def main(argv):
    cli_utils.setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("application", nargs="*")
    options = parser.parse_args()
    unit_args = cli_utils.parse_arg(
        options,
        'application', multiargs=True)
    for application in unit_args:
        mojo_utils.delete_application(application)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
