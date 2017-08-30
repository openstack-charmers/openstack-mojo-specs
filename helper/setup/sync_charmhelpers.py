#!/usr/bin/env python
import sys
import utils.mojo_utils as mojo_utils


def main(argv):
    mojo_utils.sync_all_charmhelpers()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
