#!/usr/bin/env python
import sys
import utils.mojo_utils as mojo_utils
import os


def main(argv):
    mojo_utils.setup_logging()
    mojo_utils.upgrade_all_units()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
