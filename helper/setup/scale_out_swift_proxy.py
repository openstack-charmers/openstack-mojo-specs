#!/usr/bin/python
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils

def main(argv):
    mojo_utils.add_unit('swift-proxy')

if __name__ == "__main__":
    sys.exit(main(sys.argv))
