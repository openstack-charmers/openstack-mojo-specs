#!/usr/bin/env python
import sys
import utils.mojo_utils as mojo_utils

from zaza.utilities import _local_utils


def main(argv):
    _local_utils.setup_logging()
    mojo_utils.wipe_charm_dir()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
