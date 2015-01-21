#!/usr/bin/python
import sys
import utils.mojo_utils as mojo_utils
import logging
import argparse


def main(argv):
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("units", nargs="*")
    options = parser.parse_args()
    unit_args = mojo_utils.parse_mojo_arg(options, 'units', multiargs=True)
    for unitreq in unit_args:
        if ':' in unitreq:
            service, unitcount = unitreq.split(':')
            units = mojo_utils.get_juju_units(service=service)
            i = 0
            for unit in units:
                if i >= int(unitcount):
                    break
                mojo_utils.delete_unit(unit)
                i = i + 1
        elif '/' in unitreq:
            units = mojo_utils.get_juju_units(service=unitreq.split('/')[0])
            if unitreq in units:
                mojo_utils.delete_unit(unitreq)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
