#!/usr/bin/env python

import argparse
import sys

from zaza.utilities import _local_utils


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("application",  default="ceph-mon", nargs="*")
    parser.add_argument("units", default=[0, 1], nargs="*")
    options = parser.parse_args()
    application = _local_utils.parse_arg(options,
                                         'application', multiargs=False)
    units = _local_utils.parse_arg(options, 'units', multiargs=True)

    _local_utils.remote_run(
        '{}/{}'.format(application, units[-1]),
        remote_cmd='ceph osd pool create rbd 128')
    # Check
    _local_utils.remote_run(
        '{}/{}'.format(application, units[0]),
        remote_cmd='echo 123456789 > /tmp/input.txt')
    _local_utils.remote_run(
        '{}/{}'.format(application, units[0]),
        remote_cmd='rados put -p rbd test_input /tmp/input.txt')

    # Check
    output = _local_utils.remote_run(
        '{}/{}'.format(application, units[-1]),
        remote_cmd='rados get -p rbd test_input /dev/stdout')

    # Cleanup
    _local_utils.remote_run(
        '{}/{}'.format(application, units[-1]),
        remote_cmd='rados rm -p rbd test_input')
    if output.strip() != "123456789":
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
