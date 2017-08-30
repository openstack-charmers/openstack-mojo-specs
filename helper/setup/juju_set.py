#!/usr/bin/env python
import sys
import utils.mojo_utils as mojo_utils
import argparse


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--service")
    parser.add_argument("--kv")
    options = parser.parse_args()
    service = mojo_utils.parse_mojo_arg(options, 'service')
    kv = mojo_utils.parse_mojo_arg(options, 'kv')
    print("Service: {}".format(service))
    print("Option: {}".format(kv))
    mojo_utils.juju_set(service, kv)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
