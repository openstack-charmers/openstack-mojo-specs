#!/usr/bin/env python
import sys
import utils.mojo_utils as mojo_utils


def main(argv):
    return mojo_utils.juju_status_check_and_wait()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
