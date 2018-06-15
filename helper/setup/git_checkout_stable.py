#!/usr/bin/env python3
import logging
import sys
import utils.mojo_utils as mojo_utils


def main(argv):
    log = logging.getLogger()
    log.setLevel(logging.DEBUG)
    mojo_utils.git_checkout_all('stable/17.02')


if __name__ == "__main__":
    sys.exit(main(sys.argv))
