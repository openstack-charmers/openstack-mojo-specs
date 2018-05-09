#!/usr/bin/env python3

import argparse
import sys

from zaza.utilities import (
    cli_utils,
    juju_utils,
)


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("application",  default="ceph-mon", nargs="*")
    parser.add_argument("units", default=[0, 1], nargs="*")
    options = parser.parse_args()
    application = cli_utils.parse_arg(options,
                                      'application', multiargs=False)
    units = cli_utils.parse_arg(options, 'units', multiargs=True)

    juju_utils.remote_run(
        '{}/{}'.format(application, units[-1]),
        remote_cmd='ceph osd pool create rbd 128')
    # Check
    juju_utils.remote_run(
        '{}/{}'.format(application, units[0]),
        remote_cmd='echo 123456789 > /tmp/input.txt')
    juju_utils.remote_run(
        '{}/{}'.format(application, units[0]),
        remote_cmd='rados put -p rbd test_input /tmp/input.txt')

    # Check
    output = juju_utils.remote_run(
        '{}/{}'.format(application, units[-1]),
        remote_cmd='rados get -p rbd test_input /dev/stdout')

    # Cleanup
    juju_utils.remote_run(
        '{}/{}'.format(application, units[-1]),
        remote_cmd='rados rm -p rbd test_input')
    if output.strip() != "123456789":
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
