#!/usr/bin/python
import sys
import utils.mojo_utils as mojo_utils
import utils.mojo_os_utils as mojo_os_utils
import logging
import argparse


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("units", nargs="*")
    options = parser.parse_args()
    unit_args = mojo_utils.parse_mojo_arg(options, 'units', multiargs=True)
    for unitreq in unit_args:
        service, count = unitreq.split(":")
        mojo_utils.add_unit(service, unit_num=count) 

if __name__ == "__main__":
    sys.exit(main(sys.argv))
