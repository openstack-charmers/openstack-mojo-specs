#!/usr/bin/python
import logging
import sys
import utils.mojo_utils as mojo_utils


def main(argv):
    log = logging.getLogger()
    log.setLevel(logging.DEBUG)
    mojo_utils.git_checkout_all('stable/16.10')

if __name__ == "__main__":
    sys.exit(main(sys.argv))
