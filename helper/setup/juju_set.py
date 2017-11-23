#!/usr/bin/env python
import sys
import utils.mojo_utils as mojo_utils
import argparse


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--service")
    parser.add_argument("--kv")
    parser.add_argument("--wait")
    options = parser.parse_args()
    service = mojo_utils.parse_mojo_arg(options, 'service')
    kv = mojo_utils.parse_mojo_arg(options, 'kv')
    wait = mojo_utils.parse_mojo_arg(options, 'wait')
    print("Wait: {}".format(wait))
    if wait is not None:
        wait = wait == 'True'
    print("Service: {}".format(service))
    print("Option: {}".format(kv))
    print("Wait: {}".format(wait))
    mojo_utils.juju_set(service, kv, wait=wait)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
