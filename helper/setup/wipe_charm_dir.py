#!/usr/bin/python
import sys
import utils.mojo_utils as mojo_utils


def main(argv):
    logging.basicConfig(level=logging.INFO)
    mojo_utils.wipe_charm_dir()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
