#!/usr/bin/env python3
import sys
import utils.mojo_utils as mojo_utils
import argparse

from zaza.utilities import cli as cli_utils


def main(argv):
    cli_utils.setup_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("units", nargs="*")
    options = parser.parse_args()
    unit_args = cli_utils.parse_arg(options, 'units', multiargs=True)
    for unitreq in unit_args:
        if ':' in unitreq:
            application, unitcount = unitreq.split(':')
            units = mojo_utils.get_juju_units(application)
            i = 0
            for unit in units:
                if i >= int(unitcount):
                    break
                mojo_utils.delete_unit(unit)
                i = i + 1
        elif '/' in unitreq:
            units = mojo_utils.get_juju_units(unitreq.split('/')[0])
            if unitreq in units:
                mojo_utils.delete_unit(unitreq)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
