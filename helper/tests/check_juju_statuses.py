#!/usr/bin/env python
import sys
import utils.mojo_utils as mojo_utils


def main(argv):
    return mojo_utils.juju_wait_finished()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
