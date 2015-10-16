#!/usr/bin/python
import sys
import utils.mojo_utils as mojo_utils


def main(argv):
    mojo_utils.setup_logging()
    mojo_utils.wipe_charm_dir()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
