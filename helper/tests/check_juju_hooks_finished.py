#!/usr/bin/python

import utils.mojo_utils as mojo_utils
import sys


def remote_runs(units):
    for unit in units:
        if not mojo_utils.remote_run(unit):
            raise Exception('Juju run failed')


def run_check():
    juju_units = mojo_utils.get_juju_units()
    remote_runs(juju_units)
    remote_runs(juju_units)


def main(argv):
    run_check()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
