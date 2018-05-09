#!/usr/bin/env python3

import utils.mojo_utils as mojo_utils
import sys

from zaza.utilities import juju_utils


def remote_runs(units):
    for unit in units:
        if not juju_utils.remote_run(unit, remote_cmd='uname -a'):
            raise Exception('Juju run failed on ' + unit)


def run_check():
    juju_units = mojo_utils.get_juju_units()
    remote_runs(juju_units)
    remote_runs(juju_units)


def main(argv):
    run_check()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
