#!/usr/bin/python
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils
import logging
import argparse


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--service")
    parser.add_argument("--kv")
    options = parser.parse_args()
    service = mojo_utils.parse_mojo_arg(options, 'service')
    kv = mojo_utils.parse_mojo_arg(options, 'kv')
    print "Service:" + service
    print "Optoin:" + kv
    mojo_utils.juju_set(service, kv)

if __name__ == "__main__":
    sys.exit(main(sys.argv))
