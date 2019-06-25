#!/usr/bin/env python3
import sys
import utils.mojo_utils as mojo_utils

from zaza.openstack.utilities import cli as cli_utils


def main(argv):
    cli_utils.setup_logging()
    mojo_utils.wipe_charm_dir()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
