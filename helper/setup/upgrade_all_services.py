#!/usr/bin/python
import sys
import utils.mojo_utils as mojo_utils
import logging

def main(argv):
    logging.basicConfig(level=logging.INFO)
    mojo_utils.upgrade_all_services()

if __name__ == "__main__":
    sys.exit(main(sys.argv))
