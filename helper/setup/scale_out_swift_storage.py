#!/usr/bin/env python3
import sys
import utils.mojo_utils as mojo_utils


def main(argv):
    mojo_utils.add_unit('swift-storage-z1')
    mojo_utils.add_unit('swift-storage-z2')
    mojo_utils.add_unit('swift-storage-z3')


if __name__ == "__main__":
    sys.exit(main(sys.argv))
